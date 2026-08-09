import numpy as np
import pandas as pd
import hashlib

def extract_can_features(window_df):
    """
    Extract exactly 46 features from a window of CAN messages.
    Input: DataFrame of shape (W, num_raw_cols).
    """
    W = len(window_df)
    
    # Payload byte stats (16): mean + std of b0..b7
    b_cols = [f'b{i}' for i in range(8)]
    payload_mean = window_df[b_cols].mean().values
    payload_std = window_df[b_cols].std().fillna(0).values
    payload_stats = np.concatenate([payload_mean, payload_std]) # 16
    
    # Message length (2): mean + std of DLC
    dlc_mean = window_df['dlc'].mean()
    dlc_std = window_df['dlc'].std()
    if pd.isna(dlc_std): dlc_std = 0.0
    dlc_stats = np.array([dlc_mean, dlc_std]) # 2
    
    # CAN-ID identity (26): hashed ID distribution over 24 buckets + dominant-ID stats
    # Use a fixed hash function (md5) to map hex IDs to 0-23
    def hash_id(cid):
        # Handle string or float
        cid_str = str(cid).encode('utf-8')
        return int(hashlib.md5(cid_str).hexdigest(), 16) % 24
        
    hashed_ids = window_df['can_id'].apply(hash_id)
    bucket_counts = np.bincount(hashed_ids, minlength=24)[:24]
    
    assert bucket_counts.sum() == W, f"Bucket sum {bucket_counts.sum()} != Window size {W}"
    
    # Dominant-ID stats (count, ratio)
    vc = window_df['can_id'].value_counts()
    mode_count = vc.iloc[0] if len(vc) > 0 else 0
    mode_ratio = mode_count / W if W > 0 else 0
    id_stats = np.concatenate([bucket_counts, [mode_count, mode_ratio]]) # 26
    
    # Data entropy (2): Shannon entropy of payload bytes + non-zero ratio
    # Flatten payload to 1D
    all_bytes = window_df[b_cols].values.flatten()
    if len(all_bytes) > 0:
        non_zero_ratio = np.count_nonzero(all_bytes) / len(all_bytes)
        value_counts = np.bincount(all_bytes, minlength=256)
        probs = value_counts[value_counts > 0] / len(all_bytes)
        entropy = -np.sum(probs * np.log2(probs))
    else:
        non_zero_ratio = 0.0
        entropy = 0.0
    entropy_stats = np.array([entropy, non_zero_ratio]) # 2
    
    features = np.concatenate([payload_stats, dlc_stats, id_stats, entropy_stats])
    assert features.shape == (46,), f"CAN features shape is {features.shape}, expected (46,)"
    return features

def extract_veremi_features(window_df):
    """
    Extract exactly 46 features from a window of VeReMi messages.
    """
    # 18 raw features: type, rcvTime, pos_0, pos_1, pos_noise_0, pos_noise_1,
    # spd_0, spd_1, spd_noise_0, spd_noise_1, acl_0, acl_1, acl_noise_0,
    # acl_noise_1, hed_0, hed_1, hed_noise_0, hed_noise_1.
    cols = ['type', 'rcvTime', 'pos_0', 'pos_1', 'pos_noise_0', 'pos_noise_1',
            'spd_0', 'spd_1', 'spd_noise_0', 'spd_noise_1', 'acl_0', 'acl_1',
            'acl_noise_0', 'acl_noise_1', 'hed_0', 'hed_1', 'hed_noise_0', 'hed_noise_1']
    
    # Average motion (18): means
    means = window_df[cols].mean().fillna(0).values # 18
    
    # Fluctuation (18): stds
    stds = window_df[cols].std().fillna(0).values # 18
    
    # Derived forces (5): speed mag, accel mag, heading rate, pos mag, noise mag
    spd_mag = np.mean(np.sqrt(window_df['spd_0']**2 + window_df['spd_1']**2))
    acl_mag = np.mean(np.sqrt(window_df['acl_0']**2 + window_df['acl_1']**2))
    hed_rate = window_df['hed_0'].diff().abs().mean()
    if pd.isna(hed_rate): hed_rate = 0.0
    pos_mag = np.mean(np.sqrt(window_df['pos_0']**2 + window_df['pos_1']**2))
    noise_mag = np.mean(np.sqrt(window_df['pos_noise_0']**2 + window_df['pos_noise_1']**2))
    forces = np.array([spd_mag, acl_mag, hed_rate, pos_mag, noise_mag]) # 5
    
    # Behavior stats (5): spatial spread, inter-message time mean, IMT std, broadcast rate, rcvTime span
    pos_var = window_df['pos_0'].var() + window_df['pos_1'].var()
    spatial_spread = np.sqrt(pos_var) if pd.notna(pos_var) else 0.0
    
    rcv_times = window_df['rcvTime'].sort_values().values
    imt = np.diff(rcv_times)
    imt_mean = np.mean(imt) if len(imt) > 0 else 0.0
    imt_std = np.std(imt) if len(imt) > 0 else 0.0
    
    rcv_span = rcv_times[-1] - rcv_times[0] if len(rcv_times) > 0 else 0.0
    broadcast_rate = len(rcv_times) / rcv_span if rcv_span > 0 else 0.0
    
    behavior = np.array([spatial_spread, imt_mean, imt_std, broadcast_rate, rcv_span]) # 5
    
    features = np.concatenate([means, stds, forces, behavior])
    assert features.shape == (46,), f"VeReMi features shape is {features.shape}, expected (46,)"
    return features

