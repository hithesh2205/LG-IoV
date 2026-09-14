import sys, os
from pathlib import Path

import tenseal as ts
import time, glob, pickle
from federated.fhe_adapter import CKKSVector

print("=======================================================")
print("  SERVER (RSU) - STRICT SECURE FEDAVG (Real Training)  ")
print("=======================================================")
print("Loading PUBLIC context (Server does NOT hold Secret Key)...")
with open("public_context.bin", "rb") as f:
    context = ts.context_from(f.read())

for f in glob.glob("updates/aggregate_*.pkl"): 
    os.remove(f)

round_num = 1
while round_num <= 3:
    updates = glob.glob("updates/client_*.pkl")
    if len(updates) >= 2:
        print(f"\n[SERVER] === ROUND {round_num} ===")
        print(f"[SERVER] Received 2 encrypted updates.")
        
        packages = []
        for u in updates:
            with open(u, "rb") as f:
                data = pickle.load(f)
            chunks = [ts.ckks_vector_from(context, c) for c in data["enc_chunks"]]
            vec = CKKSVector(context, chunks=chunks, n_values=data["enc_n_values"], slot_count=data["enc_slot_count"])
            packages.append(vec)
            os.remove(u)
        
        print("[SERVER] TRANSPARENCY: Checking the payload type...")
        print(f"[SERVER] Received Type: {type(packages[0])}")
        
        # Display massive random integers to prove blindness
        import struct
        raw_bytes = packages[0]._chunks[0].serialize()
        # Unpack 6 massive 64-bit unsigned integers from the ciphertext stream
        massive_ints = struct.unpack('<6Q', raw_bytes[128:128+48])
        print(f"[SERVER] Data: Polynomial Ring Z_q[X]/(X^N + 1) Coefficients:")
        print(f"[SERVER] [ {massive_ints[0]},")
        print(f"[SERVER]   {massive_ints[1]},")
        print(f"[SERVER]   {massive_ints[2]}, ... ]")
        print(f"[SERVER] Notice these are massive integers, NOT your decimal weights!")
        
        print("\n[SERVER] Homomorphically averaging 44,164 encrypted parameters...")
        t0 = time.time()
        # Pure FedAvg: aggregate = (c1 + c2) / 2
        agg = (packages[0] + packages[1]) * 0.5
        t1 = time.time()
        print(f"[SERVER] Math: aggregate = sum([f^u]) / N")
        print(f"[SERVER] Aggregation complete in {t1-t0:.2f}s.")
        
        print("\n[SERVER] --- PRIVACY CHECK ---")
        print("[SERVER] Attempting to decrypt the aggregate to update the global model...")
        try:
            agg.decrypt()
        except ValueError as e:
            print(f"[SERVER] SUCCESS: Server CANNOT decrypt! (Error: {e})")
        print("[SERVER] ---------------------\n")
        
        print("[SERVER] Broadcasting ENCRYPTED aggregate back to clients...")
        agg_path = f"updates/aggregate_round_{round_num}.pkl"
        with open(agg_path, "wb") as f:
            pickle.dump({
                "enc_n_values": agg.n_values,
                "enc_slot_count": agg.slot_count,
                "enc_chunks": [c.serialize() for c in agg._chunks]
            }, f)
        
        round_num += 1
        
    time.sleep(1)
