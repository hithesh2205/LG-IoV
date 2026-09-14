import tenseal as ts
import os, glob

os.makedirs("updates", exist_ok=True)
for f in glob.glob("updates/*.pkl"):
    os.remove(f)

print("==================================================")
print("             KEY SETUP (TRUSTED DEALER)           ")
print("==================================================")
print("Generating Strict Single-Key CKKS Context...")
context = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60])
context.global_scale = 2**40
context.generate_galois_keys()
context.generate_relin_keys()

with open("secret_context.bin", "wb") as f:
    f.write(context.serialize(save_secret_key=True))

context.make_context_public()
with open("public_context.bin", "wb") as f:
    f.write(context.serialize())

print("SUCCESS: Keys generated in Strict_SingleKey_Demo/")
print("-> secret_context.bin (Contains Secret Key -> Sent to Clients)")
print("-> public_context.bin (No Secret Key -> Sent to Server)")
