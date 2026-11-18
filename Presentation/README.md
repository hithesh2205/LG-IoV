# 🚗 IoV Collaborative Intrusion Detection: ChebyKAN + CKKS
## Master Navigation Guide & Technical Reference

> **📌 Start Here if Returning After a Few Weeks!**  
> This directory contains all presentation decks, system architecture diagrams, technical specifications, and speaker scripts for the **LG Soft India (LGSI) Collaborative Vehicular Intrusion Detection (IoV) Project**.

---

## 🧭 Directory Structure & File Map

```
Presentation/
│
├── 📄 README.md                                  <-- [YOU ARE HERE] Master Project Index & Quick Reference
│
├── 📂 01_Final_Presentations/                    <-- Exact PowerPoint decks ready for meetings
│   ├── F_Functions_In_Template_4_Slides.pptx     ⭐ PRIMARY: Exactly 4 slides on Function f in August 28 template
│   ├── October_5_Progress_Meeting.pptx           ⭐ COMPREHENSIVE: Complete progress deck for mentor review
│   └── Presentation_28th_August_Baseline.pptx    📌 BASELINE: Original 25-slide presentation from August 28
│
├── 📂 02_Diagrams_and_Flowcharts/                <-- High-Resolution 300 DPI Visual Diagrams
│   ├── 01_3Clients_ChebyKAN_CKKS_Flowchart.png   ⭐ MASTER FLOWCHART: 3 Clients, ChebyKAN NN, SIMD, Server & Decryption
│   ├── 02_F_Function_Architecture_Flow.png       ⭐ CLEAN BOX FLOW: Direct adaptation of meeting architecture sketch
│   └── 03_F_Function_System_Architecture.png     ⭐ SYSTEM CARD DIAGRAM: Detailed client/server domains & 4 f functions
│
├── 📂 03_Technical_Guides_and_Specs/             <-- Mathematical Derivations & Code Specifications
│   ├── 01_3Clients_ChebyKAN_CKKS_Specification.md⭐ Complete 3-client step-by-step technical specification
│   ├── 02_Homomorphic_Functions_Analysis.md      ⭐ In-depth analysis of f taxonomy, Kerckhoffs's principle & Page 424
│   └── 02_Homomorphic_Functions_Analysis.docx    📄 Microsoft Word report of the above analysis
│
├── 📂 04_Speaker_Notes_and_Scripts/              <-- Ready-to-use Speaking Scripts & Communications
│   ├── Speech_Sheet_F_Functions_4_Slides.md      ⭐ EXACT 90-sec per slide script & Mentor Q&A defense for the 4 slides
│   ├── Teams_Message_To_Mentor_Fahiem.md         ⭐ Ready-to-copy Microsoft Teams message with ASCII diagram
│   └── Speech_Sheet_Slides_1_to_14.md            📄 Original 14-slide presentation script from August
│
├── 📂 05_Reference_Materials/                    <-- Core Cryptographic Literature
│   ├── BookCKKS.pdf                              📄 Cheon et al. ASIACRYPT 2017 (Section 4 Page 424: Homomorphic Functions)
│   └── intro_to_CKKS.pdf                         📄 Yongsoo Song's CKKS Tutorial (Parameters N=8192, [60,40,40,60])
│
└── 📂 06_Archive/                                <-- Historical Drafts & Backups (Preserved safely)
    ├── 7_sept_presentation.pptx
    ├── F_Functions_In_CKKS_ChebyKAN_draft.pptx
    ├── Presentation_Updated_F_Functions_draft.pptx
    ├── Presentation_28th_August.BACKUP.pptx
    └── Trail.pdf
```

---

## 💡 Quick Catch-Up: The 4 Core Questions from Mentor Review

During our technical review with LGSI mentor **Fahiem Altaf** and **Dr. Praveen K**, four critical architectural questions were raised. Here is the concise summary:

### 1. What is the $f$ Function and Why Does the Server Know It?
- **Kerckhoffs’s Principle:** Security relies on keeping the **data secret**, not the algorithm.
- The untrusted Roadside Unit (RSU) / server has **ZERO decryption keys** ($sk \notin \text{Server}$).
- The server is untrusted with vehicle private telemetry, but it is explicitly assigned the mathematical circuit $f$. It evaluates $f$ blindly on ciphertexts via homomorphic arithmetic.

### 2. How is $f$ Used to Update the Global Model ($W_{t+1}$)?
- The primary model update function is **Homomorphic FedAvg ($f_{\text{agg}}$)**:
  $$[W_{t+1}] = f_{\text{agg}}([W_1^{(t)}], \dots, [W_K^{(t)}]) = \sum_{k=1}^K \alpha_k [W_k^{(t)}]$$
- Computed via plaintext-scalar multiplication and ciphertext addition.
- Consumes **Multiplicative Depth = 0** and executes across all 44,164 parameters in just **5.2 milliseconds** on the server!

### 3. Why Do We Send the Evaluated Value of $f$, NOT Raw Text?
- The server **never transmits raw aggregated text, individual updates, or concatenated ciphertexts**.
- Transmitting raw updates wastes V2X bandwidth and leaks traffic linkability.
- Instead, the server broadcasts **only the single evaluated result ciphertext $[W_{t+1}]$**.
- **Bandwidth Invariant:** Transmission payload is strictly bounded to **11 ciphertext chunks (~1.2 MB compressed)**, completely invariant to whether 3 or 3,000 vehicles participate.

