import os, time, pickle, glob
import numpy as np
import tenseal as ts
from models.cheby_kan import ChebyshevKAN
from federated.fhe_adapter import build_ckks_context, CKKSVector
from federated.server import FederatedServer

NETWORK_DIR = "demo_network"
UPDATES_DIR = os.path.join(NETWORK_DIR, "updates")
os.makedirs(UPDATES_DIR, exist_ok=True)

# Clean up previous runs
for f in glob.glob(os.path.join(UPDATES_DIR, "*.pkl")): 
    os.remove(f)
if os.path.exists(os.path.join(NETWORK_DIR, "context.bin")): 
    os.remove(os.path.join(NETWORK_DIR, "context.bin"))
if os.path.exists(os.path.join(NETWORK_DIR, "global_model.npy")): 
    os.remove(os.path.join(NETWORK_DIR, "global_model.npy"))

print("======================================================")
print("             LG-IoV FEDERATED SERVER (RSU)            ")
print("======================================================")
print("[SERVER] Initializing Single-Key CKKS Context (N=8192, 128-bit security)...")
context = build_ckks_context()

# Save context for clients (Public + Secret Key since it's Single-Key CKKS)
with open(os.path.join(NETWORK_DIR, "context.bin"), "wb") as f:
    f.write(context.serialize(save_secret_key=True))

print("[SERVER] Initializing ChebyKAN Model for 'car_hack' dataset...")
model_kwargs = dict(
    dataset="car_hack", n_classes=5,
    hidden_dim=32, num_layers=2, degree=3, dropout=0.1
)
model = ChebyshevKAN(**model_kwargs)

server = FederatedServer(
    model=model, model_kwargs=model_kwargs,
    backend="ckks", disclosure="practical", 
    context=context, multikey=None, seed=2025
)

print(f"[SERVER] Model initialized. {server.model.num_parameters():,} parameters.")
initial_global = server.broadcast_global_model()
print(f"[SERVER] --------------------------------------------------")
print(f"[SERVER] TRANSPARENCY: Initial Global Model Weights (first 4):")
print(f"[SERVER] {np.round(initial_global[:4], 4)}")
print(f"[SERVER] --------------------------------------------------")
print("[SERVER] Broadcasting initial global model to clients...")
np.save(os.path.join(NETWORK_DIR, "global_model.npy"), initial_global)

EXPECTED_CLIENTS = 2
round_num = 1

while True:
    updates = glob.glob(os.path.join(UPDATES_DIR, "*.pkl"))
    if len(updates) >= EXPECTED_CLIENTS:
        print(f"\n{'='*54}")
        print(f"[SERVER] Received {len(updates)} encrypted updates for Round {round_num}")
        
        packages = []
        for u in updates:
            with open(u, "rb") as f:
                data = pickle.load(f)
            # Reconstruct CKKSVector from bytes
            chunks = [ts.ckks_vector_from(context, c) for c in data["enc_chunks"]]
            vec = CKKSVector(context, chunks=chunks, n_values=data["enc_n_values"], slot_count=data["enc_slot_count"])
            
            packages.append({
                "client_id": data["client_id"],
                "encrypted_update": vec,
                "sample_size": data["sample_size"],
                "n_parameters": data["n_parameters"]
            })
            os.remove(u)
        
        print(f"[SERVER] --------------------------------------------------")
        print(f"[SERVER] TRANSPARENCY: What does the server actually see?")
        for pkg in packages:
            print(f"[SERVER] Client {pkg['client_id']} payload: {type(pkg['encrypted_update'])}")
            print(f"[SERVER] Client {pkg['client_id']} values: [ ENCRYPTED CIPHERTEXT - CANNOT READ ]")
        print(f"[SERVER] --------------------------------------------------")
        
        print("[SERVER] Performing FheFL Homomorphic Aggregation...")
        print("[SERVER] Math: [d^u] = g^T*g + [(f^u - 2g)^T * f^u] (Calculated entirely in ciphertext)")
        t0 = time.time()
        # The magic happens here: distances computed without decryption
        diag = server.aggregate_round(packages)
        t1 = time.time()
        
        print(f"[SERVER] Encrypted Distances computed (zero individual updates decrypted)!")
        print(f"[SERVER] Revealed Distances to global model: {[round(d, 4) for d in diag['distances']]}")
        print(f"[SERVER] Math: p^u = 1 - (d^u / sum(d))")
        print(f"[SERVER] Computed Non-Poisoning Weights (p^u): {[round(w, 4) for w in diag['non_poisoning_rates']]}")
        print(f"[SERVER] Math: aggregate = sum(p^u * [f^u])")
        print(f"[SERVER] Homomorphic Weighted Sum completed in {t1-t0:.2f}s.")
        print(f"[SERVER] Decrypting the FINAL AGGREGATE only...")
        
        new_global = server.broadcast_global_model()
        print(f"[SERVER] --------------------------------------------------")
        print(f"[SERVER] TRANSPARENCY: Decrypted Global Model Weights (first 4):")
        print(f"[SERVER] {np.round(new_global[:4], 4)}")
        print(f"[SERVER] --------------------------------------------------")
        
        np.save(os.path.join(NETWORK_DIR, "global_model.npy"), new_global)
        print(f"[SERVER] Broadcasted new global model. Waiting for Round {round_num+1}...\n")
        round_num += 1
        
    time.sleep(1)