def extract_cicids_features(window_df):
    """
    Extract exactly 46 features from a window of CICIDS flows.
    """
    # Define the 46 chosen columns
    transfer_rates = ['Flow Bytes/s', 'Flow Packets/s', 'Fwd Packets/s', 'Bwd Packets/s', 'Average Packet Size', 'Flow Duration']
    flow_sizes = ['Total Fwd Packets', 'Total Backward Packets', 'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
                  'Fwd Packet Length Max', 'Fwd Packet Length Min', 'Fwd Packet Length Mean', 'Fwd Packet Length Std',
                  'Bwd Packet Length Max', 'Bwd Packet Length Min', 'Bwd Packet Length Mean', 'Bwd Packet Length Std']
    time_gaps = ['Flow IAT Mean', 'Flow IAT Std', 'Flow IAT Max', 'Flow IAT Min', 'Fwd IAT Total', 'Fwd IAT Mean', 
                 'Fwd IAT Std', 'Fwd IAT Max', 'Fwd IAT Min', 'Bwd IAT Total', 'Bwd IAT Mean', 'Bwd IAT Std', 
                 'Bwd IAT Max', 'Bwd IAT Min', 'Active Mean']
    controls = ['Fwd PSH Flags', 'Bwd PSH Flags', 'Fwd URG Flags', 'Bwd URG Flags', 'Fwd Header Length', 'Bwd Header Length',
                'FIN Flag Count', 'SYN Flag Count', 'RST Flag Count', 'PSH Flag Count', 'ACK Flag Count', 'URG Flag Count', 'CWE Flag Count']
                
    chosen_cols = transfer_rates + flow_sizes + time_gaps + controls
    
    # Some columns might not exist exactly with these names due to spaces/casing
    # Create a mapping from clean lowercase name to actual name in df
    actual_cols = {c.strip().lower(): c for c in window_df.columns}
    
    means = []
    for col in chosen_cols:
        clean_col = col.strip().lower()
        if clean_col in actual_cols:
            val = window_df[actual_cols[clean_col]].replace([np.inf, -np.inf], np.nan).mean()
            means.append(val if pd.notna(val) else 0.0)
        else:
            means.append(0.0)
            
    features = np.array(means)
    assert features.shape == (46,), f"CICIDS features shape is {features.shape}, expected (46,)"
    return features

def get_extractor(dataset_name):
    if dataset_name == 'car_hack' or dataset_name == 'vtc_can':
        return extract_can_features
    elif dataset_name == 'veremi':
        return extract_veremi_features
    elif dataset_name == 'cicids':
        return extract_cicids_features
    else:
        raise ValueError(f"Unknown dataset {dataset_name}")
