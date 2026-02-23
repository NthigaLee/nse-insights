"""
extract_all.py — Comprehensive NSE PDF extractor.

Improvements over extract_financials_v2.py:
  1. Parses period + period_end_date from PDF filename (not relying on index)
  2. Adds NSE ticker mapping for all known companies
  3. Adds period_type: annual / half_year / quarter
  4. Handles Safaricom uppercase filenames
  5. Scans ALL PDFs in data/nse/ year folders (2015–2025)
  6. Safaricom unit normalisation: millions → thousands (×1000)
  7. Outputs clean JSON with all fields the frontend needs

Usage (from backend/ with venv active):
    python extract_all.py

Outputs:
  data/nse/financials.json   — extracted from PDFs
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

BACKEND_DIR = Path(__file__).parent
DATA_ROOT   = BACKEND_DIR.parent / "data" / "nse"
OUTPUT_FILE = DATA_ROOT / "financials.json"

# ── ticker mapping ─────────────────────────────────────────────────────────────
TICKER_MAP: Dict[str, str] = {
    "absa":                   "ABSA",
    "standard chartered":     "SCBK",
    "stanchart":              "SCBK",
    "safaricom":              "SCOM",
    "equity group":           "EQTY",
    "equity bank":            "EQTY",
    "kcb":                    "KCB",
    "national bank":          "NBK",
    "ncba":                   "NCBA",
    "co-operative bank":      "COOP",
    "cooperative bank":       "COOP",
    "co operative bank":      "COOP",
    "co_operative":           "COOP",
    "diamond trust":          "DTK",
    "dtb":                    "DTK",
    "stanbic":                "CFC",
    "i&m":                    "IMH",
    "i and m":                "IMH",
    "im bank":                "IMH",
    "i_m_group":              "IMH",
    "i_m_holdings":           "IMH",
    "family bank":            "FANB",
    "hf group":               "HFCK",
    "housing finance":        "HFCK",
    "east african breweries": "EABL",
    "eabl":                   "EABL",
    "bamburi":                "BAMB",
    "bat kenya":              "BATK",
    "britam":                 "BRIT",
    "jubilee":                "JUB",
    "sanlam kenya":           "SLAM",
    "kenya power":            "KPLC",
    "kengen":                 "KEGN",
    "nation media":           "NMG",
    "standard group":         "SGL",
    "wpp scangroup":          "SCAN",
    "bk group":               "BKG",
    "crown paints":           "CPKL",
    "unga group":             "UNGA",
    "sasini":                 "SASN",
    "williamson tea":         "WTK",
    "kapchorua tea":          "KAPA",
    "carbacid":               "CARB",
    "boc kenya":              "BOC",
    "east african portland":  "EAPC",
    "umeme":                  "UMME",
    "express kenya":          "XPRS",
    "flame tree":             "FTGH",
    "home afrika":            "HAFR",
    "homeboyz":               "HBZE",
    "transcentury":           "TCL",
    "tps eastern africa":     "TPSE",
    "nse":                    "NSE",
}

SECTOR_MAP: Dict[str, str] = {
    "ABSA":  "Banking",
    "SCBK":  "Banking",
    "EQTY":  "Banking",
    "KCB":   "Banking",
    "NBK":   "Banking",
    "NCBA":  "Banking",
    "COOP":  "Banking",
    "DTK":   "Banking",
    "CFC":   "Banking",
    "IMH":   "Banking",
    "FANB":  "Banking",
    "HFCK":  "Banking",
    "SCOM":  "Telecoms",
    "EABL":  "FMCG",
    "BATK":  "FMCG",
    "UNGA":  "FMCG",
    "BAMB":  "Construction",
    "EAPC":  "Construction",
    "BRIT":  "Insurance",
    "JUB":   "Insurance",
    "SLAM":  "Insurance",
    "NMG":   "Media",
    "SGL":   "Media",
    "SCAN":  "Media",
    "KPLC":  "Energy",
    "KEGN":  "Energy",
    "SASN":  "Agriculture",
    "WTK":   "Agriculture",
    "KAPA":  "Agriculture",
    "CARB":  "Manufacturing",
    "BOC":   "Manufacturing",
    "CPKL":  "Manufacturing",
    "UMME":  "Energy",
    "BKG":   "Banking",
    "XPRS":  "Logistics",
    "FTGH":  "Diversified",
    "HAFR":  "Real Estate",
    "HBZE":  "Entertainment",
    "TCL":   "Infrastructure",
    "TPSE":  "Hospitality",
    "NSE":   "Financial Services",
}

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def get_ticker(company_name: str) -> Optional[str]:
    if not company_name:
        return None
    name_lower = company_name.lower()
    for key, ticker in TICKER_MAP.items():
        if key in name_lower:
            return ticker
    return None


def get_ticker_from_filename(filename: str) -> Optional[str]:
    fn_lower = filename.lower()
    for key, ticker in TICKER_MAP.items():
        if key.replace(" ", "_") in fn_lower or key.replace(" ", "") in fn_lower:
            return ticker
        # try partial match
        if key.split()[0] in fn_lower:
            return ticker
    return None


def parse_period_from_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract (period_label, period_end_date_str, period_type) from filename.

    e.g.
      ABSA_Bank_Kenya_Plc_30_Jun_2024_financials.pdf
        → ("H1 FY2024", "2024-06-30", "half_year")
      ABSA_Bank_Kenya_Plc_31_Dec_2023_audited.pdf
        → ("FY2023", "2023-12-31", "annual")
      SAFARICOM_PLC_..._31_March_2024_...pdf
        → ("FY2024", "2024-03-31", "annual")
      KCB_Group_Plc_31_Mar_2024_audited.pdf
        → ("FY2023", "2024-03-31", "annual")  ← March 31 = Safaricom FY end
    """
    # Pattern: _DD_MonthName_YYYY_ or _DD_Mon_YYYY_
    date_pat = re.compile(
        r'_(\d{1,2})_([A-Za-z]+)_(\d{4})',
        re.IGNORECASE
    )
    m = date_pat.search(filename)
    if not m:
        return None, None, None

    day   = int(m.group(1))
    month_str = m.group(2).lower()
    year  = int(m.group(3))

    month = MONTH_MAP.get(month_str)
    if not month:
        return None, None, None

    try:
        d = date(year, month, day)
    except ValueError:
        return None, None, None

    date_str = d.isoformat()

    # Determine period label + type
    # Annual: Dec 31 / Dec 30 → FY{year}
    # Annual: Mar 31 → FY{year} for Safaricom (fiscal year Apr-Mar)
    # Half year: Jun 30 → H1 FY{year} (for Dec FY) or H2 FY{year-1} for Mar FY
    # Quarter: Mar 31, Jun 30, Sep 30 for calendar-year companies
    fn_lower = filename.lower()
    is_safaricom = "safaricom" in fn_lower or "scom" in fn_lower

    if month == 12 and day >= 30:
        period_label = f"FY{year}"
        period_type  = "annual"
    elif month == 3 and day >= 31:
        if is_safaricom:
            period_label = f"FY{year}"
            period_type  = "annual"
        else:
            # For banks with Dec year-end, March = Q1
            period_label = f"Q1 FY{year}"
            period_type  = "quarter"
    elif month == 6 and day >= 30:
        if is_safaricom:
            period_label = f"H1 FY{year}"
            period_type  = "half_year"
        else:
            period_label = f"H1 FY{year}"
            period_type  = "half_year"
    elif month == 9 and day >= 30:
        period_label = f"Q3 FY{year}"
        period_type  = "quarter"
    elif month == 1 and day >= 31:
        period_label = f"FY{year}"  # Some companies have Jan FY end
        period_type  = "annual"
    elif month == 7 and day >= 31:
        period_label = f"FY{year}"  # Some companies (Carbacid) have Jul FY end
        period_type  = "annual"
    else:
        # Generic fallback using month
        period_label = f"{date_str}"
        period_type  = "unknown"

    return period_label, date_str, period_type


