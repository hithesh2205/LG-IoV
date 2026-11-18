# Microsoft Teams Message Draft for Fahiem Sir

**Subject / Context:** Verification of Homomorphic Function $f$ Architecture & Role in Federated IoV  
**Attachment to Include:** [`Presentation/F_Function_Architecture_Diagram.png`](file:///C:/Users/Thrish_Sudha/Desktop/Amrita%20Files/LGSI%20IOV/Presentation/F_Function_Architecture_Diagram.png)

---

### Option 1: Complete & Structured (Recommended)

Good afternoon Fahiem Sir,

Hope you are doing well. 

Following up on our last discussion regarding the **homomorphic function $f$**, we have refined our architecture and prepared 4 dedicated slides for tomorrow's review. 

To ensure we are completely aligned with your guidance, we wanted to quickly verify the attached architecture diagram with you:

**Core Architecture Highlights:**
1. **Separation of Domains (Kerckhoffs's Principle):** The untrusted RSU/Cloud server has zero access to secret decryption keys ($sk \notin \text{Server}$). It is explicitly assigned the computational task $f$, which it evaluates homomorphically directly over the vehicle ciphertexts $[W_1], \dots, [W_K]$.
2. **Evaluated Value Transmission:** As you pointed out, the server **never transmits raw texts or individual updates**. It evaluates $f$ and broadcasts **only the evaluated value** (e.g., the new global model ciphertext $[W_{t+1}]$ or an anomaly scalar $[d_k^2]$). This strictly limits network payload to 11 SIMD chunks (~1.2 MB compressed) regardless of fleet size.
3. **Taxonomy of $f$ Functions Prepared:**
   - **$f_{\text{agg}}$ (Model Update / FedAvg):** $[W_{t+1}] = \sum \alpha_k [W_k]$ $\to$ returns the updated global model ciphertext (Depth 0, ~5 ms).
   - **$f_{\text{dist}}$ (Anomaly Distance):** $[d_k^2] = \|[W_k] - W_{\text{anc}}\|^2$ $\to$ returns a single distance scalar to detect poisoning without decrypting weights (Depth 1, ~18 ms).
   - **$f_{\text{cos}}$ (Directional Alignment):** $\langle [W_k], V_{\text{clean}} \rangle / \|V\|^2$ $\to$ returns an alignment trust score (Depth 0, ~3 ms).
   - **$f_{\text{infer}}$ (Blind Telemetry IDS):** ChebyKAN polynomial forward pass over encrypted CAN packets $\to$ returns $[P(\text{Attack})]$ (Depth $\le 2$).

Could you please confirm if this architecture and interpretation of the $f$ function matches what you are expecting from us? If there are any specific nuances or variations you'd like us to emphasize in tomorrow's presentation, we would love your input.

Thank you!

---

### Option 2: Short & Direct Version

Good afternoon Fahiem Sir,

Hope you are having a good day.

Based on your feedback in the previous meeting, we have formalized the role of the **$f$ function** and how it updates the global model ($W_{t+1}$) without transmitting raw texts or exposing vehicle updates to the server. 

Attached is our updated architecture diagram illustrating:
- The strict boundary between the Client Domain (possessing $sk$) and the Untrusted Server Domain (possessing only the public task $f$).
- Why the server broadcasts only the **evaluated value of $f$** ($[W_{t+1}]$ or scalar distance $[d_k^2]$) rather than raw ciphertexts.
- How our 44,164 ChebyKAN weights map into 11 SIMD chunks and evaluate at Depth 0 in ~5 ms.

Could you please confirm if this diagram and structure align with what you are expecting from us for tomorrow's review? 

Thank you!
