import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.5)
ax.axis('off')

DARK_NAVY = '#0F2042'
BLUE_ACCENT = '#1E3A8A'
TEAL_GREEN = '#0D9488'
LIGHT_BG = '#F8FAFC'
BORDER_COLOR = '#CBD5E1'
TEXT_DARK = '#0F172A'
WHITE = '#FFFFFF'

# Outer Card
bg_card = patches.FancyBboxPatch((0.2, 0.2), 9.6, 6.1, boxstyle="round,pad=0.2",
                                facecolor=LIGHT_BG, edgecolor=BORDER_COLOR, linewidth=1.5)
ax.add_patch(bg_card)

# Title
ax.text(5.0, 5.85, "DATASET UNIFICATION & FLEET SHARDING PIPELINE", ha='center', va='center',
        color=DARK_NAVY, fontsize=12, fontweight='bold', fontfamily='sans-serif')

# Step 1: 4 Heterogeneous Datasets (4 small cards at top)
ds_list = [
    ("Car-Hacking", "5 Classes\nRaw CAN"),
    ("CAN-VTC", "4 Classes\nTelemetry"),
    ("CICIDS-2017", "15 Classes\nIP Flows"),
    ("VeReMi", "5 Classes\nV2X BSM")
]
for idx, (name, desc) in enumerate(ds_list):
    dx = 0.6 + idx * 2.25
    b_ds = patches.FancyBboxPatch((dx, 4.3), 2.05, 1.1, boxstyle="round,pad=0.1",
                                 facecolor=WHITE, edgecolor='#94A3B8', linewidth=1)
    ax.add_patch(b_ds)
    ax.text(dx + 1.02, 5.05, name, ha='center', va='center', color=DARK_NAVY, fontsize=9, fontweight='bold')
    ax.text(dx + 1.02, 4.60, desc, ha='center', va='center', color='#475569', fontsize=7.5, multialignment='center')

# Arrows converging to Unified Adapter
for idx in range(4):
    dx = 0.6 + idx * 2.25 + 1.02
    ax.annotate('', xy=(5.0, 3.6), xytext=(dx, 4.2), arrowprops=dict(arrowstyle="->", color=BLUE_ACCENT, lw=1.5))

# Step 2: Unified 46-D Feature Vector (Middle Banner)
b_unified = patches.FancyBboxPatch((1.5, 2.9), 7.0, 0.7, boxstyle="round,pad=0.1",
                                  facecolor='#EEF2FF', edgecolor=BLUE_ACCENT, linewidth=1.5)
ax.add_patch(b_unified)
ax.text(5.0, 3.25, "UNIFIED 46-D STATISTICAL FEATURE VECTOR (Sliding Window W=29)",
        ha='center', va='center', color=BLUE_ACCENT, fontsize=9.5, fontweight='bold')

# Converging arrows to Fleet & Output
ax.annotate('', xy=(2.75, 2.2), xytext=(4.0, 2.85), arrowprops=dict(arrowstyle="->", color=DARK_NAVY, lw=1.5))
ax.annotate('', xy=(7.25, 2.2), xytext=(6.0, 2.85), arrowprops=dict(arrowstyle="->", color=DARK_NAVY, lw=1.5))

# Step 3 Left: Fleet Simulation Mode
b_fleet = patches.FancyBboxPatch((0.6, 0.45), 4.2, 1.65, boxstyle="round,pad=0.1",
                                facecolor=WHITE, edgecolor='#0D9488', linewidth=1.2)
ax.add_patch(b_fleet)
ax.text(2.7, 1.80, "FLEET SIMULATION MODE", ha='center', va='center', color=TEAL_GREEN, fontsize=9.5, fontweight='bold')
ax.text(2.7, 1.40, "• Dirichlet Non-IID Sharding (α = 0.3)", ha='center', va='center', color=TEXT_DARK, fontsize=8)
ax.text(2.7, 1.05, "• Heterogeneous Vehicle Cohort (N = 10 ECUs)", ha='center', va='center', color=TEXT_DARK, fontsize=8)
ax.text(2.7, 0.70, "• Localized Attack Exposures per Node", ha='center', va='center', color='#475569', fontsize=7.5)

# Step 3 Right: 4 Target Output Classes & 44,164 Parameters
b_out = patches.FancyBboxPatch((5.2, 0.45), 4.2, 1.65, boxstyle="round,pad=0.1",
                              facecolor=WHITE, edgecolor=BLUE_ACCENT, linewidth=1.2)
ax.add_patch(b_out)
ax.text(7.3, 1.80, "4 TARGET INTRUSION CLASSES", ha='center', va='center', color=BLUE_ACCENT, fontsize=9.5, fontweight='bold')
ax.text(7.3, 1.42, "0: Normal  |  1: DoS  |  2: Replay  |  3: Spoof", ha='center', va='center', color=TEXT_DARK, fontsize=8, fontweight='bold')
ax.text(7.3, 1.05, "ChebyKAN Trunk: 46 -> 64 -> 64 -> 4", ha='center', va='center', color=DARK_NAVY, fontsize=8)
ax.text(7.3, 0.70, "Total Parameters: EXACTLY 44,164", ha='center', va='center', color='#DC2626', fontsize=8.5, fontweight='bold')

plt.tight_layout()
plt.savefig('diagram_dataset_unification_fleet.png', dpi=300, bbox_inches='tight')
print("Successfully generated diagram_dataset_unification_fleet.png")
