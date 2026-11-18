# Homomorphic Functions ($f$) in CKKS-Encrypted Federated Learning with ChebyKAN
**A Technical Reference Guide & Architecture Analysis for Collaborative Vehicular Intrusion Detection (IoV)**

---

## 1. Executive Summary & Context of the Meeting

### 1.1 The Meeting Dialogue & The Core Misunderstanding
During the technical review with LGSI mentor **Fahiem Altaf** and **Dr. Praveen K**, the following exchange took place regarding the role of the homomorphic function:

> **Thrishwant:** *"If the server knows how the homomorphic function works, then there is no need of keeping the homomorphic function. It can be simple."*  
> **Fahiem Altaf:** *"I didn't understand you exactly."*  
> **Dr. Praveen K:** *"Yes, sir, we will see that function and broadcasting certain group key thing, yeah."*

### 1.2 Demystifying the Confusion: Kerckhoffs’s Principle & FHE
The confusion arose from a fundamental collision between **what is kept secret** and **what is computed publicly**:

1. **The Function $f$ is NOT Secret:**  
   In modern cryptography (**Kerckhoffs’s Principle**), security must never depend on the algorithm being hidden. The server is untrusted with the **data**, but it is **not blind to its computational task**. The server is explicitly programmed to compute a specific task:
   $$f(w_1, w_2, \dots, w_N) = \frac{1}{N} \sum_{i=1}^N w_i \quad \text{or} \quad f(w_i, g) = \|w_i - g\|^2$$
2. **Why We Cannot "Make It Simple" (Remove the Homomorphic Function):**  
   If the server computes $f$ "simply" using standard plaintext math, the vehicles would have to transmit unencrypted model weights $w_i$. This completely defeats privacy—the untrusted RSU (Roadside Unit) could invert the weights to reconstruct private vehicle driving trajectories, telemetry, or CAN bus traffic.
3. **The Role of FHE:**  
   Fully Homomorphic Encryption (FHE) allows the server to evaluate the public function $f$ directly on encrypted data:
   $$\text{Eval}(pk, f, [w_1], \dots, [w_N]) \longrightarrow [f(w_1, \dots, w_N)]$$
   The server calculates the exact result of $f$ without ever knowing what the numbers inside the ciphertexts actually are.

---

## 2. Deconstructing the LG Mentor's Architecture Diagram

The mentor shared the following architecture depicting the strict boundary between the **Client Domain** and the **Untrusted Server Domain**:

```
+-------------------------------------------------------------+
|                        CLIENT DOMAIN                        |
|              (Possesses Secret Decryption Key sk)           |
+------------------------------+------------------------------+
                               |
                      [1] Local Plaintext Data (w_i)
                               v
                       ( Encrypts locally )
                               |
                               v
                      [2] Secure Ciphertext [w_i]
                               |
+------------------------------|------------------------------+
|   UNTRUSTED SERVER DOMAIN    |   (Transmits over V2X/Network)
|   (No Decryption Key sk)     v                              |
|                              |                              |
|                    +---------+---------+                    |
|                    | Receives [w_i]    |                    |
|                    +---------+---------+                    |
|                              |                              |
|                              v                              |
|                    +---------+---------+                    |
|                    | Computes Function |  <--- THIS IS f    |
|                    | f([w_1], ..., [w_N])|   (e.g., FedAvg) |
|                    +---------+---------+                    |
|                              |                              |
|                              v                              |
|                    +---------+---------+                    |
|                    | Result Ciphertext |                    |
|                    | [w_global]        |                    |
|                    +---------+---------+                    |
|                              |                              |
+------------------------------|------------------------------+
                               |
                      [4] Transmits Aggregate Back
                               v
                       ( Decrypts locally )
                               |
                               v
                      [5] Final Plaintext Result (w_global)
```

### Key Architectural Invariants:
1. **Zero Knowledge on Server:** The server receives only public evaluation keys $pk$ and ciphertexts $[w_i]$. It has **zero access** to the secret key $sk$.
2. **Homomorphic Evaluation ($f$):** The server's sole purpose is executing the mathematical circuit $f(\cdot)$ over ciphertexts.
3. **Decryption Exclusively in Client Domain:** Only participating vehicles (or a collaborative threshold committee) can decrypt the aggregated result $[w_{\text{global}}]$.

