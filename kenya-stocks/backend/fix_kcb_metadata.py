"""Fix year/period metadata for KCB entries extracted from directly-downloaded PDFs.

The extractor sets year/period from the NSE index. Files downloaded via KNOWN_PDFS
bypass the index, so we infer year+period from the URL/filename.
"""
import json, re
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "nse" / "financials.json"

# Map filename substrings -> (year, period, period_end_date)
FILENAME_MAP = [
    ("q3-2025", 2025, "Q3 2025", "2025-09-30"),
    ("h1-2025", 2025, "H1 2025", "2025-06-30"),
    ("q1-2025", 2025, "Q1 2025", "2025-03-31"),
    ("fy-2024-audited", 2024, "FY 2024", "2024-12-31"),
    ("abridged-financial-results-for-the-year-ended-31-december-2024", 2024, "FY 2024", "2024-12-31"),
    ("q3-2024", 2024, "Q3 2024", "2024-09-30"),
    ("h1-2024", 2024, "H1 2024", "2024-06-30"),
    ("q1-2024", 2024, "Q1 2024", "2024-03-31"),
    ("h1-financials-2023", 2023, "H1 2023", "2023-06-30"),
    ("q1-2023", 2023, "Q1 2023", "2023-03-31"),
]

# Filenames that are NOT financial statements (governance docs etc.)
SKIP_FILENAMES = [
    "board-directors-attraction",
    "corporate-disclosure-policy",
    "dispute-resolution-policy",
    "ned-remuneration-policy",
    "stakeholder-communication-policy",
    "kcb-board-charter",
]

with DATA.open(encoding="utf-8") as f:
    data = json.load(f)

updated = 0
removed = 0
keep = []

for entry in data:
    url = (entry.get("url") or "").lower()
    source_file = (entry.get("source_file") or "").lower()
    # Prefer source_file (set by extract_all); fall back to url
    if source_file:
        filename = source_file
    elif "?document=" in url:
        filename = url.split("?document=")[-1]
    else:
        filename = url.split("/")[-1]

    # Remove non-financial governance docs
    if any(skip in filename for skip in SKIP_FILENAMES):
        removed += 1
        continue

    # Fix year/period for entries where it's missing
    if entry.get("year") is None or entry.get("period") is None:
        for substr, year, period, period_end in FILENAME_MAP:
            if substr in filename:
                entry["year"]            = year
                entry["period"]          = period
                entry["period_end_date"] = period_end
                updated += 1
                break

    keep.append(entry)

with DATA.open("w", encoding="utf-8") as f:
    json.dump(keep, f, indent=2, ensure_ascii=False)

print(f"Kept {len(keep)} entries  |  Updated metadata: {updated}  |  Removed non-financials: {removed}")
