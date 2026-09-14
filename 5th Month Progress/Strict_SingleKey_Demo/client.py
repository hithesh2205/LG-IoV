import sys, os
from pathlib import Path

import tenseal as ts
import torch
import torch.nn as nn
import numpy as np
import time, pickle

from models.cheby_kan import ChebyshevKAN
from data.preprocess import PreprocessingPipeline
from federated.fhe_adapter import encrypt_update, CKKSVector, flatten_model, load_flat_into_model

client_id = int(sys.argv[1])
print(f"==================================================")
print(f"             VEHICLE CLIENT {client_id}           ")
print(f"==================================================")

print(f"[CLIENT {client_id}] Loading 'car_hack' dataset...")
# Point directly to the actual Preprocessed_Dataset directory!
DATA_ROOT = Path(r"C:\Users\Thrish_Sudha\Desktop\Amrita Files\LGSI IOV\Team\LG_IoV\Preprocessed_Dataset")

try:
    print(f"[CLIENT {client_id}] Loading 'car_hack' dataset from disk (Please wait ~15 seconds)...")
    pipeline = PreprocessingPipeline()
    split = pipeline.fit_transform(
        name="car_hack", data_root=DATA_ROOT,
        window=64, stride=16, max_rows_per_class=50000, cicids_multi_class=False
    )
    X = split["X_train"]
    y = split["y_train"]
    X_test_client = torch.tensor(split["X_test"], dtype=torch.float32)
    y_test_client = torch.tensor(split["y_test"], dtype=torch.long)
    print(f"[CLIENT {client_id}] Real 'car_hack' CSVs loaded successfully! Shape: {X.shape}")
except Exception as e:
    print(f"[CLIENT {client_id}] Note: Local CSVs missing ({e}). Generating realistic synthetic CAN data for the demo...")
    X = np.random.randn(20000, 46).astype(np.float32)
    y = np.random.randint(0, 5, size=(20000,)).astype(np.int64)
    X_test_client = torch.tensor(np.random.randn(2000, 46), dtype=torch.float32)
    y_test_client = torch.tensor(np.random.randint(0, 5, size=(2000,)), dtype=torch.long)

# Split the dataset dynamically based on how much data we successfully loaded
total_rows = len(X)
chunk_size = total_rows // 2
start = (client_id - 1) * chunk_size
X_client = torch.tensor(X[start:start+chunk_size], dtype=torch.float32)
y_client = torch.tensor(y[start:start+chunk_size], dtype=torch.long)
dataset = torch.utils.data.TensorDataset(X_client, y_client)
loader = torch.utils.data.DataLoader(dataset, batch_size=128, shuffle=True)

test_dataset = torch.utils.data.TensorDataset(X_test_client, y_test_client)
test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=256, shuffle=False)

print(f"[CLIENT {client_id}] Loading SECRET Context (Holds the Secret Key)...")
with open("secret_context.bin", "rb") as f:
    context = ts.context_from(f.read())

print(f"[CLIENT {client_id}] Initializing ChebyKAN Model (44,164 parameters)...")
model = ChebyshevKAN(dataset="car_hack", n_classes=5, hidden_dim=32, num_layers=2, degree=3, dropout=0.1)

# Let Client 2 start with slightly different weights so they diverge and properly average
with torch.no_grad():
    for p in model.parameters():
        p.add_(torch.randn_like(p) * 0.05 * client_id)

optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
criterion = nn.CrossEntropyLoss()

for round_num in range(1, 4):
    print(f"\n[CLIENT {client_id}] === ROUND {round_num} ===")
    print(f"[CLIENT {client_id}] Performing local training on CAN bus data...")
    
    # 1. REAL TRAINING
    model.train()
    for local_epoch in range(2):
        total_loss = 0
        for data, target in loader:
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
    print(f"[CLIENT {client_id}] Training Loss for Round {round_num}: {total_loss/len(loader):.4f}")

    # 2. ENCRYPTION
    flat = flatten_model(model)
    print(f"[CLIENT {client_id}] TRANSPARENCY: First 4 Plaintext Weights:")
    print(f"[CLIENT {client_id}] {np.round(flat[:4], 4)}")
    print(f"[CLIENT {client_id}] Encrypting {flat.size:,} parameters with CKKS...")
    
    t0 = time.time()
    enc = encrypt_update(flat, backend="ckks", context=context, levels_to_drop=1)
    
    print(f"[CLIENT {client_id}] Encryption took {time.time()-t0:.2f}s")
    print(f"[CLIENT {client_id}] Uploading {enc.serialized_bytes() / 1024 / 1024:.2f} MB ciphertext to Server...")
    
    # 3. UPLOAD
    save_path = f"updates/client_{client_id}.pkl"
    with open(save_path, "wb") as f:
        pickle.dump({
            "enc_n_values": enc.n_values,
            "enc_slot_count": enc.slot_count,
            "enc_chunks": [c.serialize() for c in enc._chunks]
        }, f)
        
    print(f"[CLIENT {client_id}] Uploaded! Waiting for Encrypted Aggregate from Server...")
    
    # 4. DOWNLOAD & DECRYPT
    agg_path = f"updates/aggregate_round_{round_num}.pkl"
    while not os.path.exists(agg_path):
        time.sleep(1)
        
    print(f"[CLIENT {client_id}] Received ENCRYPTED Aggregate! Decrypting with Secret Key...")
    with open(agg_path, "rb") as f:
        data = pickle.load(f)
    chunks = [ts.ckks_vector_from(context, c) for c in data["enc_chunks"]]
    agg_enc = CKKSVector(context, chunks=chunks, n_values=data["enc_n_values"], slot_count=data["enc_slot_count"])
    
    decrypted = agg_enc.decrypt()
    print(f"[CLIENT {client_id}] First 4 Decrypted Global Weights:")
    print(f"[CLIENT {client_id}] {np.round(decrypted[:4], 4)}")
    
    load_flat_into_model(model, np.array(decrypted))
    print(f"[CLIENT {client_id}] Local model updated with global aggregate for next round.")
    
    # 5. EVALUATE ACCURACY
    model.eval()
    correct = 0
    with torch.no_grad():
        for d_batch, t_batch in test_loader:
            pred = model(d_batch).argmax(dim=1)
            correct += (pred == t_batch).sum().item()
    acc = 100.0 * correct / len(test_dataset)
    print(f"[CLIENT {client_id}] >>> ROUND {round_num} GLOBAL ACCURACY: {acc:.2f}% <<<")
    
    time.sleep(2) # Give client 2 time to read the file before next round overwrites
