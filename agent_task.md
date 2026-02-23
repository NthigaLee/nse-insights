You are working on the Kenya stocks financial data extraction pipeline. Here is the current state and what needs fixing.

## Context

The project is in this directory. Key files:
- backend/extract_financials_v2.py — the main extractor (already rewritten with fixes)
- backend/test_extractor_v2.py — test script against known PDFs
- test_results.txt — last test run output (shows what passes/fails)
- AUDIT_FINDINGS.md — detailed audit of bugs and known issues
- data/nse/financials.json — extraction output
- data/nse/index_2023_2025.json — index of PDFs to process
- frontend/data.js — the frontend data file that needs updating

## Current Test Results Summary

The v2 extractor is mostly working. Remaining issues:

### Issue 1 — ABSA total_assets = None
- ABSA_Sep2020 and ABSA_Jun2024 both return total_assets = None
- Investigate why find_line(lines, "total assets") returns None for these PDFs
- Print lines from these PDFs containing "asset" or "total" to see the actual text
- Fix the extractor to catch it

### Issue 2 — SCOM_Mar2020 units wrong + balance sheet missing
- Units detected as KES_thousands but values are clearly KES_billions (revenue=251.22, PAT=73.66)
- Fix unit detection for Safaricom 2020 (the PDF likely says "KES billions" or "KShs billions")
- total_assets and total_equity are None — investigate and fix

### Issue 3 — ABSA_Dec2023 PAT anomaly
- profit_after_tax (30,681,559) > profit_before_tax (19,832,431) — unusual
- Investigate: is there a deferred tax credit in the PDF, or is the extractor picking the wrong line?
- Fix if wrong. Leave a comment if legitimately correct.

### Issue 4 — SCBK H1 2025 not tested
- File: data/nse/2025/Standard_Chartered_Bank_Kenya_Ltd_00_1_51_financials.pdf
- Check if it is in data/nse/index_2023_2025.json — add it if missing
- Run extraction on it and verify results in test_extractor_v2.py

## The Fix Process

1. Investigate each issue by printing relevant lines from problematic PDFs using pdfplumber
2. Fix backend/extract_financials_v2.py and/or backend/test_extractor_v2.py
3. Re-run tests: python backend/test_extractor_v2.py
4. Re-run full extraction: python backend/extract_financials_v2.py
5. Update frontend/data.js with clean figures from financials.json for ABSA, STANCHART, SAFARICOM only

## frontend/data.js Update Rules
- Keep the existing annuals[] structure
- Use Group consolidated figures where available
- Units: ABSA and STANCHART = KES thousands. SAFARICOM = KES millions
  (Normalise Safaricom 2020 from KES billions to KES millions: multiply by 1000)
- Only update ABSA, STANCHART, SAFARICOM — leave KCB, EQUITY, COOP unchanged
- Deduplicate by year: keep most complete full-year data per year

## Important Notes
- Check for a venv directory first. If found, activate with: venv\Scripts\activate.bat
- Run extraction scripts from the project root (not from backend/)
- The PDFs are in data/nse/ subdirectory tree organised by year

When completely finished, run this exact command to notify:
openclaw system event --text "Done: Kenya stocks extractor fixed and data.js updated" --mode now