---

## 3. Cryptographic Grounding: Page 424 of `BookCKKS.pdf`

Fahiem Altaf directed the team to **Book Page 424** of the reference material (`BookCKKS.pdf`, which is Cheon, Kim, Kim, and Song's seminal paper: *"Homomorphic Encryption for Arithmetic of Approximate Numbers"*, ASIACRYPT 2017).

On **Page 424 (Section 4)**, the authors formally define how an arbitrary function $f$ is evaluated in CKKS:

```
Section 4: Homomorphic Evaluation of Functions
  4.1 Polynomial Functions
```

### 3.1 Constant Addition and Multiplication (Lemma 4, Page 424)
Any function of the form $f(x) = x + a$ or $f(x) = a \cdot x$ for a public constant $a \in \mathcal{R}$ is evaluated directly on ciphertext $c = (c_0, c_1)$:
- **Constant Addition:** $c_a \leftarrow c + (a, 0) \pmod{q_\ell}$
- **Constant Multiplication:** $c_m \leftarrow a \cdot c \pmod{q_\ell}$
*Multiplicative Depth consumed: **0**.*

### 3.2 Power Polynomials & Rescaling (Algorithm 1, Page 424)
To evaluate non-linear functions of the form $f(x) = x^d$ where $d = 2^r$:
```python
procedure Power(c, d = 2^r):
    c_0 = c
    for j = 1 to r do:
        c_j = Rescale(Mult(c_{j-1}, c_{j-1}))
    return c_r
```
*Each squaring step consumes **1 modulus level** via the Rescaling ($\mathsf{RS}$) procedure.*

### 3.3 General Polynomials & Analytic Functions (Lemmas 6, 7 & Section 4.2)
Any smooth function $f(x)$ (such as an activation function, loss function, or distance metric) is expressed as a polynomial:
$$f(x) = \sum_{i=0}^d a_i x^i$$
In CKKS, evaluating $f$ means converting the function into an arithmetic circuit composed strictly of:
1. Homomorphic additions ($+$)
2. Homomorphic scalar multiplications ($\cdot$)
3. Ciphertext $\times$ ciphertext multiplications ($\otimes$) followed by rescaling ($\mathsf{RS}$)

---

## 4. Comprehensive Taxonomy of $f$ Functions for CKKS + FL + ChebyKAN

In our system, what functions $f$ can the server evaluate?

```
                     ┌────────────────────────────────────────────────────────┐
                     │           HOMOMORPHIC FUNCTIONS f IN FedIoV            │
                     └───────────────────────────┬────────────────────────────┘
                                                 │
         ┌────────────────────────┬──────────────┴───────────┬────────────────────────┐
         │                        │                          │                        │
         ▼                        ▼                          ▼                        ▼
 1. Model Aggregation     2. Byzantine Defenses     3. ChebyKAN Specific     4. Encrypted Inference
  • Homomorphic FedAvg     • Squared Euclidean Dist   • High-Degree Damping    • Native Forward Pass
  • FedProx Anchoring      • Cosine Similarity        • Spline vs Trunk Split  • Blind Classification
  • Server Momentum        • Smooth Outlier Weighting
```

---

### Category 1: Model Aggregation Functions ($f_{\text{agg}}$)

These functions combine local encrypted parameter vectors $[w_k]$ from $K$ vehicles into the global update $[w_{\text{global}}]$.

#### 1. Homomorphic FedAvg (Baseline — Currently Implemented)
* **Mathematical Definition:**
  $$f_{\text{FedAvg}}([w_1], \dots, [w_K]) = \sum_{k=1}^K \alpha_k [w_k]$$
  where $\alpha_k = \frac{n_k}{\sum n_i}$ or $\frac{1}{K}$.
* **CKKS Operations:** Plaintext-scalar multiplication and ciphertext additions.
* **Modulus Levels Consumed:** **0 levels**.
* **Measured Benchmark:** $\approx 5\text{ ms}$ for 44,164 parameters across 11 ciphertext chunks.

#### 2. Homomorphic FedProx / Elastic Anchoring ($f_{\text{FedProx}}$)
* **Purpose:** Counteracts client drift caused by non-IID vehicular traffic (e.g., highway vs. urban CAN data).
* **Mathematical Definition:**
  $$f_{\text{FedProx}}([w_{\text{agg}}], g^{(t)}) = (1 - \gamma) g^{(t)} + \gamma [w_{\text{agg}}]$$
  where $g^{(t)}$ is the previous global model (held in plaintext by the RSU).
* **CKKS Operations:** Ciphertext addition with a plaintext vector.
* **Modulus Levels Consumed:** **0 levels**.

#### 3. Homomorphic Server Momentum ($f_{\text{FedMom}}$)
* **Purpose:** Accelerates training convergence across rounds directly in the encrypted domain.
* **Mathematical Definition:**
  $$[v^{(t)}] = \beta v^{(t-1)} + (1 - \beta) [\Delta w_{\text{agg}}]$$
  $$[w^{(t+1)}] = w^{(t)} + [v^{(t)}]$$
* **Modulus Levels Consumed:** **0 levels**.

---

### Category 2: Byzantine-Resilient Defenses ($f_{\text{def}}$)

Vehicles in an IoV network can be compromised to inject poisoning updates. Since the server cannot decrypt updates to inspect them or use non-polynomial functions like `if-else` / `sort` / `median`, it evaluates algebraic scoring functions:

#### 1. FheFL Squared Euclidean Distance ($f_{\text{dist}}$) — *(Implemented in Code)*
* **Purpose:** Measures parameter deviation from the global model without decrypting weights.
* **Mathematical Definition:**
  $$f_{\text{dist}}([w_k], g) = \|w_k - g\|^2 = g^T g + [(w_k - 2g)^T w_k]$$
* **CKKS Operations:** Ciphertext-plaintext linear combination followed by **one ciphertext $\times$ ciphertext inner product** and slot rotations.
* **Modulus Levels Consumed:** **1 level** (consumed safely within the 2-level budget of $N=8192$).
* **Measured Latency:** $\approx 18\text{ ms}$ per vehicle update.

#### 2. Clean-Anchor Cosine Similarity ($f_{\text{cos}}$)
* **Purpose:** Checks whether a vehicle's update aligns with a clean validation gradient computed on a verified RSU dataset:
  $$f_{\text{cos}}([w_k], v_{\text{anchor}}) = \frac{\langle [w_k], v_{\text{anchor}} \rangle}{\|v_{\text{anchor}}\|^2}$$
* **CKKS Operations:** Ciphertext-plaintext inner product (no ciphertext-ciphertext multiply).
* **Modulus Levels Consumed:** **0 levels**.
* **Advantage:** Faster than Euclidean distance; does not consume any multiplicative depth.

#### 3. Continuous Outlier Weighting ($f_{\text{weight}}$)
* **Purpose:** Replaces hard threshold rejection with a smooth polynomial decay:
  $$f_{\text{weight}}([d_k]) \approx \exp\left(-\frac{d_k^2}{2\sigma^2}\right) \approx 1 - c_1 [d_k] + c_2 [d_k]^2$$
  $$[w_{\text{global}}] = \sum_{k=1}^K [f_{\text{weight}}(d_k)] \otimes [w_k]$$
* **Modulus Levels Consumed:** **2 levels** (requires the 3-prime / $N=16384$ parameter profile).

---

### Category 3: ChebyKAN-Specific Functions ($f_{\text{KAN}}$)

ChebyKAN models replace traditional weight matrices with learnable univariate functions parameterized by Chebyshev polynomials:
$$\phi(x) = w_b \cdot x + \sum_{j=0}^D c_j T_j(x)$$
where $T_0(x)=1, T_1(x)=x, T_2(x)=2x^2-1, T_3(x)=4x^3-3x, \dots$

This architectural property enables ChebyKAN-tailored homomorphic functions:

#### 1. High-Degree Coefficient Regularization / Damping ($f_{\text{damp}}$)
* **Problem:** Adversarial vehicles manipulate higher-order polynomial coefficients ($T_3, T_4$) to induce Runge's oscillation phenomenon, degrading global accuracy.
* **The Function:** The RSU applies a homomorphic damping function that penalizes higher degrees:
  $$f_{\text{damp}}([c_j]) = \lambda_j \cdot [c_j] \quad \text{where } \lambda_j = \frac{1}{1 + \eta \cdot j^2}$$
* **Modulus Levels Consumed:** **0 levels** (plaintext scalar multiplication).
* **Paper Value:** A novel defense mechanism tailored specifically to KANs in federated settings.

#### 2. Trunk vs. Spline Modular Aggregation ($f_{\text{split}}$)
* **The Function:** The server splits aggregation policies:
  - Base linear weights $[w_b]$: Aggregated with standard FedAvg across the entire fleet.
  - Chebyshev polynomial coefficients $[c_j]$: Aggregated using distance-weighted robust averaging to preserve non-linear decision boundaries.

---

### Category 4: Encrypted ChebyKAN Inference ($f_{\text{infer}}$)
*The Theoretical Synergy between ChebyKAN and CKKS*

| Model Type | Activation Function | Homomorphic Feasibility in FHE |
|---|---|---|
| **Standard MLP / CNN** | $\text{ReLU}(x) = \max(0, x)$ | **Severe Bottleneck:** ReLU is non-smooth. Requires degree 7–15 polynomial approximation (consuming 3–4 modulus levels and introducing approximation error). |
| **ChebyKAN** | Chebyshev Basis $T_j(x)$ | **Natively Homomorphic:** ChebyKAN basis functions are polynomials by definition. Evaluated exactly using the Clenshaw recurrence relation: $T_{j+1}(x) = 2x T_j(x) - T_{j-1}(x)$. |

Because ChebyKAN is built purely on polynomial arithmetic, an RSU can evaluate **encrypted inference on encrypted CAN telemetry packets $[x]$** using the exact recurrence logic of Algorithm 1 (Page 424 of `BookCKKS.pdf`) without needing activation approximations!

---

## 5. Comparative Function Summary Table

| Function Name | Formal Notation | Depth | Latency | Status in Codebase |
|---|---|:---:|:---:|---|
| **Homomorphic FedAvg** | $\sum \alpha_k [w_k]$ | 0 | $\approx 5\text{ ms}$ | ✅ Fully implemented (`server.py`) |
| **FedProx Anchoring** | $(1-\gamma)g + \gamma [w_{\text{agg}}]$ | 0 | $<1\text{ ms}$ | 🟢 Readily integrable |
| **Squared Distance (FheFL)** | $g^Tg + [(w_k - 2g)^Tw_k]$ | 1 | $\approx 18\text{ ms}$ | ✅ Fully implemented (`fhe_adapter.py`) |
| **Cosine Similarity** | $\langle [w_k], v_{\text{clean}} \rangle / \|v\|^2$ | 0 | $\approx 3\text{ ms}$ | 🟢 High-value addition |
| **High-Degree Damping** | $\lambda_j [c_j]$ | 0 | $<1\text{ ms}$ | 🟢 ChebyKAN-specific novelty |
| **Strict Outlier Weighting** | $\sum [w_k(d_k)] \otimes [w_k]$ | 2 | $\approx 68\text{ ms}$ | 🟡 Modeled; requires $N=16384$ |
| **Encrypted ChebyKAN Forward** | $\sum c_j T_j([x])$ | $\lceil \log_2 D \rceil$ | $\approx 45\text{ ms}$ | 📘 Theoretical grounding (Pg 424) |

---

## 6. Comprehensive Project Gap Analysis ("Where We Lag")

Based on the meeting transcript, the LG mentor's diagram, and the codebase:

```
[1. Key Management]  Single-Key CKKS in code ──> Need Multi-Key xMK-CKKS (Praveen's point)
[2. Trust Boundary]  server.py calls acc.decrypt() ──> Diagram mandates Server has NO sk
[3. Protocol Mode]   disclosure="strict" raises NotImplementedError ──> Using "practical"
[4. Wire Bandwidth]  2.47 MB per update (915 DSRC frames) ──> Serialization spec open
[5. Vehicle Dropout] 10 clients / 5 rounds ──> Scale to 50+ clients with dropout handling
[6. VeReMi Dataset]  Accuracy near chance ──> Sender ID stripped during preprocessing
[7. Quantization]    INT8 model quantization not started
```

### Gap 1: Key Distribution & Trust Boundary (Praveen's "Group Key Broadcast")
* **Current State:** Implemented as **Single-Key CKKS** with a simulated Trusted Dealer distributing one secret key $sk$ to all vehicles.
* **The Flaw:** If a single vehicle ECU is compromised, the attacker can decrypt every other vehicle's update off the air.
* **The Target:** True **Multi-Key CKKS (xMK-CKKS)** where each vehicle holds private key $s_i$, the server aggregates over joint public key $\tilde{P}$, and decryption is collaborative via partial decryption shares.

### Gap 2: Server-Side Decryption in Simulation
* **Current State:** In `server.py` (line 269), `acc.decrypt()` is called directly inside the server object because TenSEAL shares the context.
* **The Flaw:** Violates the LG mentor's diagram where the server has **NO secret key**.
* **The Target:** Separate the server into a blind aggregator that returns $[w_{\text{global}}]$ to the client domain.

### Gap 3: "Strict" vs "Practical" Mode in FheFL
* **Current State:** `server.py` line 125 throws `NotImplementedError` for `strict` mode. The code falls back to `practical` mode, which reveals 1 distance scalar per client per round to compute weights in plaintext.
* **The Target:** Document this trade-off clearly: `practical` mode leaks 1 scalar vs. 44,164 parameters, saving 4× computation latency.

### Gap 4: V2X Communication Bandwidth
* **Current State:** An encrypted 44k ChebyKAN update expands to **2.47 MB** on the wire.
* **The Flaw:** A standard DSRC/C-V2X channel cannot support 180 MB per round for a 50-vehicle fleet.
* **The Target:** Implement level-dropped transmission (29.6% reduction achieved), seed compression, and hierarchical RSU aggregation.

### Gap 5: VeReMi Dataset Defect
* **Current State:** VeReMi accuracy is near chance (~50%).
* **The Flaw:** When cleaning the dataset, the `sender_id` column was dropped, eliminating the temporal trajectory information needed to detect position-falsification attacks.
* **The Target:** Re-acquire the raw dataset preserving `sender_id`.

---

## 7. Action Checklist for the October 5th Review Meeting

### How to Present to Fahiem Altaf and Dr. Praveen K:
1. **Clarify the Function ($f$):**  
   *"To clarify our discussion from the previous meeting: the server is intentionally aware of the function $f$, but oblivious to the data. In our pipeline, $f$ consists of homomorphic FedAvg (depth 0) and FheFL squared distance calculation (depth 1), strictly complying with Section 4 (Page 424) of the Cheon et al. 2017 CKKS paper."*
2. **Present the ChebyKAN + CKKS Advantage:**  
   *"Unlike standard MLPs that require lossy polynomial approximations for non-linear activations like ReLU, ChebyKAN’s activation functions are Chebyshev polynomials by construction. This makes ChebyKAN natively compatible with CKKS arithmetic circuits."*
3. **Address Key Broadcasting (Praveen's Question):**  
   *"We have modeled xMK-CKKS key masking where pairwise secrets cancel out over the participating set ($\sum ss_u = \sum s_u = s$), ensuring no individual update can be decrypted even if the server colludes with up to $K-2$ vehicles."*
4. **Present the Baseline Result:**  
   *"Our baseline confirms that CKKS homomorphic evaluation introduces zero accuracy loss ($<0.07$ pp difference from plaintext) across all benchmarks."*
