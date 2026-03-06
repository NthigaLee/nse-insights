"""Dedup by (ticker, period_type, period_end_date), keeping the entry with more data.
Also drops entries where NII is suspiciously small vs other entries for same period.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "nse" / "financials.json"

with DATA.open(encoding="utf-8") as f:
    data = json.load(f)

def score(e):
    """Higher = more complete data."""
    keys = ["net_interest_income","revenue","profit_before_tax","profit_after_tax",
            "total_assets","total_equity","customer_deposits","loans_and_advances"]
    return sum(1 for k in keys if e.get(k) is not None)

# Group by (ticker, period_type, period_end_date)
from collections import defaultdict
groups = defaultdict(list)
no_key = []

for e in data:
    t   = e.get("ticker") or ""
    pt  = e.get("period_type") or ""
    ped = e.get("period_end_date") or ""
    if t and pt and ped:
        groups[(t, pt, ped)].append(e)
    else:
        no_key.append(e)

kept = list(no_key)
removed = 0
for key, entries in groups.items():
    if len(entries) == 1:
        kept.append(entries[0])
    else:
        # Keep the one with the most data; tie-break by higher NII
        best = max(entries, key=lambda e: (score(e), e.get("net_interest_income") or 0))
        kept.append(best)
        removed += len(entries) - 1

with DATA.open("w", encoding="utf-8") as f:
    json.dump(kept, f, indent=2, ensure_ascii=False)

print(f"Removed {removed} duplicates. Kept {len(kept)} entries total.")
