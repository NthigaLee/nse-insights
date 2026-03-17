"""Infer period_type and period_end_date for entries where they're missing.

Uses period string and filename to determine:
  - Q1/Q3       -> quarter
  - H1/H2/HY    -> half_year
  - FY/Annual   -> annual
"""
import json, re
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "nse" / "financials.json"

QUARTER_RE  = re.compile(r'\bQ[1-4]\b', re.I)
HALF_RE     = re.compile(r'\bH[12]\b|\bHY\b|\bH1\b|\bH2\b|half.year|interim', re.I)
ANNUAL_RE   = re.compile(r'\bFY\b|\bannual\b|year.ended|december|31.dec|full.year|audited', re.I)

PERIOD_DATE_MAP = {
    # period label -> period_end_date
    "Q3 2025": "2025-09-30", "H1 2025": "2025-06-30", "Q1 2025": "2025-03-31",
    "FY 2024": "2024-12-31", "Q3 2024": "2024-09-30", "H1 2024": "2024-06-30", "Q1 2024": "2024-03-31",
    "H1 2023": "2023-06-30", "Q1 2023": "2023-03-31",
}

FILENAME_META = [
    ("q3-2025",   "quarter",   "2025-09-30"),
    ("h1-2025",   "half_year", "2025-06-30"),
    ("q1-2025",   "quarter",   "2025-03-31"),
    ("fy-2024",   "annual",    "2024-12-31"),
    ("abridged-financial-results-for-the-year-ended-31-december-2024", "annual", "2024-12-31"),
    ("q3-2024",   "quarter",   "2024-09-30"),
    ("h1-2024",   "half_year", "2024-06-30"),
    ("q1-2024",   "quarter",   "2024-03-31"),
    ("h1-financials-2023", "half_year", "2023-06-30"),
    ("q1-2023",   "quarter",   "2023-03-31"),
]

with DATA.open(encoding="utf-8") as f:
    data = json.load(f)

fixed = 0
for entry in data:
    if entry.get("period_type"):
        continue  # already set

    period_str  = str(entry.get("period") or "").strip()
    source_file = (entry.get("source_file") or "").lower()

    period_type    = None
    period_end     = entry.get("period_end_date")

    # Try filename-based lookup first (most reliable)
    for substr, ptype, pend in FILENAME_META:
        if substr in source_file:
            period_type = ptype
            if not period_end:
                period_end = pend
            break

    # Try period-string lookup
    if not period_type:
        if period_str in PERIOD_DATE_MAP:
            if not period_end:
                period_end = PERIOD_DATE_MAP[period_str]

        if QUARTER_RE.search(period_str) or QUARTER_RE.search(source_file):
            period_type = "quarter"
        elif HALF_RE.search(period_str) or HALF_RE.search(source_file):
            period_type = "half_year"
        elif ANNUAL_RE.search(period_str) or ANNUAL_RE.search(source_file):
            period_type = "annual"

    if period_type:
        entry["period_type"] = period_type
        if period_end:
            entry["period_end_date"] = period_end
        # Also set year from period_end_date if missing
        if not entry.get("year") and period_end:
            entry["year"] = int(period_end[:4])
        fixed += 1

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Fixed period_type for {fixed} entries.")
