import json

with open(r'C:\Users\nthig\.openclaw\workspace\kenya-stocks\data\nse\financials.json') as f:
    data = json.load(f)

print(f"Total records: {len(data)}\n")

for d in data:
    ticker = d.get('ticker', '?')
    period = d.get('period', '?')
    ptype = d.get('period_type', '?')
    units = d.get('units_source', '?')
    pat = d.get('profit_after_tax')
    rev = d.get('revenue')
    eps = d.get('basic_eps')
    nii = d.get('net_interest_income')
    
    pat_b = f"{pat/1e6:.1f}B" if pat else "None"
    rev_b = f"{rev/1e6:.1f}B" if rev else "None"
    nii_b = f"{nii/1e6:.1f}B" if nii else "None"
    
    print(f"{str(ticker):6} | {str(period):12} | {str(ptype):10} | units={str(units):14} | PAT={pat_b:10} | Rev={rev_b:10} | NII={nii_b:10} | EPS={eps}")