# ── PDF extraction (reuse core logic from extract_financials_v2.py) ────────────

def extract_text(path: Path) -> str:
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t:
                chunks.append(t)
    return "\n".join(chunks)


def _fix_doubled_token(token: str) -> str:
    if not any(c.isdigit() for c in token):
        return token
    if len(token) < 4 or len(token) % 2 != 0:
        return token
    if all(token[i] == token[i + 1] for i in range(0, len(token), 2)):
        return token[::2]
    return token


def normalise_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = line.replace("\u2019", "'")
    line = line.replace("\u2018", "'")
    line = re.sub(r"(\d)\s+,(\d)", r"\1,\2", line)
    line = re.sub(r"(?<!\d)(\d)\s+(\d{1,2},\d{3})", r"\1\2", line)
    line = re.sub(r"(?<!\d)(\d)\s+(\d{1,2}\.\d+)", r"\1\2", line)
    line = re.sub(r"(?<!\d)(\d)\s+\.(\d+)", r"\1.\2", line)
    tokens = line.split()
    tokens = [_fix_doubled_token(t) for t in tokens]
    line = " ".join(tokens)
    line = " ".join(line.split())
    return line


def get_lines(text: str) -> List[str]:
    return [normalise_line(l) for l in text.splitlines() if l.strip()]


