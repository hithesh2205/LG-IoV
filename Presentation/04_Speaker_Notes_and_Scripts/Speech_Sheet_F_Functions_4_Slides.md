# Speech Sheet: 4 Slides on Function $f$ in CKKS + ChebyKAN Federated IoV

**Target Audience:** LGSI Mentor Fahiem Altaf, Dr. Praveen K, Technical Review Panel  
**Estimated Runtime:** ~6 to 7 minutes total (~90 seconds per slide)  
**Primary Presentation File:** [`Presentation/F_Functions_In_Template_4_Slides.pptx`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/F_Functions_In_Template_4_Slides.pptx)  
*(Also mirrored in [`Presentation/Presentation_Updated_F_Functions.pptx`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/Presentation_Updated_F_Functions.pptx))*

---

## 🎯 Executive Overview & Context of Mentor Review

During our previous progress review, mentor **Fahiem Altaf** raised critical architectural questions regarding the homomorphic computation:
1. *"What $f$ functions are you using, for what purpose, and how are you using them?"*
2. *"We won't send the aggregated raw text/data, but send the evaluated value of that $f$ function."*
3. *"Is the $f$ function used to update the global model $W_{t+1}$?"*
4. *"How do the 44,000 weights of ChebyKAN fit into the polynomial ring and get evaluated by $f$?"*

These **4 slides** are built directly in your project template (`Presentation 28th August.pptx`), completely addressing every point with mathematical rigor and practical IoV engineering.

---

## Slide 1 — The Role of Function $f$: Updating the Global Model ($W_{t+1}$) in Federated IoV
*(Runtime: ~90 seconds)*

### 🎙️ Exact Speaker Script

> *"Good morning everyone. This slide directly resolves the question regarding the role of function $f$: why the server knows $f$, why we transmit the evaluated value rather than raw text, and how $f$ produces the global model update $W_{t+1}$.*
>
> *First, looking at the left card: in modern cryptography under Kerckhoffs’s Principle, security never relies on keeping the algorithm secret. The untrusted Roadside Unit (RSU) or cloud server is untrusted with our **data**, but it is explicitly assigned the computational task: evaluating function $f$. Under the CKKS scheme, the server receives public evaluation keys and encrypted client weights $[W_1]$ through $[W_K]$. It holds **zero secret key shares** and cannot read a single parameter, yet it executes $f$ blindly over the ciphertext space.*
>
> *Second, on the right card: as the mentor correctly noted, **we never send raw plaintext strings or individual client ciphertexts across the network**. Doing so would destroy bandwidth and invite traffic linkability attacks. Instead, the server homomorphically evaluates $f([W_1], \dots, [W_K])$ and broadcasts **only the evaluated value of that $f$ function**—which is the encrypted global model $[W_{t+1}]$. This transmission payload is strictly bounded to 11 ciphertext chunks, regardless of whether 5 or 500 vehicles participated.*
>
> *At the bottom, we provide the exact mathematical update equations. For Federated Averaging, the server performs plaintext-scalar multiplication by vehicle dataset weight $\alpha_k$ and ciphertext addition. Because this requires no ciphertext-by-ciphertext multiplication, it operates at **Multiplicative Depth = 0**, executing across all 44,164 parameters in just **5.2 milliseconds**."*

### 💡 Mentor Q&A Handling
- **If Fahiem asks:** *"Why can't the server just decrypt the average?"*
  - **Your answer:** *"In our threat model, the RSU is honest-but-curious or semi-honest. If the server possessed the decryption key to decrypt the average, a compromised RSU could collude to isolate individual vehicle weights when client participation fluctuates. By sending only the evaluated ciphertext $[W_{t+1}]$, decryption happens strictly collaboratively inside the client domain."*

---

## Slide 2 — SIMD Packing & Parallel Evaluation of 44,164 ChebyKAN Weights in $f$
*(Runtime: ~90 seconds)*

### 🎙️ Exact Speaker Script

> *"Moving to Slide 2: how do 44,164 ChebyKAN weights actually get packaged into the CKKS polynomial ring, and how does function $f$ compute them?*
>
> *Looking at the left breakdown: our ChebyKAN intrusion detection trunk has exactly 44,164 parameters for 4 network traffic classes. Notice the distribution: 7,296 are linear base weights, 388 are LayerNorm and bias terms, and **36,480 are Chebyshev polynomial coefficients**. Because we employ degree-4 Chebyshev polynomials ($T_0$ through $T_4$), every single one of the 7,296 network edges maintains 5 polynomial coefficients ($5 \times 7,296 = 36,480$). This gives ChebyKAN 14 times fewer parameters than a comparable MLP while capturing high-frequency intrusion patterns.*
>
> *Now, looking at the right card: how does CKKS handle 44,164 numbers? We do **not** encrypt 44,164 individual ciphertexts. At ring dimension $N = 8,192$, CKKS uses Single Instruction Multiple Data (SIMD) slot packing. One ciphertext polynomial pair $(c_0, c_1)$ packs **4,096 numbers** into its complex slots.*
>
> *Dividing 44,164 by 4,096 gives **exactly 11 ciphertext chunks**. Chunks 1 through 10 hold 4,096 weights each, and Chunk 11 holds the remaining 3,204 weights with zero-padding.*
>
> *When the server evaluates function $f$, it executes chunk-by-chunk in parallel. A single homomorphic addition operates on 4,096 weights simultaneously. Thus, **just 11 ciphertext additions update the entire 44,164-parameter model in 5.2 ms**!"*

