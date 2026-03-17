#!/usr/bin/env python3
"""
build_price_history.py

Merges Wanjawa Mendeley NSE daily OHLC CSVs (2013-2025) and outputs one JSON per ticker.

Input CSVs expected in data/prices/raw/:
  NSE_data_all_stocks_2013_2020.csv
  NSE_data_all_stocks_2021.csv
  NSE_data_all_stocks_2022.csv
  NSE_data_all_stocks_2023_2024.csv  (or separate _2023.csv / _2024.csv)
  NSE_data_all_stocks_2025.csv

CSV schema (Wanjawa Mendeley datasets):
  Date, Stock Code, Stock Name, 12-month Low, 12-month High, Day Low, Day High,
  Day Final Price, Previous Price, Change Value, Change %, Volume, Adjusted Price

Output: data/prices/{TICKER}.json per ticker
  {
    "ticker": "KCB",
    "name": "KCB Group PLC",
    "sector": "Finance",
    "prices": [
      {"date": "2013-01-02", "close": 27.5, "high": 28.0, "low": 27.0, "volume": 123456, "adj": 27.5},
      ...
    ]
  }

Usage:
  python backend/prices/build_price_history.py
  python backend/prices/build_price_history.py --ticker KCB EQTY SCBK
"""

import csv
import json
import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
RAW_DIR = os.path.join(REPO_ROOT, 'data', 'prices', 'raw')
OUT_DIR = os.path.join(REPO_ROOT, 'data', 'prices')

# CSV files to try (in priority order; skip any that don't exist)
CSV_FILES = [
    'NSE_data_all_stocks_2013_2020.csv',
    'NSE_data_all_stocks_2021.csv',
    'NSE_data_all_stocks_2022.csv',
    'NSE_data_all_stocks_2023_2024.csv',  # combined dataset
    'NSE_data_all_stocks_2023.csv',        # individual year fallback
    'NSE_data_all_stocks_2024.csv',
    'NSE_data_all_stocks_2025.csv',
]

SECTORS_FILES = [
    'NSE_data_stock_market_sectors_2013_2020.csv',
    'NSE_data_stock_market_sectors_2021.csv',
    'NSE_data_stock_market_sectors_2022.csv',
    'NSE_data_stock_market_sectors_2023.csv',
    'NSE_data_stock_market_sectors_2024.csv',
    'NSE_data_stock_market_sectors_2025.csv',
]

# Date format candidates (most-common-first for speed)
DATE_FORMATS = [
    '%d/%m/%Y',
    '%m/%d/%Y',
    '%Y-%m-%d',
    '%d-%m-%Y',
    '%d %b %Y',
    '%B %d, %Y',
    '%Y/%m/%d',
]


def parse_date(date_str):
    """Normalize a date string to ISO YYYY-MM-DD."""
    date_str = date_str.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    # Last resort: fromisoformat
    try:
        return datetime.fromisoformat(date_str).strftime('%Y-%m-%d')
    except Exception:
        pass
    raise ValueError(f"Cannot parse date: {date_str!r}")


def parse_float(val):
    """Parse a float, handling commas/dashes/blanks."""
    if not val or val.strip() in ('-', '', 'N/A', 'n/a', 'NULL', 'null', '#N/A'):
        return None
    val = val.strip().replace(',', '')
    try:
        return float(val)
    except ValueError:
        return None


def parse_int(val):
    """Parse an integer, handling commas/dashes/blanks."""
    if not val or val.strip() in ('-', '', 'N/A', 'n/a', 'NULL', 'null', '#N/A'):
        return None
    val = val.strip().replace(',', '')
    try:
        return int(float(val))
    except ValueError:
        return None


def norm_header(h):
    """Lowercase + strip for header matching."""
    return h.strip().lower()


def find_col(headers_lower, *candidates):
    """Return index of first header matching any candidate (case-insensitive)."""
    for c in candidates:
        c_l = c.lower()
        for i, h in enumerate(headers_lower):
            if h == c_l:
                return i
    return None


def load_sectors():
    """Load sector info from any available sector CSV. Returns {TICKER: sector}."""
    sectors = {}
    for fn in SECTORS_FILES:
        path = os.path.join(RAW_DIR, fn)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                continue
            hl = [norm_header(h) for h in rows[0]]
            sector_col = find_col(hl, 'market sector', 'sector', 'industry')
            ticker_col = find_col(hl, 'stock code', 'ticker', 'symbol', 'code')
            if sector_col is None or ticker_col is None:
                print(f"  Warning: sector CSV {fn} missing expected columns (got: {rows[0][:6]})")
                continue
            for row in rows[1:]:
                if len(row) <= max(sector_col, ticker_col):
                    continue
                ticker = row[ticker_col].strip().upper()
                sector = row[sector_col].strip()
                if ticker and sector:
                    sectors[ticker] = sector
            print(f"  Loaded sectors from {fn}: {len(sectors)} entries so far")
        except Exception as e:
            print(f"  Warning: could not load sectors from {fn}: {e}")
    return sectors


def read_csv_file(path):
    """Try reading a CSV file with utf-8-sig, fallback to latin-1."""
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(path, encoding=enc) as f:
                reader = csv.reader(f)
                return list(reader)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read {path} with any supported encoding")


