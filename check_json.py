import json
with open(r'C:\Users\nthig\.openclaw\workspace\kenya-stocks\data\nse\financials.json') as f:
    data = json.load(f)
from collections import Counter
companies = Counter(d['company_key'] for d in data)
print(f'Total records: {len(data)}')
for company, count in sorted(companies.items()):
    print(f'  {company}: {count} records')
print()
print('Records with PAT data:')
for d in data:
    if d.get('profit_after_tax'):
        print(f"  {d['company_key']} {d['period_str']}: PAT={d['profit_after_tax']}, EPS={d['basic_eps']}")
