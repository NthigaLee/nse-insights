# Overnight Task Brief

You are working on a Kenya NSE stocks financial data project. The repo is at:
`C:\Users\nthig\.openclaw\workspace\kenya-stocks`

## Goal
By morning, produce a working website (GitHub Pages) showing financial data + live stock prices
for at least the 10 most relevant NSE companies, with all companies we have PDFs for also included.

---

## Priority Companies (top 10 by NSE relevance/market cap)
1. Safaricom PLC (SCOM)
2. Equity Group Holdings (EQTY)
3. KCB Group (KCB)
4. NCBA Group (NCBA)
5. Co-operative Bank of Kenya (COOP)
6. East African Breweries / EABL (EABL)
7. ABSA Bank Kenya (ABSA)
8. Standard Chartered Bank Kenya (SCBK)
9. Stanbic Holdings (CFC)
10. Diamond Trust Bank (DTK)

---

## Task 1: Fix the Python Extractor

File: `backend/extract_financials_v2.py`

Known bugs to fix:
1. **Note reference numbers captured instead of values** — extractor grabs "Note X" refs instead of actual KES figures
2. **Multi-column numbers concatenated** — e.g. "568,015 490,128" gets read as one giant number instead of two separate years
3. **PAT sign error** — Profit After Tax picks up equity movement instead of the P&L line
4. **Uppercase filenames missed** — Safaricom PDFs have uppercase names (SAFARICOM_PLC_...) but the script looks for lowercase

After fixing, test it on a few PDFs to confirm output looks correct.

---

## Task 2: Re-run Extraction for ALL Companies

Run the fixed extractor against all PDFs in `data/nse/` (all year folders).

Companies with PDFs include:
- ABSA_Bank_Kenya_Plc
- Bamburi_Cement_Plc
- BAT_Kenya_Plc
- BK_Group_Plc
- Britam_Holdings_Plc
- Co_operative_Bank_of_Kenya_Ltd
- Diamond_Trust_Bank_Kenya_Limited
- East_African_Breweries_PLC
- Equity_Group_Holdings_Plc
- Family_Bank_Ltd
- HF_Group_Plc
- Jubilee_Holdings_Limited
- KCB_Group_Plc
- Kenya_Power_Lighting_Plc
- Nation_Media_Group_Plc
- NCBA_Group_Plc
- Safaricom PLC (uppercase: SAFARICOM_PLC_...)
- Sanlam_Kenya_Plc
- Sasini_Plc
- Standard_Chartered_Bank_Kenya_Ltd
- Stanbic_Holdings_Plc
- Unga_Group_Plc
- Williamson_Tea_Kenya
- Wpp_Scangroup_Plc
- (and any others found in data/nse/)

Save all extracted data to `data/nse/financials.json` (overwrite with full dataset).
Also produce `data/nse/financials.xlsx`.

Key fields per entry:
- company (string)
- ticker (NSE ticker symbol, e.g. "SCOM", "EQTY", "KCB")
- period (string, e.g. "FY2024", "H1 FY2024", "Q1 FY2024")
- period_end_date (ISO date string)
- period_type ("annual" | "half_year" | "quarter")
- revenue (KES thousands, integer)
- operating_profit (KES thousands, integer)
- profit_before_tax (KES thousands, integer)
- profit_after_tax (KES thousands, integer)
- total_assets (KES thousands, integer)
- total_equity (KES thousands, integer)
- eps (KES, float) — earnings per share if available
- source_file (PDF filename)

**Currency normalisation:** Safaricom reports in KES millions — multiply by 1000 to convert to thousands.

---

## Task 3: Fill Data Gaps via Web Search

For the top 10 priority companies, use web search (brave_search or requests + BeautifulSoup) to fill in any missing periods. Key sources:
- NSE website: https://www.nse.co.ke/listed-companies/
- Mystocks Kenya: https://mystocks.co.ke/
- Company IR pages (e.g. investor.safaricom.co.ke)
- Reuters / Yahoo Finance

Missing data to look for (examples):
- StanChart: FY2024 full year, H1 FY2025
- Safaricom: FY2023, FY2022 (check for available PDFs)
- Any company where we have < 3 years of data

Write filled-in entries to `data/nse/financials_supplemental.json` (separate from PDF-extracted data, so sources stay clear).

---

## Task 4: Add Live Stock Prices to the UI

### Backend: create `backend/fetch_prices.py`
- Use yfinance to fetch current/latest prices for all companies
- NSE tickers on yfinance use `.NR` suffix: e.g. `SCOM.NR`, `EQTY.NR`, `KCB.NR`, `ABSA.NR`, `SCBK.NR`, `COOP.NR`, `EABL.NR`, `DTK.NR`, `CFC.NR`, `NCBA.NR`
- If yfinance fails for a ticker, try scraping https://mystocks.co.ke/ as fallback
- Output: `data/nse/prices.json` in format:
```json
{
  "SCOM": { "price": 18.50, "change": 0.25, "change_pct": 1.37, "date": "2026-02-22" },
  ...
}
```
- Run this script as part of the build process

### Frontend: update `frontend/data.js` and `frontend/app.js`
- Load `prices.json` (or embed the data in data.js)
- For each company card, show:
  - Current share price (KES)
  - Price change (+ or - with colour: green/red)
  - % change
- Add a "Last updated" timestamp

---

## Task 5: Update Frontend for All Companies

File: `frontend/app.js`, `frontend/data.js`, `frontend/index.html`, `frontend/styles.css`

- Currently only shows 3 companies (ABSA, StanChart, Safaricom)
- Expand to show ALL companies we now have data for
- Add a search/filter bar at the top so users can filter by company name
- Add a sector filter (Banking, Telecoms, FMCG, etc.) — assign sectors to each company
- Keep the existing Qualtrim-style dark theme and Chart.js charts
- Each company card should show:
  - Company name + NSE ticker
  - Current share price + change
  - Key financials: Revenue, PAT, EPS (most recent period)
  - Sparkline or bar chart showing PAT trend over available periods
  - Data source indicator (PDF extracted vs supplemental)

---

## Task 6: Push Everything to GitHub

When all tasks are complete:
1. `git add -A`
2. `git commit -m "feat: expanded to all NSE companies, fixed extractor, live prices"`
3. `git push origin master`

The site is hosted at https://nthigalee.github.io/kenya-stocks/ via GitHub Pages (serves from /docs).
Remember to also copy updated frontend files to `docs/` before committing:
```
Copy-Item frontend\* docs\ -Force
```

---

## When Done

Run this command to notify:
```
openclaw system event --text "Done: Kenya stocks site expanded to all NSE companies with live prices" --mode now
```

---

## Notes
- Python env is in `backend/venv/` — activate with `backend\venv\Scripts\activate`
- The extractor uses pdfplumber — already installed
- yfinance may need installing: `pip install yfinance`
- Keep console output clean — redirect verbose logs to `extract_log.txt`
- Don't touch `SOUL.md`, `USER.md`, `MEMORY.md` or anything in the parent workspace