_COMMA_NUM = re.compile(r"\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b")
_PAREN_NUM = re.compile(r"\((\d[\d,]*(?:\.\d+)?)\)")
_DECIMAL   = re.compile(r"\b(\d+\.\d+)\b")
_ROW_REF   = re.compile(r"^\s*\d{1,2}(?:\.\d{1,2})?\s*\.?\s+")


def _candidates(line: str) -> List[Tuple[float, int]]:
    results: List[Tuple[float, int]] = []
    for m in _PAREN_NUM.finditer(line):
        try:
            results.append((-float(m.group(1).replace(",", "")), m.start()))
        except ValueError:
            pass
    for m in _COMMA_NUM.finditer(line):
        try:
            results.append((float(m.group(1).replace(",", "")), m.start()))
        except ValueError:
            pass
    for m in _DECIMAL.finditer(line):
        if not any(abs(pos - m.start()) < 5 for _, pos in results):
            try:
                results.append((float(m.group(1)), m.start()))
            except ValueError:
                pass
    results.sort(key=lambda x: x[1])
    return results


def parse_value(line: str, want_ratio: bool = False) -> Optional[float]:
    if not line:
        return None
    stripped = _ROW_REF.sub("", line)
    hits = _candidates(stripped)
    if not hits:
        return None
    if not want_ratio:
        large = [(v, p) for v, p in hits if abs(v) >= 1000 or v != int(v)]
        if large:
            return large[0][0]
        return hits[0][0]
    else:
        return hits[0][0]


def find_line(lines: List[str], *patterns: str) -> Optional[str]:
    pats = [p.lower() for p in patterns]
    for line in lines:
        low = line.lower()
        if any(p in low for p in pats):
            return line
    return None


def _keyword_before_first_large_number(line: str, pattern: str) -> bool:
    """
    Return True if *pattern* appears BEFORE the first large (≥1000) number in *line*.
    This filters out lines where the pattern is in narrative text after tabular data.
    e.g.  "1.5 Total interest income 48,591,544 ...  Profit after tax grew..." → False (narrative)
          "12 Profit after tax and exceptional items 13,797,373 ..." → True (label row)
    """
    stripped = _ROW_REF.sub("", line)
    low = stripped.lower()
    pat_pos = low.find(pattern.lower())
    if pat_pos < 0:
        return False
    # Find the position of the first large number in the stripped line
    for m in _COMMA_NUM.finditer(stripped):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if abs(val) >= 1000:
            return pat_pos < m.start()
    # No large number found — the pattern is the label by default
    return True


