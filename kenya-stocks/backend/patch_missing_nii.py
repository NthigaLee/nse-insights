"""Re-extract NII for entries where it's null using the older extractor logic."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from extract_financials_from_pdfs import pdf_lines, extract_bank_metrics

DATA = Path(__file__).parent.parent / "data" / "nse" / "financials.json"
PDF_DIRS = [
    Path(__file__).parent.parent / "data" / "nse" / str(yr)
    for yr in range(2020, 2027)
]

with DATA.open(encoding="utf-8") as f:
    data = json.load(f)

patched = 0
for entry in data:
    if entry.get("net_interest_income") is not None:
        continue
    if 'KCB' not in (entry.get('company') or '') and 'Equity' not in (entry.get('company') or ''):
        continue

    source = entry.get("source_file", "")
    if not source:
        continue

    # Find the PDF
    pdf_path = None
    for d in PDF_DIRS:
        candidate = d / source
        if candidate.exists():
            pdf_path = candidate
            break

    if not pdf_path:
        print(f"  NOT FOUND: {source}")
        continue

    try:
        lines = pdf_lines(pdf_path)
        metrics = extract_bank_metrics(lines)
        nii = metrics.get("net_interest_income")
        if nii is not None:
            entry["net_interest_income"] = nii
            # Also patch other missing fields
            for k, v in metrics.items():
                if entry.get(k) is None and v is not None:
                    entry[k] = v
            print(f"  Patched {source}: NII={nii:,.0f}")
            patched += 1
        else:
            print(f"  Still null: {source}")
    except Exception as e:
        print(f"  Error {source}: {e}")

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\nPatched {patched} entries.")