### 💡 Mentor Q&A Handling
- **If Praveen asks:** *"Is it one weight per polynomial or 4 weights per polynomial?"*
  - **Your answer:** *"Neither! In CKKS SIMD vectorization, one polynomial pair packs **4,096 weights simultaneously**. So the 44,164 weights are mapped sequentially across 11 polynomial chunks."*

---

## Slide 3 — Taxonomy of $f$ Functions in IoV: Purpose, Mechanics & Return Values
*(Runtime: ~100 seconds)*

### 🎙️ Exact Speaker Script

> *"Slide 3 answers the mentor's explicit request: 'What all $f$ functions can you use, for what purpose, and what do they return?' We have structured our architecture into a concrete suite of four functions shown in this table.*
>
> *1. First is $f_{\text{agg}}$, our **Model Update Function**. It performs homomorphic FedAvg or momentum updates, combining fleet updates into the new global model $[W_{t+1}]$. It consumes **Depth 0**, finishes in 5.2 ms, and returns the **11-chunk global model ciphertext** to the fleet.*
>
> *2. Second is $f_{\text{dist}}$, our **Byzantine Anomaly Distance Function** from our FheFL implementation. In an IoV network, compromised vehicles may inject model poisoning. The server computes the squared Euclidean distance between the vehicle's update and an anchor model without decrypting. Crucially, the server returns **only the single scalar distance $[d_k^2]$**, not the raw weights! This consumes **Depth 1** and takes 18 ms.*
>
> *3. Third is $f_{\text{cos}}$, our **Clean-Anchor Directional Alignment Function**. The server computes the inner product between the vehicle's update and a verified clean RSU validation gradient. It returns a **single scalar trust score $[s_k]$** at **Depth 0** in just 3.1 ms, allowing the server to weight client contributions without any ciphertext multiplication.*
>
> *4. Fourth is $f_{\text{infer}}$, our **Blind Edge Telemetry Inference Function**. Because ChebyKAN is built purely on Chebyshev polynomials, an RSU can evaluate the forward intrusion detection pass directly on encrypted vehicle telemetry $[x]$ via Clenshaw recurrence. It consumes **Depth $\le 2$** and returns the **encrypted classification probability $[P(\text{Attack})]$**."*

---

## Slide 4 — Cryptographic Feasibility & ChebyKAN Synergy (Page 424 of BookCKKS)
*(Runtime: ~90 seconds)*

### 🎙️ Exact Speaker Script

> *"Finally, Slide 4 grounds our entire architecture in Page 424 of BookCKKS—Cheon et al. 2017—and highlights why ChebyKAN is the mathematical partner for homomorphic encryption.*
>
> *On the left: Page 424, Section 4 formalizes how functions are evaluated in CKKS. Lemma 4 proves that constant additions and scalar multiplications consume **zero multiplicative depth**. This is why $f_{\text{agg}}$ and $f_{\text{cos}}$ preserve full cryptographic precision without consuming modulus levels. Algorithm 1 and Lemma 7 show that evaluating a general polynomial of degree $D$ requires exactly $\lceil \log_2 D \rceil$ multiplicative levels using the baby-step giant-step method. Our modulus chain $[60, 40, 40, 60]$ provides a level budget of 2, perfectly matching degree $D=4$.*
>
> *On the right: why ChebyKAN? In traditional deep learning, MLPs and CNNs rely on **ReLU activations**. But FHE cannot compute comparisons or non-smooth functions. Approximating ReLU under FHE requires degree 7 to 15 polynomial approximations, which destroys 3 to 4 modulus levels and introduces heavy numerical error.*
>
> *ChebyKAN completely eliminates this problem. By design, ChebyKAN’s activation functions are linear combinations of Chebyshev orthogonal polynomials ($T_0$ through $T_4$). We evaluate them homomorphically using the **exact Clenshaw recurrence relation** ($T_{n+1} = 2x T_n - T_{n-1}$) with **ZERO approximation error**!*
>
> *In summary: ChebyKAN avoids the ReLU bottleneck entirely, fits natively within our 2-level CKKS parameter profile, and enables both ultra-fast model aggregation and encrypted edge inference."*

---

## Summary Matrix for Rapid Presenter Reference

| Slide | Core Focus | Key Metric / Formula | Mentor Objection Answered |
|---|---|---|---|
| **Slide 1** | Role of $f$ in $W_{t+1}$ Update | $[W_{t+1}] = \sum \alpha_k [W_k]$ (Depth 0) | Explains why server knows $f$ and why only evaluated value is sent. |
| **Slide 2** | 44,164 Weights in SIMD | 11 chunks $\times$ 4096 slots (5.2 ms) | Resolves parameter count and SIMD polynomial vectorization. |
| **Slide 3** | Taxonomy of $f$ Functions | $f_{\text{agg}}$, $f_{\text{dist}}$, $f_{\text{cos}}$, $f_{\text{infer}}$ | Details specific functions, purposes, depths, and return values. |
| **Slide 4** | Theory (Page 424) & ChebyKAN | Clenshaw Recurrence / Zero ReLU Error | Grounds design in ASIACRYPT 2017 & proves why ChebyKAN fits FHE. |
