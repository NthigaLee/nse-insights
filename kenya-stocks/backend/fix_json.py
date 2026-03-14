import json

# Read the corrupted JSON file
with open('../data/nse/financials.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the position of the truncation
if content.endswith('"operating_cash_flow"'):
    # Add the missing fields and close the JSON properly
    fixed_content = content + ': null,\n  "capex": null,\n  "mpesa_revenue": null,\n  "subscribers": null\n}\n]'
    
    # Write the fixed content back to the file
    with open('../data/nse/financials_fixed.json', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("JSON file fixed successfully!")
else:
    print("File doesn't appear to be truncated at the expected position.")