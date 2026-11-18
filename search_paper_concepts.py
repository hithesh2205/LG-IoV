import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('Team/LG_IoV/fed_iov_p1-8.txt', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

keywords = ['interval', 'record', 'sample', 'batch', 'window', 'stride', 'D_i', 'time', 'round', 'Dirichlet', 'partition', 'aggregation']

print("=== SEARCHING PAPER TEXT ===")
for kw in keywords:
    matches = [m.start() for m in re.finditer(re.escape(kw), text, re.IGNORECASE)]
    print(f"\nKeyword '{kw}' (count: {len(matches)}):")
    for idx in matches[:4]:
        snippet = text[max(0, idx-100):min(len(text), idx+120)].replace('\n', ' ')
        print(f"  ...{snippet}...")