def find_line_excluding(lines: List[str], pattern: str, *excludes: str) -> Optional[str]:
    excl = [e.lower() for e in excludes]
    # First pass: prefer lines where pattern is a ROW LABEL (before numbers) AND has large value
    for line in lines:
        low = line.lower()
        if pattern.lower() in low and not any(e in low for e in excl):
            v = parse_value(line)
            if v is not None and abs(v) >= 1000 and _keyword_before_first_large_number(line, pattern):
                return line
    # Second pass: any matching line with a large number (relax position check)
    for line in lines:
        low = line.lower()
        if pattern.lower() in low and not any(e in low for e in excl):
            v = parse_value(line)
            if v is not None and abs(v) >= 1000:
                return line
    # Third pass: any matching line with any numeric value
    for line in lines:
        low = line.lower()
        if pattern.lower() in low and not any(e in low for e in excl):
            if parse_value(line) is not None:
                return line
    # Fourth pass: any matching line as fallback
    for line in lines:
        low = line.lower()
        if pattern.lower() in low and not any(e in low for e in excl):
            return line
    return None


def detect_units(text: str) -> str:
    t = text.lower()
    # "Kes 000" or "Ksh 000" → explicitly thousands (multi-period NSE table format)
    if re.search(r"\bkes\s+000\b", t) or re.search(r"\bksh\s+000\b", t):
        return "KES_thousands"
    # Millions check — handle "KShs Millions", "KES Millions", etc.
    if ("kes millions" in t or "ksh millions" in t or "kshs millions" in t
            or "in millions" in t
            or "ksh mn" in t or "kshs mn" in t or "ksh. mn" in t or "kshs. mn" in t):
        return "KES_millions"
    # Billions check — handle "KShs Bn" phrase AND inline "KShs <number>Bn" patterns
    if ("kes billions" in t or "ksh billions" in t or "in billions" in t
            or "kshs bn" in t or "ksh bn" in t or "kes bn" in t
            or "kshs. bn" in t or "ksh. bn" in t
            or re.search(r"kshs?\s+[\d,.]+bn\b", t) is not None):
        return "KES_billions"
    if "thousands" in t:
        return "KES_thousands"
    return "KES_thousands"


def units_to_thousands_multiplier(units: str) -> float:
    """Return multiplier to convert to KES thousands."""
    if units == "KES_millions":
        return 1000.0
    if units == "KES_billions":
        return 1_000_000.0
    return 1.0  # already in thousands


