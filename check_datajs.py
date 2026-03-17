import json, re

with open(r'C:\Users\nthig\.openclaw\workspace\kenya-stocks\frontend\data.js', encoding='utf-8') as f:
    content = f.read()

# Extract companies from the annuals blocks
companies_found = re.findall(r'\n  (\w+): \{', content)
print(f"Companies in data.js: {', '.join(companies_found)}\n")

# For key companies, show a few annual rows
for co in ['ABSA', 'SCOM', 'KCB', 'COOP', 'NCBA', 'SCBK']:
    # Find annuals block
    m = re.search(rf'\n  {co}: \{{(.*?)^\s+\}},?\n', content, re.DOTALL | re.MULTILINE)
    if not m:
        print(f"{co}: NOT FOUND")
        continue
    block = m.group(1)
    rows = re.findall(r'\{"year".*?\}', block)
    print(f"=== {co} ({len(rows)} annual rows) ===")
    for r in rows[:6]:
        try:
            d = json.loads(r)
            pat = d.get('pat')
            rev = d.get('revenue')
            eps = d.get('eps')
            print(f"  {d['period']:12} PAT={pat} Rev={rev} EPS={eps}")
        except:
            print(f"  RAW: {r[:100]}")
    print()
