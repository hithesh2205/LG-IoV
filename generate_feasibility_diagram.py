import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Set up figure
fig, ax = plt.subplots(figsize=(8.0, 5.0), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.5)
ax.axis('off')

# Styling constants
DARK_NAVY = '#0F2042'
BLUE_ACCENT = '#1E3A8A'
GREEN_PASS = '#0D9488'
LIGHT_BG = '#F8FAFC'
BORDER_COLOR = '#CBD5E1'
TEXT_DARK = '#0F172A'
WHITE = '#FFFFFF'

# Outer Card
bg_card = patches.FancyBboxPatch((0.2, 0.2), 9.6, 6.1, boxstyle="round,pad=0.2",
                                facecolor=LIGHT_BG, edgecolor=BORDER_COLOR, linewidth=1.5)
ax.add_patch(bg_card)

# Title Banner
ax.text(5.0, 5.85, "AUTOMOTIVE EDGE COMPUTING FEASIBILITY BENCHMARK", ha='center', va='center',
        color=DARK_NAVY, fontsize=12, fontweight='bold', fontfamily='sans-serif')

# Section 1: Real-Time CAN Latency Budget (Horizontal Bar comparison)
ax.text(0.6, 5.2, "1. Real-Time CAN Frame Latency Budget", ha='left', va='center',
        color=BLUE_ACCENT, fontsize=10.5, fontweight='bold')

# Bar 1: Safety Limit (10.0 ms)
bar_limit = patches.Rectangle((0.6, 4.4), 8.5, 0.45, facecolor='#E2E8F0', edgecolor='#94A3B8', linewidth=1)
ax.add_patch(bar_limit)
ax.text(0.8, 4.62, "Maximum Safety Deadline on CAN 2.0B Bus (10.0 ms)", va='center', fontsize=9, color='#475569', fontweight='bold')
ax.text(8.9, 4.62, "10.0 ms", ha='right', va='center', fontsize=9, color='#475569', fontweight='bold')

# Bar 2: ChebyKAN Inference (< 1.5 ms)
bar_cheby = patches.Rectangle((0.6, 3.8), 1.28, 0.45, facecolor=GREEN_PASS, edgecolor='#0F766E', linewidth=1)
ax.add_patch(bar_cheby)
ax.text(0.8, 4.02, "ChebyKAN Inference (< 1.5 ms) — PASS (85% Safety Margin)", va='center', fontsize=9, color=WHITE, fontweight='bold')
ax.text(1.85, 4.02, "< 1.5 ms", ha='left', va='center', fontsize=9, color=GREEN_PASS, fontweight='bold')

# Section 2: Three KPI Metric Cards (Side by side)
cards_data = [
    ("5G UPLINK TIME", "< 0.4s", "3.52 MB (11 Chunks)\nover 50-150 Mbps NR", GREEN_PASS),
    ("ECU RAM FOOTPRINT", "< 20 MB", "TenSEAL context on\n1-4 GB Automotive Gateway", BLUE_ACCENT),
    ("ACCURACY GAP", "0.0000%", "Plaintext: 99.83%\nCKKS FHE: 99.83%", DARK_NAVY)
]

for idx, (head, val, sub, col) in enumerate(cards_data):
    cx = 0.6 + idx * 3.0
    kpi_box = patches.FancyBboxPatch((cx, 1.4), 2.7, 2.0, boxstyle="round,pad=0.15",
                                     facecolor=WHITE, edgecolor=BORDER_COLOR, linewidth=1.2)
    ax.add_patch(kpi_box)
    ax.text(cx + 1.35, 3.05, head, ha='center', va='center', color='#64748B', fontsize=8.5, fontweight='bold')
    ax.text(cx + 1.35, 2.45, val, ha='center', va='center', color=col, fontsize=16, fontweight='bold')
    ax.text(cx + 1.35, 1.75, sub, ha='center', va='center', color=TEXT_DARK, fontsize=8, multialignment='center')

# Section 3: Bottom Precision Assertion
assert_box = patches.FancyBboxPatch((0.6, 0.45), 8.7, 0.7, boxstyle="round,pad=0.1",
                                    facecolor='#EEF2FF', edgecolor='#C7D2FE', linewidth=1)
ax.add_patch(assert_box)
ax.text(5.0, 0.8, "Bitwise Hardware Assertion:  ε_agg = || Dec(cF) − Δw_unencrypted ||_∞ = 8.174 × 10⁻⁷  (Passed)",
        ha='center', va='center', color=BLUE_ACCENT, fontsize=9.5, fontweight='bold')

plt.tight_layout()
plt.savefig('diagram_edge_feasibility.png', dpi=300, bbox_inches='tight')
print("Successfully generated diagram_edge_feasibility.png")
