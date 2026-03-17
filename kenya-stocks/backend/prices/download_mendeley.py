"""
download_mendeley.py

Stub for future automated Mendeley dataset downloads.

For now, manually download the following datasets and place CSVs in data/prices/raw/:

  2013-2020: https://data.mendeley.com/datasets/73rb78pmzw/2
  2021:      https://data.mendeley.com/datasets/97hkwn5y3x/3
  2022:      https://data.mendeley.com/datasets/jmcdmnyh2s/2
  2023-2024: https://data.mendeley.com/datasets/ss5pfw8xnk/3
  2025:      https://data.mendeley.com/datasets/2b63rx67xt/1

Expected CSV filenames in data/prices/raw/:
  NSE_data_all_stocks_2013_2020.csv
  NSE_data_all_stocks_2021.csv
  NSE_data_all_stocks_2022.csv
  NSE_data_all_stocks_2023_2024.csv  (combined, or separate 2023/2024 files)
  NSE_data_all_stocks_2025.csv

Optional sector CSVs (same directory):
  NSE_data_stock_market_sectors_YYYY.csv

After placing files, run:
  python backend/prices/build_price_history.py
"""

if __name__ == '__main__':
    print("HTTP download not implemented.")
    print("Please download CSVs manually from Mendeley and place them in data/prices/raw/")
    print("See module docstring for dataset URLs and expected filenames.")