def process_csv(path, ticker_data):
    """
    Read one CSV file and merge rows into ticker_data.
    ticker_data: {ticker: {date: {close, high, low, volume, adj, name}}}
    Duplicate ticker+date: latest row wins (last occurrence in file).
    """
    rows = read_csv_file(path)
    if not rows:
        return 0

    headers = rows[0]
    hl = [norm_header(h) for h in headers]

    date_col   = find_col(hl, 'date')
    ticker_col = find_col(hl, 'stock code', 'ticker', 'symbol', 'code')
    name_col   = find_col(hl, 'stock name', 'name', 'company name', 'company')
    close_col  = find_col(hl, "day's final price", "day final price", "final price",
                          'close', 'closing price', 'last price', 'price')
    high_col   = find_col(hl, 'day high', "day's high", 'high', 'daily high')
    low_col    = find_col(hl, 'day low', "day's low", 'low', 'daily low')
    volume_col = find_col(hl, 'volume', 'shares traded', 'traded volume')
    adj_col    = find_col(hl, 'adjusted price', 'adj price', 'adj close', 'adjusted close')

    if date_col is None or ticker_col is None or close_col is None:
        print(f"  WARNING: Missing required columns (date/ticker/close) in {os.path.basename(path)}")
        print(f"    Headers found: {headers[:10]}")
        return 0

    count = 0
    for row in rows[1:]:
        # Ensure row is long enough for required columns
        req_max = max(c for c in [date_col, ticker_col, close_col] if c is not None)
        if len(row) <= req_max:
            continue

        try:
            date = parse_date(row[date_col])
        except ValueError:
            continue

        ticker = row[ticker_col].strip().upper()
        if not ticker:
            continue

        close  = parse_float(row[close_col])
        high   = parse_float(row[high_col])   if high_col   is not None and len(row) > high_col   else None
        low    = parse_float(row[low_col])    if low_col    is not None and len(row) > low_col    else None
        volume = parse_int(row[volume_col])   if volume_col is not None and len(row) > volume_col else None
        adj    = parse_float(row[adj_col])    if adj_col    is not None and len(row) > adj_col    else None
        name   = row[name_col].strip()        if name_col   is not None and len(row) > name_col   else ticker

        if adj is None:
            adj = close

        # Latest row wins for same ticker+date
        ticker_data[ticker][date] = {
            'close': close,
            'high':  high,
            'low':   low,
            'volume': volume,
            'adj':   adj,
            'name':  name,
        }
        count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description='Build per-ticker price history JSONs from Mendeley CSVs')
    parser.add_argument('--ticker', nargs='+', help='Only output these tickers (e.g. KCB EQTY)')
    parser.add_argument('--raw-dir', default=RAW_DIR, help=f'Directory with raw CSVs (default: {RAW_DIR})')
    parser.add_argument('--out-dir', default=OUT_DIR, help=f'Output directory (default: {OUT_DIR})')
    args = parser.parse_args()

    raw_dir = args.raw_dir
    out_dir = args.out_dir
    filter_tickers = set(t.upper() for t in args.ticker) if args.ticker else None

    if not os.path.isdir(raw_dir):
        print(f"ERROR: Raw data directory not found: {raw_dir}")
        print("Please download Mendeley CSVs and place them there.")
        print("See backend/prices/download_mendeley.py for instructions.")
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)

    # Load sectors
    print("Loading sector data...")
    sectors = load_sectors()
    print(f"  Total sector entries: {len(sectors)}")

    # Load all CSVs
    ticker_data = defaultdict(dict)  # {ticker: {date: row}}
    total_rows = 0

    print("\nReading price CSVs...")
    for fn in CSV_FILES:
        path = os.path.join(raw_dir, fn)
        if not os.path.exists(path):
            print(f"  Skipping (not found): {fn}")
            continue
        print(f"  Reading: {fn}")
        n = process_csv(path, ticker_data)
        print(f"    → {n} rows loaded")
        total_rows += n

    print(f"\nTotal rows loaded: {total_rows}")
    print(f"Unique tickers found: {len(ticker_data)}")

    if not ticker_data:
        print("\nNo data loaded. Please ensure CSV files are present in:")
        print(f"  {raw_dir}")
        sys.exit(0)

    # Write one JSON per ticker
    written = 0
    skipped = 0
    for ticker in sorted(ticker_data.keys()):
        if filter_tickers and ticker not in filter_tickers:
            skipped += 1
            continue

        rows_by_date = ticker_data[ticker]
        if not rows_by_date:
            continue

        # Get name from the most recent entry
        latest_date = max(rows_by_date.keys())
        name = rows_by_date[latest_date].get('name', ticker)

        # Build sorted price array (skip entries with no close price)
        prices = []
        for date in sorted(rows_by_date.keys()):
            r = rows_by_date[date]
            if r['close'] is None:
                continue
            entry = {'date': date, 'close': r['close']}
            if r.get('high')   is not None: entry['high']   = r['high']
            if r.get('low')    is not None: entry['low']    = r['low']
            if r.get('volume') is not None: entry['volume'] = r['volume']
            if r.get('adj')    is not None: entry['adj']    = r['adj']
            prices.append(entry)

        if not prices:
            continue

        out = {'ticker': ticker, 'name': name, 'prices': prices}
        if ticker in sectors:
            out['sector'] = sectors[ticker]

        out_path = os.path.join(out_dir, f'{ticker}.json')
        with open(out_path, 'w') as f:
            json.dump(out, f, separators=(',', ':'))
        written += 1

    print(f"\nDone: wrote {written} ticker JSON files to {out_dir}/")
    if skipped:
        print(f"  (skipped {skipped} tickers not in --ticker filter)")


if __name__ == '__main__':
    main()
