import re, json

# Read raw file and truncate to last valid JSON record
with open('data/nse/financials.json', 'r', encoding='utf-8') as f:
    raw = f.read()

# Try to find the last complete object by finding last '}' before the broken end
# The file is an array of objects - find the last complete '}'
# We'll try progressively truncating

text = raw.strip()
# Try to parse, if fails, find last closing brace
for attempt in range(5):
    try:
        data = json.loads(text)
        print(f"Parsed OK: {len(data)} records")
        break
    except json.JSONDecodeError as e:
        pos = e.pos
        # Find last complete record by finding '}, {' pattern going backwards
        last_close = text.rfind('},', 0, pos)
        if last_close < 0:
            print("Cannot fix")
            break
        text = text[:last_close+1] + ']'

has_data = [d for d in data if any([d.get('revenue'), d.get('profit_after_tax'), d.get('net_interest_income')])]
print(f"Entries with actual data: {len(has_data)}")

# Group by company/title keyword
companies = {}
for d in has_data:
    title = (d.get('title') or '').lower()
    comp = 'other'
    if 'absa' in title or 'barclays' in title:
        comp = 'ABSA'
    elif 'stanchart' in title or 'standard chartered' in title:
        comp = 'STANCHART'
    elif 'safaricom' in title:
        comp = 'SAFARICOM'
    elif 'equity' in title:
        comp = 'EQUITY'
    elif 'kcb' in title:
        comp = 'KCB'
    elif 'cooperative' in title or 'co-operative' in title:
        comp = 'COOP'
    companies.setdefault(comp, []).append(d)

for comp, records in sorted(companies.items()):
    print(f"\n=== {comp} ({len(records)} records) ===")
    for r in sorted(records, key=lambda x: x.get('year', 0)):
        print(f"  {r.get('year')} | rev={r.get('revenue')} | pat={r.get('profit_after_tax')} | nii={r.get('net_interest_income')} | eps={r.get('basic_eps')} | dps={r.get('dividend_per_share')}")