def extract_bank_metrics(lines):
    def val(line, ratio=False):
        return parse_value(line, want_ratio=ratio) if line else None

    nii_line = find_line(lines, "net interest income")
    inc_line = find_line(lines, "total operating income", "total income")
    opex_line = find_line(lines, "other operating expenses", "operating expenses")
    pbt_line = find_line_excluding(lines, "profit before tax", "deferred", "income tax expense")
    if pbt_line is None:
        pbt_line = find_line_excluding(lines, "profit before taxation", "deferred")
    # Try most-specific patterns first; "profit for the year" is last (can appear in equity statements)
    pat_line = find_line_excluding(lines, "profit after tax", "retained", "balance at", "total equity",
                                   "loans and advances", "advances to customers")
    if pat_line is None:
        # KCB / DTK style: "Profit/(loss) after tax and exceptional items"
        pat_line = find_line_excluding(lines, "profit/(loss) after tax", "retained", "balance",
                                       "total equity", "loans and advances")
    if pat_line is None:
        pat_line = find_line_excluding(lines, "profit after exceptional items", "retained")
    if pat_line is None:
        pat_line = find_line_excluding(lines, "net profit for the period", "retained")
    if pat_line is None:
        pat_line = find_line_excluding(lines, "profit for the period", "retained", "balance", "total equity",
                                       "loans and advances", "advances to customers")
    if pat_line is None:
        # Last resort — can appear in equity section, so exclude those
        pat_line = find_line_excluding(lines, "profit for the year", "retained", "balance", "total equity",
                                       "loans and advances", "advances to customers",
                                       "at 1 january", "at 31 december", "at 1 april")
    eps_line = find_line(lines, "earnings per share", "basic eps")
    dps_line = find_line(lines, "dividend per share", "dividends per share")
    assets_line = find_line(lines, "total assets", "total asset")
    equity_line = find_line_excluding(lines, "total shareholders' funds", "minimum", "excess", "deficiency")
    if equity_line is None:
        equity_line = find_line_excluding(lines, "total shareholders funds", "minimum")
    if equity_line is None:
        equity_line = find_line_excluding(lines, "total equity", "minimum")
    if equity_line is None:
        for candidate in lines:
            if "shareholder" in candidate.lower():
                v = parse_value(candidate)
                if v is not None and abs(v) >= 1000:
                    equity_line = candidate
                    break
    deposits_line = find_line(lines, "customer deposits")
    loans_line = find_line_excluding(lines, "loans and advances to customers", "non-performing", "non performing", "insider", "fees", "provision")
    if loans_line is None:
        loans_line = find_line_excluding(lines, "loans and advances", "non-performing", "non performing", "insider", "fees", "provision", "contingent")
    if loans_line is None:
        loans_line = find_line(lines, "net loans", "advances to customers")

    dps_raw = val(dps_line, ratio=True)
    dps = dps_raw if (dps_raw is None or abs(dps_raw) < 100) else None

    return {
        "net_interest_income": val(nii_line),
        "revenue":             val(inc_line),
        "operating_expenses":  val(opex_line),
        "profit_before_tax":   val(pbt_line),
        "profit_after_tax":    val(pat_line),
        "basic_eps":           val(eps_line, ratio=True),
        "dividend_per_share":  dps,
        "total_assets":        val(assets_line),
        "total_equity":        val(equity_line),
        "customer_deposits":   val(deposits_line),
        "loans_and_advances":  val(loans_line),
        "operating_cash_flow": None,
        "capex":               None,
        "ebitda":              None,
        "mpesa_revenue":       None,
    }


def extract_telco_metrics(lines):
    def val(line, ratio=False):
        return parse_value(line, want_ratio=ratio) if line else None

    rev_line = find_line(lines, "service revenue", "total revenue", "revenue")
    ebitda_line = find_line(lines, "ebitda")
    opex_line = find_line(lines, "operating profit", "profit from operations", "ebit")
    pbt_line = find_line(lines, "profit before tax", "profit before income tax")
    pat_line = find_line_excluding(lines, "profit after tax", "retained")
    if pat_line is None:
        pat_line = find_line_excluding(lines, "profit for the year", "retained", "balance")
    eps_line = find_line(lines, "basic", "earnings per share", "eps")
    dps_line = find_line(lines, "dividend per share", "dividends per share", "proposed dividend per share")
    assets_line = find_line(lines, "total assets")
    equity_line = find_line(lines, "total equity", "shareholders' equity", "shareholders equity")
    mpesa_line = find_line(lines, "m-pesa revenue", "mpesa revenue", "mobile money revenue")
    ocf_line = find_line(lines, "net cash from operating", "net cash generated from operating", "cash generated from operations")
    capex_line = find_line(lines, "capital expenditure", "capex", "purchase of property", "purchase of plant")

    dps_raw = val(dps_line, ratio=True)
    dps = dps_raw if (dps_raw is None or abs(dps_raw) < 100) else None

    return {
        "net_interest_income": None,
        "revenue":             val(rev_line),
        "operating_expenses":  val(opex_line),
        "profit_before_tax":   val(pbt_line),
        "profit_after_tax":    val(pat_line),
        "basic_eps":           val(eps_line, ratio=True),
        "dividend_per_share":  dps,
        "total_assets":        val(assets_line),
        "total_equity":        val(equity_line),
        "customer_deposits":   None,
        "loans_and_advances":  None,
        "operating_cash_flow": val(ocf_line),
        "capex":               val(capex_line),
        "ebitda":              val(ebitda_line),
        "mpesa_revenue":       val(mpesa_line),
    }


