import numpy as np
import pandas as pd
from loaders import load_car_hacking, load_vtc_can, load_veremi, load_cicids
from features import get_extractor
import warnings

class PreprocessingPipeline:
    def __init__(self, window_size=64, stride=16, n_clients=10, alpha=0.3):
        self.W = window_size
        self.S = stride
        self.n_clients = n_clients
        self.alpha = alpha
        
        self.clip_min = None
        self.clip_max = None
        self.mean = None
        self.std = None

    def _split_sessions(self, df):
        """Split 70/15/15 by session_id."""
        sessions = df['session_id'].unique()
        np.random.shuffle(sessions)
        
        n_train = int(0.7 * len(sessions))
        n_val = int(0.15 * len(sessions))
        
        train_sess = sessions[:n_train]
        val_sess = sessions[n_train:n_train+n_val]
        test_sess = sessions[n_train+n_val:]
        
        # Explicit assertion for leakage
        assert len(set(train_sess).intersection(set(val_sess))) == 0
        assert len(set(train_sess).intersection(set(test_sess))) == 0
        assert len(set(val_sess).intersection(set(test_sess))) == 0
        
        return (df[df['session_id'].isin(train_sess)], 
                df[df['session_id'].isin(val_sess)], 
                df[df['session_id'].isin(test_sess)])

    def _window_and_extract(self, df, extractor):
        """Generate sliding windows per session and extract 46-D features."""
        X, y = [], []
        dropped_sessions = 0
        
        for sess_id, group in df.groupby('session_id'):
            if len(group) < self.W:
                dropped_sessions += 1
                continue
                
            for i in range(0, len(group) - self.W + 1, self.S):
                window = group.iloc[i:i+self.W]
                feat = extractor(window)
                # Label is the mode of the window
                label = window['label'].mode().iloc[0]
                
                X.append(feat)
                y.append(label)
                
        return np.array(X), np.array(y), dropped_sessions

    def _fit_scale(self, X_train):
        self.clip_min = np.percentile(X_train, 1, axis=0)
        self.clip_max = np.percentile(X_train, 99, axis=0)
        
        clipped = np.clip(X_train, self.clip_min, self.clip_max)
        self.mean = np.mean(clipped, axis=0)
        self.std = np.std(clipped, axis=0)
        self.std[self.std == 0] = 1.0 # Prevent division by zero
        
    def _transform_scale(self, X):
        if len(X) == 0:
            return np.empty((0, self.clip_min.shape[0]))
        clipped = np.clip(X, self.clip_min, self.clip_max)
        z_scored = (clipped - self.mean) / self.std
        squashed = np.tanh(z_scored)
        
        # Assert post-scaling
        assert not np.isnan(squashed).any(), "NaN in scaled features"
        assert not np.isinf(squashed).any(), "Inf in scaled features"
        assert np.all(squashed >= -1.0) and np.all(squashed <= 1.0), "Features out of [-1, 1]"
        
        return squashed

    def _dirichlet_partition(self, y_train):
        """Partition train indices among N clients using Dirichlet distribution per class."""
        classes = np.unique(y_train)
        client_indices = {i: [] for i in range(self.n_clients)}
        
        client_class_counts = {i: {c: 0 for c in classes} for i in range(self.n_clients)}
        
        for c in classes:
            idx_c = np.where(y_train == c)[0]
            np.random.shuffle(idx_c)
            
            proportions = np.random.dirichlet(np.repeat(self.alpha, self.n_clients))
            # Scale and round proportions
            splits = np.round(proportions * len(idx_c)).astype(int)
            # Fix rounding errors
            splits[-1] = len(idx_c) - splits[:-1].sum()
            
            start = 0
            for i in range(self.n_clients):
                end = start + splits[i]
                if end > start: # if client gets any samples of this class
                    indices = idx_c[start:end]
                    client_indices[i].extend(indices)
                    client_class_counts[i][c] = len(indices)
                start = end
                
        # Return per-client assignments as a list of arrays (each array is a list of indices)
        return client_indices, client_class_counts, classes

    def fit_transform(self, dataset_name, base_dir, smoke_mode=False):
        print(f"--- Starting Preprocessing Pipeline for {dataset_name} ---")
        
        if dataset_name == 'car_hack':
            df = load_car_hacking(base_dir)
        elif dataset_name == 'vtc_can':
            df = load_vtc_can(base_dir)
        elif dataset_name == 'veremi':
            df = load_veremi(base_dir)
        elif dataset_name == 'cicids':
            df = load_cicids(base_dir)
        else:
            raise ValueError("Unknown dataset")
            
        print(f"Total raw records: {len(df)}")
        
        train_df, val_df, test_df = self._split_sessions(df)
        
        if smoke_mode:
            print("[Smoke Mode] Truncating raw dataframes before windowing to save time...")
            train_df = train_df.head(2000)
            val_df = val_df.head(1000)
            test_df = test_df.head(1000)
            
        print(f"Sessions split (70/15/15) - Train: {train_df['session_id'].nunique()}, Val: {val_df['session_id'].nunique()}, Test: {test_df['session_id'].nunique()}")
        
        extractor = get_extractor(dataset_name)
        
        X_train_raw, y_train_raw, drop_train = self._window_and_extract(train_df, extractor)
        X_val_raw, y_val_raw, drop_val = self._window_and_extract(val_df, extractor)
        X_test_raw, y_test_raw, drop_test = self._window_and_extract(test_df, extractor)
        
        print(f"Windows extracted: Train {len(X_train_raw)}, Val {len(X_val_raw)}, Test {len(X_test_raw)}")
        print(f"Dropped sessions (too short): Train {drop_train}, Val {drop_val}, Test {drop_test}")
        
        if len(X_train_raw) == 0:
            raise ValueError("Train split generated 0 windows! Cannot fit scaling.")
            
        # Scaling
        self._fit_scale(X_train_raw)
        X_train = self._transform_scale(X_train_raw)
        X_val = self._transform_scale(X_val_raw)
        X_test = self._transform_scale(X_test_raw)
        
        # Partitioning
        classes_all = np.unique(np.concatenate([y_train_raw, y_val_raw, y_test_raw])) if len(y_val_raw) > 0 else np.unique(np.concatenate([y_train_raw, y_test_raw]))
        client_indices, client_class_counts, _ = self._dirichlet_partition(y_train_raw)
        
        # Ensure all classes are represented in counts
        for i in range(self.n_clients):
            for c in classes_all:
                if c not in client_class_counts[i]:
                    client_class_counts[i][c] = 0
                    
        metadata = {
            'drop_train': drop_train,
            'drop_val': drop_val,
            'drop_test': drop_test,
            'client_indices': client_indices,
            'client_class_counts': client_class_counts,
            'classes': classes_all.tolist()
        }
        
        return X_train, y_train_raw, X_val, y_val_raw, X_test, y_test_raw, classes_all.tolist(), metadata
