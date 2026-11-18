import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set up figure
fig, ax = plt.subplots(figsize=(7.5, 9.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 13)
ax.axis('off')

# Styling constants
DARK_BLUE = '#0F2042'
LIGHT_BLUE = '#F0F5FD'
BORDER_BLUE = '#1E3A8A'
ACCENT_GREEN = '#0D9488'
SERVER_BG = '#F8FAFC'
SERVER_BORDER = '#64748B'
TEXT_COLOR = '#0F172A'
WHITE = '#FFFFFF'

# 1. CLIENT DOMAIN BOX (Top)
box_client = patches.FancyBboxPatch((1.0, 11.0), 8.0, 1.4, boxstyle="round,pad=0.2",
                                    facecolor=DARK_BLUE, edgecolor=BORDER_BLUE, linewidth=1.5)
ax.add_patch(box_client)
ax.text(5.0, 11.9, "CLIENT DOMAIN", ha='center', va='center', color=WHITE, fontsize=13, fontweight='bold', fontfamily='sans-serif')
ax.text(5.0, 11.4, "(Possesses Secret Decryption Key sk)", ha='center', va='center', color='#93C5FD', fontsize=10.5, fontfamily='sans-serif')

# Step [1]
ax.annotate('', xy=(5.0, 10.3), xytext=(5.0, 10.9), arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=2))
ax.text(5.0, 10.5, "[1] Local Plaintext Data (46 CAN Features)", ha='center', va='center', color=TEXT_COLOR, fontsize=10, fontweight='bold')

# Encrypts locally
ax.annotate('', xy=(5.0, 9.6), xytext=(5.0, 10.2), arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=2))
ax.text(5.0, 9.85, "( Encrypts locally via pk )", ha='center', va='center', color=ACCENT_GREEN, fontsize=10, style='italic', fontweight='bold')

# Step [2]
ax.annotate('', xy=(5.0, 8.9), xytext=(5.0, 9.5), arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=2))
ax.text(5.0, 9.15, "[2] Secure Ciphertext (ck, nk)", ha='center', va='center', color=BORDER_BLUE, fontsize=10.5, fontweight='bold')

# Transmit Arrow
ax.annotate('', xy=(5.0, 7.8), xytext=(5.0, 8.8), arrowprops=dict(arrowstyle="->", color='#EF4444', lw=2.5, ls='--'))
ax.text(6.8, 8.35, "(Transmits over network)", ha='left', va='center', color='#DC2626', fontsize=9.5, fontweight='bold')

# 2. UNTRUSTED SERVER DOMAIN (Middle outer container)
box_server_outer = patches.FancyBboxPatch((0.6, 3.2), 8.8, 4.4, boxstyle="round,pad=0.2",
                                          facecolor=SERVER_BG, edgecolor=SERVER_BORDER, linewidth=1.5, linestyle='--')
ax.add_patch(box_server_outer)
ax.text(0.9, 7.3, "UNTRUSTED SERVER DOMAIN", ha='left', va='center', color=SERVER_BORDER, fontsize=10.5, fontweight='bold')
ax.text(0.9, 6.9, "(No Decryption Key: sk = ∅)", ha='left', va='center', color='#DC2626', fontsize=9.5, fontweight='bold')

# Server Step 1: Receives Ciphertext
box_s1 = patches.FancyBboxPatch((2.2, 6.0), 5.6, 0.7, boxstyle="round,pad=0.1", facecolor=WHITE, edgecolor='#CBD5E1', linewidth=1.2)
ax.add_patch(box_s1)
ax.text(5.0, 6.35, "Receives Ciphertext { (ck, nk) }", ha='center', va='center', color=TEXT_COLOR, fontsize=10, fontweight='bold')

# Arrow inside server
ax.annotate('', xy=(5.0, 5.2), xytext=(5.0, 5.9), arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=2))

# Server Step 2: Computes Function f
box_s2 = patches.FancyBboxPatch((2.2, 4.4), 5.6, 0.7, boxstyle="round,pad=0.1", facecolor='#EEF2FF', edgecolor=BORDER_BLUE, linewidth=1.5)
ax.add_patch(box_s2)
ax.text(5.0, 4.85, "Computes Function F(Encrypted Data)", ha='center', va='center', color=DARK_BLUE, fontsize=10, fontweight='bold')
ax.text(5.0, 4.55, "F = (1 / ∑ nk) · ∑ nk ck", ha='center', va='center', color=BORDER_BLUE, fontsize=9.5, fontweight='bold')

# Arrow inside server
ax.annotate('', xy=(5.0, 3.6), xytext=(5.0, 4.3), arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=2))

# Server Step 3: New Result Ciphertext
box_s3 = patches.FancyBboxPatch((2.2, 2.8), 5.6, 0.7, boxstyle="round,pad=0.1", facecolor=WHITE, edgecolor='#CBD5E1', linewidth=1.2)
ax.add_patch(box_s3)
ax.text(5.0, 3.15, "New Result Ciphertext (cF)", ha='center', va='center', color=TEXT_COLOR, fontsize=10, fontweight='bold')

# Send back arrow
ax.annotate('', xy=(5.0, 1.8), xytext=(5.0, 2.7), arrowprops=dict(arrowstyle="->", color='#2563EB', lw=2.5, ls='--'))
ax.text(5.0, 2.3, "[4] Sends Result cF Back (Broadcast)", ha='center', va='center', color=BORDER_BLUE, fontsize=10, fontweight='bold')

# Decrypts locally
ax.annotate('', xy=(5.0, 0.9), xytext=(5.0, 1.6), arrowprops=dict(arrowstyle="->", color=DARK_BLUE, lw=2))
ax.text(5.0, 1.25, "( Decrypts locally using sk )", ha='center', va='center', color=ACCENT_GREEN, fontsize=10, style='italic', fontweight='bold')

# [5] Final Plaintext Result
box_final = patches.FancyBboxPatch((1.5, 0.1), 7.0, 0.7, boxstyle="round,pad=0.1", facecolor=DARK_BLUE, edgecolor=BORDER_BLUE, linewidth=1.2)
ax.add_patch(box_final)
ax.text(5.0, 0.45, "[5] Final Plaintext Result: w^(t+1) = w^(t) + Δw_global", ha='center', va='center', color=WHITE, fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('diagram_client_server_trust.png', dpi=300, bbox_inches='tight')
print("Successfully generated diagram_client_server_trust.png")
