"""Normalise company names and tickers in financials.json.

Groups all KCB variants -> ticker=KCB, company=KCB Group Plc
Groups EQTY/Equity variants similarly.
"""
import json, re
from pathlib import Path

DATA = Path(__file__).parent.parent / "data" / "nse" / "financials.json"

# (pattern, canonical_ticker, canonical_company)
RULES = [
    (re.compile(r'kcb', re.I), "KCB", "KCB Group Plc"),
    (re.compile(r'equity.group', re.I), "EQTY", "Equity Group Holdings Plc"),
    (re.compile(r'equity group', re.I), "EQTY", "Equity Group Holdings Plc"),
    (re.compile(r'equit', re.I), "EQTY", "Equity Group Holdings Plc"),
    (re.compile(r'safaricom', re.I), "SCOM", "Safaricom Plc"),
    (re.compile(r'co.op', re.I), "COOP", "Co-operative Bank of Kenya"),
    (re.compile(r'cooperative', re.I), "COOP", "Co-operative Bank of Kenya"),
    (re.compile(r'absa', re.I), "ABSA", "ABSA Bank Kenya Plc"),
    (re.compile(r'stanbic', re.I), "SBIC", "Stanbic Holdings Plc"),
    (re.compile(r'standard.chartered', re.I), "SCBK", "Standard Chartered Bank Kenya"),
    (re.compile(r'stanchart', re.I), "SCBK", "Standard Chartered Bank Kenya"),
    (re.compile(r'dtb|diamond.trust', re.I), "DTB", "Diamond Trust Bank Kenya"),
    (re.compile(r'i&m|im.group|im holdings', re.I), "IMH", "I&M Group Plc"),
    (re.compile(r'family.bank', re.I), "FMLY", "Family Bank Ltd"),
    (re.compile(r'national.bank', re.I), "NBK", "National Bank of Kenya"),
    (re.compile(r'ncba', re.I), "NCBA", "NCBA Group Plc"),
    (re.compile(r'hf.group|housing.finance', re.I), "HFCK", "HF Group Plc"),
]

def normalise(entry: dict) -> dict:
    company = entry.get("company") or ""
    ticker  = entry.get("ticker") or ""
    search  = (company + " " + ticker).lower()
    # Also check URL
    url = entry.get("url", "").lower()
    combined = search + " " + url

    for pat, tick, name in RULES:
        if pat.search(combined):
            entry["ticker"]  = tick
            entry["company"] = name
            return entry
    return entry

with DATA.open(encoding="utf-8") as f:
    data = json.load(f)

before = {e.get("company") for e in data}
data = [normalise(e) for e in data]
after  = {e.get("company") for e in data}

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Normalised {len(data)} entries")
print(f"Company names before: {sorted(str(c) for c in before)}")
print(f"Company names after:  {sorted(str(c) for c in after)}")
