import json

with open('data/nse/financials.json') as f:
    data = json.load(f)

has_data = [d for d in data if d.get('revenue') or d.get('profit_after_tax') or d.get('net_interest_income')]
print(f'Total entries: {len(data)}')
print(f'Entries with data: {len(has_data)}')
for d in has_data[:20]:
    print(f"  {d.get('company','?')} | {d.get('year')} | {d.get('period','')} | rev={d.get('revenue')} | pat={d.get('profit_after_tax')} | nii={d.get('net_interest_income')} | eps={d.get('basic_eps')}")
