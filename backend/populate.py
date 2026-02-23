"""
populate.py -- One-pass pipeline: scan PDFs -> extract financials -> write data.js + financials.json

Scans all PDFs under data/nse/, matches to a company registry, extracts financials
using the v2 extraction logic, then writes:
  - data/nse/financials.json   (raw extracted data, all periods)
  - frontend/data.js           (annual data only, formatted for the site)

Usage (from the repo root or backend/ with venv active):
    python backend/populate.py                            # process all companies
    python backend/populate.py --dry-run                  # preview, no writes
    python backend/populate.py --company ABSA STANCHART   # specific companies only
    python backend/populate.py --all-periods              # include interim results in data.js
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber

# -- Paths ---------------------------------------------------------------------
BACKEND_DIR     = Path(__file__).parent
DATA_ROOT       = BACKEND_DIR.parent / "data" / "nse"
FRONTEND_DATA   = BACKEND_DIR.parent / "frontend" / "data.js"
FINANCIALS_JSON = DATA_ROOT / "financials.json"

sys.stdout.reconfigure(encoding="utf-8")

# -- Month helpers -------------------------------------------------------------
MONTH_MAP = {
    "jan":1, "feb":2, "mar":3, "apr":4, "may":5, "jun":6,
    "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12,
    "january":1, "february":2, "march":3, "april":4, "june":6,
    "july":7, "august":8, "september":9, "october":10, "november":11, "december":12,
}
MONTH_ABBREV = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

# -- Company registry ----------------------------------------------------------
@dataclass
class CompanyConfig:
    key:          str
    name:         str
    ticker:       str
    sector:       str
    company_type: str          # "bank" | "telco" | "generic"
    units:        str          # "thousands" | "millions"
    fy_end_month: int          # fiscal year-end month (12=Dec, 3=Mar, 6=Jun...)
    latest_price: float = 0.0
    emoji:        str   = ""
    keywords:     List[str] = field(default_factory=list)


def _co(key, name, ticker, sector, ctype, units, fy_month, keywords,
        price=0.0, emoji=""):
    """Shorthand constructor so positional list is readable."""
    return CompanyConfig(
        key=key, name=name, ticker=ticker, sector=sector,
        company_type=ctype, units=units, fy_end_month=fy_month,
        latest_price=price, emoji=emoji, keywords=keywords,
    )


COMPANY_REGISTRY: List[CompanyConfig] = [
    _co("ABSA",       "ABSA Bank Kenya PLC",              "ABSA", "Banking",            "bank",    "thousands", 12, ["ABSA_Bank_Kenya", "Absa_Bank_Kenya"],                      14.20),
    _co("STANCHART",  "Standard Chartered Bank Kenya",    "SCBK", "Banking",            "bank",    "thousands", 12, ["Standard_Chartered_Bank_Kenya", "Standard_Chartered_Bank_Ltd"], 195.0),
    _co("SAFARICOM",  "Safaricom PLC",                    "SCOM", "Telecom",            "telco",   "millions",   3, ["Safaricom"],                                               15.85),
    _co("KCB",        "KCB Group PLC",                    "KCB",  "Banking",            "bank",    "thousands", 12, ["KCB_Group", "KCB_KENYA"],                                  34.50),
    _co("EQUITY",     "Equity Group Holdings",            "EQTY", "Banking",            "bank",    "thousands", 12, ["Equity_Group"],                                            40.50),
    _co("COOP",       "Co-operative Bank of Kenya",       "COOP", "Banking",            "bank",    "thousands", 12, ["Co_operative_Bank"],                                       12.35),
    _co("NCBA",       "NCBA Group PLC",                   "NCBA", "Banking",            "bank",    "thousands", 12, ["NCBA_Group"]),
    _co("DTB",        "Diamond Trust Bank Kenya",         "DTB",  "Banking",            "bank",    "thousands", 12, ["Diamond_Trust_Bank_Kenya"]),
    _co("STANBIC",    "Stanbic Holdings PLC",             "CFC",  "Banking",            "bank",    "thousands", 12, ["Stanbic_Holdings"]),
    _co("HF",         "HF Group PLC",                     "HFCK", "Banking",            "bank",    "thousands", 12, ["HF_Group"]),
    _co("FAMILYBANK", "Family Bank Ltd",                  "FAMB", "Banking",            "bank",    "thousands", 12, ["Family_Bank"]),
    _co("IMBANK",     "I&M Group PLC",                    "IMH",  "Banking",            "bank",    "thousands", 12, ["I_M_Group"]),
    _co("BKGROUP",    "BK Group PLC",                     "BKG",  "Banking",            "bank",    "thousands", 12, ["BK_Group"]),
    _co("KMRC",       "Kenya Mortgage Refinance Company", "KMRC", "Finance",            "bank",    "thousands", 12, ["Kenya_Mortgage"]),
    _co("EABL",       "East African Breweries PLC",       "EABL", "Manufacturing",      "generic", "thousands",  6, ["East_African_Breweries"]),
    _co("BAT",        "BAT Kenya PLC",                    "BAT",  "Manufacturing",      "generic", "thousands", 12, ["BAT_Kenya"]),
    _co("BAMB",       "Bamburi Cement PLC",               "BAMB", "Construction",       "generic", "thousands", 12, ["Bamburi_Cement"]),
    _co("BRITAM",     "Britam Holdings PLC",              "BRIT", "Insurance",          "generic", "thousands", 12, ["Britam_Holdings"]),
    _co("JUBILEE",    "Jubilee Holdings Limited",         "JUB",  "Insurance",          "generic", "thousands", 12, ["Jubilee_Holdings"]),
    _co("NMG",        "Nation Media Group PLC",           "NMG",  "Media",              "generic", "thousands", 12, ["Nation_Media_Group"]),
    _co("KENGEN",     "KenGen PLC",                       "KEGN", "Energy",             "generic", "thousands",  6, ["KenGen"]),
    _co("KPLC",       "Kenya Power & Lighting Co.",       "KPLC", "Energy",             "generic", "thousands",  6, ["Kenya_Power"]),
    _co("NSEPLC",     "Nairobi Securities Exchange PLC",  "NSE",  "Financial Services", "generic", "thousands", 12, ["Nairobi_Securities_Exchange", "NSE_Plc"]),
    _co("SANLAM",     "Sanlam Kenya PLC",                 "SLAM", "Insurance",          "generic", "thousands", 12, ["Sanlam_Kenya"]),
    _co("SASINI",     "Sasini PLC",                       "SASN", "Agriculture",        "generic", "thousands",  9, ["Sasini"]),
    _co("CARBACID",   "Carbacid Investments PLC",         "CABL", "Manufacturing",      "generic", "thousands",  7, ["Carbacid_Investments"]),
    _co("KAKUZI",     "Kakuzi PLC",                       "KUKZ", "Agriculture",        "generic", "thousands", 12, ["Kakuzi"]),
    _co("TPS",        "TPS Eastern Africa PLC",           "TPSE", "Hospitality",        "generic", "thousands", 12, ["TPS_Eastern_Africa"]),
    _co("SCANGROUP",  "WPP Scangroup PLC",                "SCAN", "Media",              "generic", "thousands", 12, ["Wpp_Scangroup"]),
    _co("TRANSCENT",  "TransCentury PLC",                 "TCL",  "Infrastructure",     "generic", "thousands", 12, ["TransCentury"]),
    _co("LIMTEA",     "Limuru Tea PLC",                   "LIMT", "Agriculture",        "generic", "thousands", 12, ["LIMURU_TEA", "Limuru_Tea"]),
    _co("EXPRESS",    "Express Kenya PLC",                "EXPR", "Logistics",          "generic", "thousands", 12, ["Express_Kenya"]),
    _co("EAPC",       "East African Portland Cement",     "PORT", "Construction",       "generic", "thousands", 12, ["East_African_Portland"]),
    _co("FLAME",      "Flame Tree Group Holdings",        "FTG",  "Consumer",           "generic", "thousands", 12, ["Flame_Tree"]),
    _co("HOMEBOYZ",   "Homeboyz Entertainment PLC",       "HBL",  "Media",              "generic", "thousands", 12, ["Homeboyz"]),
    _co("HOMEAFRIKA", "Home Afrika Limited",              "HAFR", "Real Estate",        "generic", "thousands", 12, ["Home_Afrika"]),
    _co("SGTMEDIA",   "Standard Group PLC",               "SGL",  "Media",              "generic", "thousands", 12, ["Standard_Group", "The_Standard_Group"]),
    _co("BOC",        "BOC Kenya PLC",                    "BOC",  "Manufacturing",      "generic", "thousands", 12, ["BOC_Kenya"]),
    _co("UMEME",      "Umeme Limited",                    "UMME", "Energy",             "generic", "thousands", 12, ["Umeme_Limited"]),
    _co("KAPCHORUA",  "Kapchorua Tea Kenya PLC",          "KTDA", "Agriculture",        "generic", "thousands",  3, ["Kapchorua_Tea"]),
    _co("EAAGADS",    "Eaagads Limited",                  "EGAD", "Agriculture",        "generic", "thousands",  3, ["Eaagads"]),
    _co("CROWN",      "Crown Paints Kenya PLC",           "CRON", "Manufacturing",      "generic", "thousands", 12, ["Crown_Paints"]),
    _co("EAC",        "EAC PLC",                          "EAC",  "Manufacturing",      "generic", "thousands",  6, ["EAC_Plc"]),
]


def match_company(pdf_name: str) -> Optional[CompanyConfig]:
    """Match a PDF filename to a company config (case-insensitive)."""
    pdf_lower = pdf_name.lower()
    for company in COMPANY_REGISTRY:
        for kw in company.keywords:
            if kw.lower() in pdf_lower:
                return company
    return None


# -- Period parsing ------------------------------------------------------------
_DATE_PAT = re.compile(
    r"(\d{1,2})[_\s]?"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    r"|January|February|March|April|May|June|July|August"
    r"|September|October|November|December)"
    r"[_\s]?(\d{4})",
    re.IGNORECASE,
)


def parse_period(filename: str) -> Optional[Dict[str, Any]]:
    """Extract date info from a filename. Returns None if no date found."""
    m = _DATE_PAT.search(filename)
    if not m:
        return None
    month_str = m.group(2).lower()[:3]
    month = MONTH_MAP.get(month_str)
    if month is None:
        return None
    year = int(m.group(3))
    is_audited = "audited" in filename.lower()
    return {
        "day": int(m.group(1)),
        "month": month,
        "year": year,
        "is_audited": is_audited,
        "period_str": f"{MONTH_ABBREV.get(month,'?')}{year}",
    }


def is_annual(period: Dict, company: CompanyConfig) -> bool:
    """True if this period represents a full annual result.

    A result is annual if its month matches the company's fiscal year-end month.
    We don't require the '_audited' label because some companies (e.g. StanChart)
    label full-year results as '_financials' rather than '_audited'.
    """
    return period["month"] == company.fy_end_month


def fiscal_year_label(period: Dict, company: CompanyConfig) -> int:
    """Calendar year label to use for this period in data.js."""
    return period["year"]


# -- PDF text extraction -------------------------------------------------------
def extract_text(pdf_path: Path) -> str:
    chunks: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t:
                chunks.append(t)
    return "\n".join(chunks)


def _fix_doubled_token(token: str) -> str:
    """Fix Safaricom PDF doubled-character artifact: '114433..0088' -> '143.08'."""
    if not any(c.isdigit() for c in token):
        return token
    if len(token) < 4 or len(token) % 2 != 0:
        return token
    if all(token[i] == token[i + 1] for i in range(0, len(token), 2)):
        return token[::2]
    return token


def normalise_line(line: str) -> str:
    line = line.replace("\u00a0", " ").replace("\u2019", "'").replace("\u2018", "'")
    line = re.sub(r"(\d)\s+,(\d)", r"\1,\2", line)
    line = re.sub(r"(?<!\d)(\d)\s+(\d{1,2},\d{3})", r"\1\2", line)
    line = re.sub(r"(?<!\d)(\d)\s+(\d{1,2}\.\d+)", r"\1\2", line)
    line = re.sub(r"(?<!\d)(\d)\s+\.(\d+)", r"\1.\2", line)
    tokens = [_fix_doubled_token(t) for t in line.split()]
    return " ".join(tokens)


def get_lines(text: str) -> List[str]:
    return [normalise_line(l) for l in text.splitlines() if l.strip()]


# -- Number parsing ------------------------------------------------------------
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
    return hits[0][0]


def find_line(lines: List[str], *patterns: str) -> Optional[str]:
    pats = [p.lower() for p in patterns]
    for line in lines:
        if any(p in line.lower() for p in pats):
            return line
    return None


def find_line_excluding(lines: List[str], pattern: str, *excludes: str) -> Optional[str]:
    excl = [e.lower() for e in excludes]
    for line in lines:
        low = line.lower()
        if pattern.lower() in low and not any(e in low for e in excl):
            return line
    return None


# -- Metric extractors ---------------------------------------------------------
def extract_bank_metrics(lines: List[str]) -> Dict[str, Optional[float]]:
    def val(line: Optional[str], ratio: bool = False) -> Optional[float]:
        return parse_value(line, want_ratio=ratio) if line else None

    nii    = val(find_line(lines, "net interest income"))
    income = val(find_line(lines, "total operating income", "total income"))
    opex   = val(find_line(lines, "other operating expenses", "operating expenses"))

    pbt_line = find_line_excluding(lines, "profit before tax", "deferred", "income tax expense")
    if not pbt_line:
        pbt_line = find_line_excluding(lines, "profit before taxation", "deferred")
    pbt = val(pbt_line)

    pat_line = find_line_excluding(
        lines, "profit after tax",
        "retained", "balance at", "total equity", "loans and advances", "advances to customers"
    )
    if not pat_line:
        pat_line = find_line_excluding(lines, "profit for the year", "retained", "balance", "total equity")
    if not pat_line:
        pat_line = find_line_excluding(lines, "profit for the period", "retained", "balance", "total equity")
    if not pat_line:
        pat_line = find_line_excluding(lines, "net profit for the period", "retained")
    pat = val(pat_line)

    eps = val(find_line(lines, "earnings per share", "basic eps"), ratio=True)

    dps_line = find_line(lines, "dividend per share", "dividends per share")
    dps_raw  = val(dps_line, ratio=True)
    dps = dps_raw if (dps_raw is None or abs(dps_raw) < 1000) else None

    assets_line = find_line(lines, "total assets", "total asset")
    assets = val(assets_line)

    equity_line = find_line_excluding(lines, "total shareholders' funds", "minimum", "excess")
    if not equity_line:
        equity_line = find_line_excluding(lines, "total shareholders funds", "minimum")
    if not equity_line:
        equity_line = find_line_excluding(lines, "total equity", "minimum")
    if not equity_line:
        for cand in lines:
            if "shareholder" in cand.lower():
                v = parse_value(cand)
                if v is not None and abs(v) >= 1000:
                    equity_line = cand
                    break
    equity = val(equity_line)

    deposits = val(find_line(lines, "customer deposits"))
    loans_line = find_line(lines, "loans and advances to customers", "loans and advances")
    if not loans_line:
        loans_line = find_line(lines, "net loans", "advances to customers")
    loans = val(loans_line)

    return {
        "net_interest_income": nii,
        "revenue":             income,
        "operating_expenses":  opex,
        "profit_before_tax":   pbt,
        "profit_after_tax":    pat,
        "basic_eps":           eps,
        "dividend_per_share":  dps,
        "total_assets":        assets,
        "total_equity":        equity,
        "customer_deposits":   deposits,
        "loans_and_advances":  loans,
        "operating_cash_flow": None,
        "capex":               None,
        "ebitda":              None,
        "mpesa_revenue":       None,
    }


def extract_telco_metrics(lines: List[str]) -> Dict[str, Optional[float]]:
    def val(line: Optional[str], ratio: bool = False) -> Optional[float]:
        return parse_value(line, want_ratio=ratio) if line else None

    revenue = val(find_line(lines, "service revenue", "total revenue", "revenue"))
    ebitda  = val(find_line(lines, "ebitda"))
    opex    = val(find_line(lines, "operating profit", "profit from operations", "ebit"))
    pbt     = val(find_line(lines, "profit before tax", "profit before income tax"))
    pat     = val(find_line_excluding(lines, "profit after tax", "retained"))

    eps = val(find_line(lines, "basic", "earnings per share", "eps"), ratio=True)

    dps_line = find_line(lines, "dividend per share", "dividends per share",
                         "proposed dividend per share")
    dps_raw = val(dps_line, ratio=True)
    dps = dps_raw if (dps_raw is None or abs(dps_raw) < 100) else None

    assets = val(find_line(lines, "total assets"))
    equity = val(find_line(lines, "total equity", "shareholders' equity", "shareholders equity"))
    mpesa  = val(find_line(lines, "m-pesa revenue", "mpesa revenue", "mobile money revenue"))
    ocf    = val(find_line(lines, "net cash from operating", "net cash generated from operating",
                           "cash generated from operations"))
    capex  = val(find_line(lines, "capital expenditure", "capex", "purchase of property",
                           "purchase of plant"))

    return {
        "net_interest_income": None,
        "revenue":             revenue,
        "operating_expenses":  opex,
        "profit_before_tax":   pbt,
        "profit_after_tax":    pat,
        "basic_eps":           eps,
        "dividend_per_share":  dps,
        "total_assets":        assets,
        "total_equity":        equity,
        "customer_deposits":   None,
        "loans_and_advances":  None,
        "operating_cash_flow": ocf,
        "capex":               capex,
        "ebitda":              ebitda,
        "mpesa_revenue":       mpesa,
    }


def extract_generic_metrics(lines: List[str]) -> Dict[str, Optional[float]]:
    def val(line: Optional[str], ratio: bool = False) -> Optional[float]:
        return parse_value(line, want_ratio=ratio) if line else None

    return {
        "net_interest_income": None,
        "revenue":             val(find_line(lines, "revenue", "turnover", "total income",
                                             "total operating income")),
        "operating_expenses":  val(find_line(lines, "operating expenses")),
        "profit_before_tax":   val(find_line_excluding(lines, "profit before tax", "deferred")),
        "profit_after_tax":    val(find_line_excluding(lines, "profit after tax", "retained")),
        "basic_eps":           val(find_line(lines, "earnings per share"), ratio=True),
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


def detect_units(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["kes billions", "ksh billions", "in billions", "kshs bn", "kes bn"]):
        return "KES_billions"
    if any(x in t for x in ["kes millions", "ksh millions", "in millions"]):
        return "KES_millions"
    if "thousands" in t:
        return "KES_thousands"
    return "KES_thousands"


def detect_consolidation(text: str) -> str:
    t = text.lower()
    if "group" in t and "company" in t:
        return "group_and_company"
    if "consolidated" in t or "group" in t:
        return "group"
    if "company" in t:
        return "company"
    return "unknown"


# -- PDF scanning --------------------------------------------------------------
def find_all_pdfs() -> List[Path]:
    return sorted(DATA_ROOT.rglob("*.pdf"))


def process_pdf(pdf_path: Path, company: CompanyConfig,
                period: Dict) -> Optional[Dict[str, Any]]:
    try:
        text = extract_text(pdf_path)
    except Exception as e:
        print(f"  ERROR {pdf_path.name}: {e}")
        return None

    lines   = get_lines(text)
    units   = detect_units(text)
    consol  = detect_consolidation(text)
    annual  = is_annual(period, company)
    fy      = fiscal_year_label(period, company)

    if company.company_type == "bank":
        metrics = extract_bank_metrics(lines)
    elif company.company_type == "telco":
        metrics = extract_telco_metrics(lines)
    else:
        metrics = extract_generic_metrics(lines)

    return {
        "company_key":    company.key,
        "company":        company.name,
        "ticker":         company.ticker,
        "sector":         company.sector,
        "period_str":     period["period_str"],
        "period_month":   period["month"],
        "period_year":    period["year"],
        "is_audited":     period["is_audited"],
        "is_annual":      annual,
        "fiscal_year":    fy,
        "units":          units,
        "consolidation":  consol,
        "source_file":    pdf_path.name,
        "source_path":    str(pdf_path),
        **metrics,
    }


# -- data.js rendering ---------------------------------------------------------
def _js_val(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return f"{v:.2f}"
    return str(v)


def build_data_js(by_company: Dict[str, List[Dict]],
                  include_all_periods: bool = False) -> str:
    cfg_by_key = {c.key: c for c in COMPANY_REGISTRY}

    lines = [
        "// Kenya NSE Companies -- Embedded Financial Data",
        "// Auto-generated by backend/populate.py",
        "// Units: Revenue/NII/PAT in KES thousands (except Safaricom = KES millions)",
        "// Source: NSE annual results PDFs",
        "",
        "const NSE_COMPANIES = {",
        "",
    ]

    priority = ["ABSA", "STANCHART", "SAFARICOM", "KCB", "EQUITY", "COOP"]
    all_keys = list(by_company.keys())
    ordered = [k for k in priority if k in all_keys] + \
              sorted([k for k in all_keys if k not in priority])

    for key in ordered:
        records = by_company[key]
        cfg = cfg_by_key.get(key)
        if not cfg or not records:
            continue

        if include_all_periods:
            to_render = sorted(records, key=lambda r: (r["period_year"], r["period_month"]))
        else:
            to_render = sorted(
                [r for r in records if r["is_annual"]],
                key=lambda r: r["fiscal_year"],
            )

        annual_rows = []
        for r in to_render:
            row_items = [
                f"year: {r['fiscal_year']}",
                f"period: \"{r['period_str']}\"",
                f"revenue: {_js_val(r.get('revenue'))}",
                f"pat: {_js_val(r.get('profit_after_tax'))}",
                f"pbt: {_js_val(r.get('profit_before_tax'))}",
                f"nii: {_js_val(r.get('net_interest_income'))}",
                f"eps: {_js_val(r.get('basic_eps'))}",
                f"dps: {_js_val(r.get('dividend_per_share'))}",
                f"totalAssets: {_js_val(r.get('total_assets'))}",
                f"totalEquity: {_js_val(r.get('total_equity'))}",
                f"deposits: {_js_val(r.get('customer_deposits'))}",
                f"loans: {_js_val(r.get('loans_and_advances'))}",
                f"ebitda: {_js_val(r.get('ebitda'))}",
            ]
            annual_rows.append("      { " + ", ".join(row_items) + " },")

        annuals_js = "\n".join(annual_rows) if annual_rows else \
                     "      // No annual data extracted yet"

        lines += [
            f"  {key}: {{",
            f"    name: \"{cfg.name}\",",
            f"    ticker: \"{cfg.ticker}\",",
            f"    exchange: \"NSE\",",
            f"    sector: \"{cfg.sector}\",",
            f"    currency: \"KES\",",
            f"    units: \"{cfg.units}\",",
            f"    latestPrice: {cfg.latest_price},",
            f"    annuals: [",
            annuals_js,
            f"    ]",
            f"  }},",
            "",
        ]

    lines.append("};")
    lines.append("")
    return "\n".join(lines)


# -- Main ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Populate NSE financials from PDFs")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Extract and preview without writing files")
    parser.add_argument("--company",     nargs="*",
                        help="Company key(s) to process. Default: all.")
    parser.add_argument("--all-periods", action="store_true",
                        help="Include interim results in data.js (not just annuals)")
    args = parser.parse_args()

    target_keys = set(args.company) if args.company else None

    pdfs = find_all_pdfs()
    print(f"Found {len(pdfs)} PDFs under {DATA_ROOT}\n")

    results: List[Dict[str, Any]] = []
    skipped_no_company = 0
    skipped_no_period  = 0
    errors = 0

    for i, pdf_path in enumerate(pdfs, 1):
        company = match_company(pdf_path.name)
        if company is None:
            skipped_no_company += 1
            continue

        if target_keys and company.key not in target_keys:
            continue

        period = parse_period(pdf_path.name)
        if period is None:
            skipped_no_period += 1
            print(f"  [skip] No date found: {pdf_path.name}")
            continue

        kind  = "annual" if is_annual(period, company) else "interim"
        label = f"{company.key} | {period['period_str']} | {kind}"
        print(f"[{i}/{len(pdfs)}] {label}")

        result = process_pdf(pdf_path, company, period)
        if result:
            results.append(result)
        else:
            errors += 1

    print(f"\n{'='*60}")
    print(f"Processed:           {len(results)}")
    print(f"Skipped (no match):  {skipped_no_company}")
    print(f"Skipped (no date):   {skipped_no_period}")
    print(f"Errors:              {errors}")
    print(f"{'='*60}\n")

    # Summary per company
    by_company: Dict[str, List[Dict]] = {}
    for r in results:
        by_company.setdefault(r["company_key"], []).append(r)

    for key in sorted(by_company.keys()):
        recs     = by_company[key]
        annuals  = [r for r in recs if r["is_annual"]]
        interims = [r for r in recs if not r["is_annual"]]
        periods  = ", ".join(
            r["period_str"]
            for r in sorted(recs, key=lambda x: (x["period_year"], x["period_month"]))
        )
        print(f"  {key:<15}  {len(annuals):>2} annual,  {len(interims):>2} interim  |  {periods}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Write financials.json
    FINANCIALS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with FINANCIALS_JSON.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(results)} records -> {FINANCIALS_JSON}")

    # Write data.js
    js_content = build_data_js(by_company, include_all_periods=args.all_periods)
    FRONTEND_DATA.parent.mkdir(parents=True, exist_ok=True)
    with FRONTEND_DATA.open("w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"Wrote data.js -> {FRONTEND_DATA}")

    annual_count = sum(1 for r in results if r["is_annual"])
    print(f"\n  {annual_count} annual entries in data.js")
    print(f"  {len(results)} total entries in financials.json")
    print("\nDone.")


if __name__ == "__main__":
    main()