def extract_generic_metrics(lines):
    def val(line, ratio=False):
        return parse_value(line, want_ratio=ratio) if line else None

    pat_line = find_line_excluding(lines, "profit after tax", "retained", "balance", "total equity")
    if pat_line is None:
        pat_line = find_line_excluding(lines, "profit for the year", "retained", "balance")
    if pat_line is None:
        pat_line = find_line_excluding(lines, "profit for the period", "retained", "balance")

    return {
        "net_interest_income": None,
        "revenue":             val(find_line(lines, "revenue", "turnover", "total income", "total operating income")),
        "operating_expenses":  val(find_line(lines, "operating expenses")),
        "profit_before_tax":   val(find_line_excluding(lines, "profit before tax", "deferred")),
        "profit_after_tax":    val(pat_line),
        "basic_eps":           val(find_line(lines, "earnings per share", "basic eps"), ratio=True),
        "dividend_per_share":  val(find_line(lines, "dividend per share"), ratio=True),
        "total_assets":        val(find_line(lines, "total assets")),
        "total_equity":        val(find_line(lines, "total equity", "shareholders")),
        "customer_deposits":   None,
        "loans_and_advances":  None,
        "operating_cash_flow": val(find_line(lines, "net cash from operating")),
        "capex":               val(find_line(lines, "capital expenditure", "purchase of property")),
        "ebitda":              val(find_line(lines, "ebitda")),
        "mpesa_revenue":       None,
    }


BANK_KEYWORDS = ["absa", "standard chartered", "stanchart", "equity bank", "equity group",
    "kcb", "cooperative bank", "co-op bank", "diamond trust", "dtb", "ncba", "stanbic",
    "family bank", "im bank", "i&m", "hf group", "national bank", "bank"]
TELCO_KEYWORDS = ["safaricom", "telkom", "airtel"]


def classify_company(name: str, filename: str, text_snippet: str) -> str:
    probe = " ".join(filter(None, [name, filename, text_snippet[:500]])).lower()
    if any(k in probe for k in TELCO_KEYWORDS):
        return "telco"
    if any(k in probe for k in BANK_KEYWORDS):
        return "bank"
    return "generic"


def extract_company_name(filename: str, index_company: Optional[str]) -> str:
    """Best-effort company name from filename."""
    if index_company:
        return index_company

    # Strip date and suffix from filename
    name = Path(filename).stem
    # Remove date pattern (e.g. _30_Jun_2024)
    name = re.sub(r'_\d{1,2}_[A-Za-z]+_\d{4}.*', '', name)
    # Convert underscores to spaces
    name = name.replace('_', ' ').strip()
    return name


# ── main scan ──────────────────────────────────────────────────────────────────

def scan_all_pdfs(min_year: int = 0) -> List[Path]:
    """Find all PDF files in data/nse/ year subfolders. Optional min_year filter."""
    pdfs = []
    for year_dir in sorted(DATA_ROOT.iterdir()):
        if year_dir.is_dir() and year_dir.name.isdigit():
            if min_year and int(year_dir.name) < min_year:
                continue
            pdfs.extend(sorted(year_dir.glob("*.pdf")))
    return pdfs


def load_index_company_map() -> Dict[str, Dict]:
    """Build a map from local_path → index entry for quick lookup."""
    index_file = DATA_ROOT / "index_2023_2025.json"
    if not index_file.exists():
        return {}
    with index_file.open(encoding="utf-8") as f:
        raw = json.load(f)
    items = list(raw.values()) if isinstance(raw, dict) else raw
    result = {}
    for item in items:
        if isinstance(item, dict) and item.get("local_path"):
            result[Path(item["local_path"]).name] = item
    return result


