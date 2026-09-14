import argparse
import os, time, pickle
import numpy as np
import torch
import tenseal as ts
from models.cheby_kan import ChebyshevKAN
from federated.fhe_adapter import encrypt_update, load_flat_into_model, flatten_model

parser = argparse.ArgumentParser()
parser.add_argument("--id", type=int, required=True, help="Vehicle ID")
args = parser.parse_args()

NETWORK_DIR = "demo_network"
UPDATES_DIR = os.path.join(NETWORK_DIR, "updates")
model_path = os.path.join(NETWORK_DIR, "global_model.npy")
context_path = os.path.join(NETWORK_DIR, "context.bin")

print(f"======================================================")
print(f"               VEHICLE CLIENT {args.id}               ")
print(f"======================================================")
print(f"[CLIENT {args.id}] Waiting for Server to broadcast CKKS context...")

while not os.path.exists(context_path):
    time.sleep(1)

print(f"[CLIENT {args.id}] Loading CKKS Context...")
with open(context_path, "rb") as f:
    context = ts.context_from(f.read())

# Initialize local model
model = ChebyshevKAN(dataset="car_hack", n_classes=5, hidden_dim=32, num_layers=2, degree=3, dropout=0.1)

last_mtime = 0
round_num = 1

while True:
    if os.path.exists(model_path):
        mtime = os.path.getmtime(model_path)
        if mtime > last_mtime:
            print(f"\n[CLIENT {args.id}] === ROUND {round_num} ===")
            print(f"[CLIENT {args.id}] Downloaded Plaintext Global Model.")
            last_mtime = mtime
            
            # Load broadcasted model
            global_flat = np.load(model_path)
            load_flat_into_model(model, global_flat)
            
            print(f"[CLIENT {args.id}] Training locally on vehicle CAN logs...")
            time.sleep(2) # Simulating local training time
            
            # Simulate SGD by adding random noise to weights
            with torch.no_grad():
                for p in model.parameters():
                    p.add_(torch.randn_like(p) * 0.05)
            
            flat = flatten_model(model)
            print(f"[CLIENT {args.id}] Training complete.")
            print(f"[CLIENT {args.id}] --------------------------------------------------")
            print(f"[CLIENT {args.id}] TRANSPARENCY: Plaintext weights (first 4):")
            print(f"[CLIENT {args.id}] {np.round(flat[:4], 4)}")
            print(f"[CLIENT {args.id}] --------------------------------------------------")
            print(f"[CLIENT {args.id}] Encrypting {flat.size:,} parameters with CKKS...")
            
            t0 = time.time()
            # Encrypt full update (packs 4096 reals per ciphertext chunk)
            enc = encrypt_update(flat, backend="ckks", context=context, levels_to_drop=1)
            t1 = time.time()
            
            print(f"[CLIENT {args.id}] Encryption took {t1-t0:.2f}s.")
            print(f"[CLIENT {args.id}] --------------------------------------------------")
            print(f"[CLIENT {args.id}] TRANSPARENCY: What is being sent to server?")
            print(f"[CLIENT {args.id}] Object type: {type(enc)}")
            print(f"[CLIENT {args.id}] Underlying data: {len(enc._chunks)} x {type(enc._chunks[0])}")
            print(f"[CLIENT {args.id}] Payload size: {enc.serialized_bytes() / 1024 / 1024:.2f} MB of ciphertext")
            print(f"[CLIENT {args.id}] --------------------------------------------------")
            print(f"[CLIENT {args.id}] Uploading to Server...")
            
            # Serialize for file-drop communication
            save_path = os.path.join(UPDATES_DIR, f"client_{args.id}.pkl")
            with open(save_path, "wb") as f:
                pickle.dump({
                    "client_id": args.id,
                    "sample_size": 1000,
                    "n_parameters": flat.size,
                    "enc_n_values": enc.n_values,
                    "enc_slot_count": enc.slot_count,
                    "enc_chunks": [c.serialize() for c in enc._chunks]
                }, f)
            
            print(f"[CLIENT {args.id}] Upload complete. Waiting for next round...")
            round_num += 1
            
    time.sleep(1)
