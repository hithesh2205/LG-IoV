import pytest
import numpy as np
import torch
import tenseal as ts
from model import ChebyKAN
from fhe_engine import DesignatedDecryptor, encrypt_tensor
from aggregation import homomorphic_multi_krum_distances, multi_krum_select
import pandas as pd
from preprocessing import PreprocessingPipeline

def test_model_params():
    model = ChebyKAN(in_features=46, hidden_features=64, num_classes=4, degree=5)
    total = sum(p.numel() for p in model.parameters() if p.requires_grad)
    assert total == 44164

def test_server_no_secret_key():
    decryptor = DesignatedDecryptor()
    public_context = decryptor.get_public_context()
    assert not public_context.has_secret_key()

def test_multi_krum_rejection():
    # Setup
    decryptor = DesignatedDecryptor()
    public_context = decryptor.get_public_context()
    
    # 4 clients, f=1 (expect 1 rejection)
    # 3 normal, 1 malicious
    normal_tensor = torch.ones((10, 10))
    malicious_tensor = normal_tensor * 50.0
    
    clients_data = []
    for i in range(3):
        # Add slight noise to normal so distances aren't exactly 0
        noisy_tensor = normal_tensor + torch.randn_like(normal_tensor)*0.1
        enc = encrypt_tensor(noisy_tensor, public_context)
        clients_data.append({'layer': enc})
        
    # Add malicious client
    enc_malicious = encrypt_tensor(malicious_tensor, public_context)
    clients_data.append({'layer': enc_malicious})
    
    # Homomorphic Krum
    enc_distances = homomorphic_multi_krum_distances(clients_data)
    
    # Decrypt
    dec_distances = np.zeros((4, 4))
    for i in range(4):
        for j in range(i+1, 4):
            enc_distances[i][j].link_context(decryptor.context)
            val = enc_distances[i][j].decrypt()[0]
            dec_distances[i][j] = val
            dec_distances[j][i] = val
            
    selected_idx, rejected_idx, scores = multi_krum_select(dec_distances, 4, f=1)
    
    # The last client (index 3) should be rejected
    assert 3 in rejected_idx
    assert len(rejected_idx) == 1

def test_no_leakage_and_bounds():
    # Mock data
    df = pd.DataFrame({
        'session_id': [f"sess_{i}" for i in range(100) for _ in range(100)], # 100 sessions, 100 length each
        'label': ['Normal'] * 10000,
        'b0': np.random.randint(0, 255, 10000),
        'b1': np.random.randint(0, 255, 10000),
        'b2': np.random.randint(0, 255, 10000),
        'b3': np.random.randint(0, 255, 10000),
        'b4': np.random.randint(0, 255, 10000),
        'b5': np.random.randint(0, 255, 10000),
        'b6': np.random.randint(0, 255, 10000),
        'b7': np.random.randint(0, 255, 10000),
        'dlc': [8] * 10000,
        'can_id': ['0350'] * 10000
    })
    
    pipeline = PreprocessingPipeline(window_size=64, stride=16, n_clients=10, alpha=0.3)
    train_df, val_df, test_df = pipeline._split_sessions(df)
    
    # Verify split assertion (implicitly tested in pipeline but let's re-verify)
    train_sess = set(train_df['session_id'])
    val_sess = set(val_df['session_id'])
    test_sess = set(test_df['session_id'])
    
    assert len(train_sess.intersection(val_sess)) == 0
    assert len(train_sess.intersection(test_sess)) == 0
    
    from features import extract_can_features
    X_train_raw, y_train_raw, _ = pipeline._window_and_extract(train_df, extract_can_features)
    
    if len(X_train_raw) > 0:
        pipeline._fit_scale(X_train_raw)
        X_train = pipeline._transform_scale(X_train_raw)
        
        # Verify bounds
        assert np.all(X_train >= -1.0)
        assert np.all(X_train <= 1.0)
        assert not np.isnan(X_train).any()