### 4. How Do 44,164 ChebyKAN Weights Fit into CKKS Polynomials?
- **ChebyKAN Model Anatomy:**
  - Base Linear Weights ($w_b$): $7,296$ weights.
  - Chebyshev Polynomial Coefficients ($c_0 \dots c_4$ for degree $D=4$): $5 \times 7,296 = \mathbf{36,480}$ coefficients.
  - LayerNorm & Biases: $388$ parameters.
  - **Total Parameters:** Exactly $\mathbf{44,164}$ weights per vehicle.
- **CKKS Vectorization ($N = 8,192$):**
  - Canonical embedding packs $N/2 = \mathbf{4,096 \text{ numbers}}$ into SIMD slots per ciphertext.
  - Partitioning: $\lceil 44,164 / 4,096 \rceil = \mathbf{11 \text{ Ciphertext Chunks}}$.
  - The server evaluates $f$ chunk-by-chunk in parallel: 11 ciphertext additions update all 44,164 parameters in one pass!

---

## 🔄 The 3-Client End-to-End Workflow Summary

```text
+--------------------------------------------------------------------------------------------------+
| STAGE 1: 3 Clients (Vehicles 1, 2, 3)                                                            |
| • Each vehicle trains local ChebyKAN model (16 inputs -> 32 hidden -> 4 attack classes).         |
| • Edge equation: phi(x) = w_b*x + sum_{d=0}^4 c_d*T_d(x) (6 parameters per edge).                |
| • Produces local weight vector: W_k in R^{44,164}.                                               |
+--------------------------------------------------------------------------------------------------+
                                                │
                                                ▼
+--------------------------------------------------------------------------------------------------+
| STAGE 2: CKKS SIMD Packing & Polynomial Encryption                                               |
| • 44,164 weights partitioned into 11 chunks (4,096 weights/chunk).                               |
| • Scaled by Delta = 2^{40} and encoded into polynomials m^(j)(X) in R_q (deg 8,191).             |
| • Encrypted under public key pk=(b, a): C_k^(j) = (c_0^(j), c_1^(j)) in R_q x R_q.              |
| • Upload payload: 11 chunks (~1.2 MB compressed) per client. Total to server: 33 chunks.        |
+--------------------------------------------------------------------------------------------------+
                                                │
                                                ▼
+--------------------------------------------------------------------------------------------------+
| STAGE 3: Untrusted Server Domain & Function f Execution                                          |
| • Server receives 33 chunks. ZERO secret key shares (sk not in server).                          |
| • Evaluates Homomorphic FedAvg (f_agg) chunk-by-chunk:                                           |
|   c_{global, 0}^(j) = 1/3 * (c_{1,0}^(j) + c_{2,0}^(j) + c_{3,0}^(j)) (mod q)                   |
|   c_{global, 1}^(j) = 1/3 * (c_{1,1}^(j) + c_{2,1}^(j) + c_{3,1}^(j)) (mod q)                   |
| • Multiplicative Depth = 0 | Execution Latency = ~5.2 ms.                                        |
+--------------------------------------------------------------------------------------------------+
                                                │
                                                ▼
+--------------------------------------------------------------------------------------------------+
| STAGE 4: Downlink Broadcast of Evaluated Value [W_{t+1}]                                         |
| • Server broadcasts ONLY the evaluated global ciphertext: C_global = [C_agg^(1) ... C_agg^(11)].|
| • Exactly 11 chunks (~1.2 MB). ZERO raw text, ZERO individual weights transmitted.               |
+--------------------------------------------------------------------------------------------------+
                                                │
                                                ▼
+--------------------------------------------------------------------------------------------------+
| STAGE 5: Client Reception & Decryption                                                           |
| • Vehicles decrypt using secret key sk: m_global^(j) = c_0,agg^(j) + c_1,agg^(j)*sk (mod q).     |
| • Decode slots: divide by Delta = 2^{40}.                                                        |
| • Recover exact plaintext global model: W_{t+1} = 1/3 * (W_1 + W_2 + W_3) in R^{44,164}.         |
| • Error noise is < 10^{-8} -> Mathematically identical to plaintext FedAvg accuracy!             |
+--------------------------------------------------------------------------------------------------+
```

---

## 🛠️ Which File Should I Open?

| What do you need to do? | Open this file |
|---|---|
| **Presenting the 4 Slides on F function** | [`01_Final_Presentations/F_Functions_In_Template_4_Slides.pptx`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/01_Final_Presentations/F_Functions_In_Template_4_Slides.pptx) |
| **Speaking script for the 4 slides** | [`04_Speaker_Notes_and_Scripts/Speech_Sheet_F_Functions_4_Slides.md`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/04_Speaker_Notes_and_Scripts/Speech_Sheet_F_Functions_4_Slides.md) |
| **Sending an update/diagram on MS Teams** | [`04_Speaker_Notes_and_Scripts/Teams_Message_To_Mentor_Fahiem.md`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/04_Speaker_Notes_and_Scripts/Teams_Message_To_Mentor_Fahiem.md) |
| **Showing the master 3-client visual flowchart** | [`02_Diagrams_and_Flowcharts/01_3Clients_ChebyKAN_CKKS_Flowchart.png`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/02_Diagrams_and_Flowcharts/01_3Clients_ChebyKAN_CKKS_Flowchart.png) |
| **Reading full technical specs & equations** | [`03_Technical_Guides_and_Specs/01_3Clients_ChebyKAN_CKKS_Specification.md`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/03_Technical_Guides_and_Specs/01_3Clients_ChebyKAN_CKKS_Specification.md) |
| **Checking the seminal paper (Page 424)** | [`05_Reference_Materials/BookCKKS.pdf`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/05_Reference_Materials/BookCKKS.pdf) |