def process_pdf(pdf_path: Path, index_entry: Optional[Dict]) -> Optional[Dict]:
    filename = pdf_path.name
    company_name = extract_company_name(filename, index_entry.get("company") if index_entry else None)
    ticker = get_ticker(company_name) or get_ticker_from_filename(filename)

    period_label, period_end_date, period_type = parse_period_from_filename(filename)
    # If index has period info, prefer it
    if index_entry and index_entry.get("period"):
        period_label = index_entry["period"]

    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(f"  ✗ {filename}: {e}", file=sys.stderr)
        return None

    lines = get_lines(text)
    snippet = text[:1000]

    company_type = classify_company(company_name, filename, snippet)
    units = detect_units(text)
    mult = units_to_thousands_multiplier(units)

    if company_type == "bank":
        metrics = extract_bank_metrics(lines)
    elif company_type == "telco":
        metrics = extract_telco_metrics(lines)
    else:
        metrics = extract_generic_metrics(lines)

    # Apply unit multiplier to convert everything to KES thousands
    financial_fields = [
        "net_interest_income", "revenue", "operating_expenses",
        "profit_before_tax", "profit_after_tax", "total_assets",
        "total_equity", "customer_deposits", "loans_and_advances",
        "operating_cash_flow", "capex", "ebitda", "mpesa_revenue",
    ]
    if mult != 1.0:
        for field in financial_fields:
            if metrics[field] is not None:
                metrics[field] = round(metrics[field] * mult)

    # Try to infer year from filename if we have a period
    year = int(period_end_date[:4]) if period_end_date else (index_entry.get("year") if index_entry else None)

    return {
        "company":             company_name,
        "ticker":              ticker,
        "sector":              SECTOR_MAP.get(ticker, "Other") if ticker else "Other",
        "period":              period_label,
        "period_end_date":     period_end_date,
        "period_type":         period_type,
        "year":                year,
        "units_source":        units,
        "source_file":         filename,
        "url":                 index_entry.get("url", "") if index_entry else "",
        **metrics,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    # CLI args: optional company names and/or --since YEAR
    # e.g.  python extract_all.py absa safaricom --since 2020
    raw_args = sys.argv[1:]
    min_year = 0
    company_filters = []
    i = 0
    while i < len(raw_args):
        if raw_args[i] == "--since" and i + 1 < len(raw_args):
            min_year = int(raw_args[i + 1])
            i += 2
        else:
            company_filters.append(raw_args[i].lower())
            i += 1

    if min_year:
        print(f"Filtering to years >= {min_year}")
    if company_filters:
        print(f"Filtering to companies: {company_filters}")

    pdfs = scan_all_pdfs(min_year=min_year)
    if company_filters:
        pdfs = [p for p in pdfs if any(f in p.name.lower() for f in company_filters)]
    print(f"Processing {len(pdfs)} PDF files.")

    index_map = load_index_company_map()
    print(f"Index has {len(index_map)} entries for cross-referencing.")

    results = []
    errors  = 0

    for i, pdf_path in enumerate(pdfs, 1):
        filename = pdf_path.name
        index_entry = index_map.get(filename)
        print(f"[{i}/{len(pdfs)}] {filename[:60]}")

        entry = process_pdf(pdf_path, index_entry)
        if entry:
            results.append(entry)
        else:
            errors += 1

    print(f"\n✓ Extracted: {len(results)}  Errors: {errors}")
    print(f"Writing to {OUTPUT_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary by company
    companies: Dict[str, int] = {}
    for r in results:
        c = r.get("ticker") or r.get("company", "?")
        companies[c] = companies.get(c, 0) + 1
    print("\nCompany summary:")
    for c, count in sorted(companies.items()):
        print(f"  {c}: {count} periods")
    print("\n✓ Done")


if __name__ == "__main__":
    main()
