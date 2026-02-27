"""
Collect daily market data for a single stock via QMT.
Edit STOCK_CODE and date range below, then run.
Same API and save format as daily_data_collection.py.
"""

from xtquant import xtdata
import os

# --- Edit these ---
STOCK_CODE = "300114.SZ"   # e.g. 000001.SZ, 600519.SH
START_DATE = "19900101"
END_DATE = "20991231"
# --- End edit ---

base_data_path = r'E:\妖魔鬼怪\backtest\data\level1\daily\stock'

print(f"Collecting: {STOCK_CODE} ({START_DATE} to {END_DATE})")

xtdata.download_history_data(
    stock_code=STOCK_CODE,
    period='1d',
    start_time=START_DATE,
    end_time=END_DATE
)

res = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=[STOCK_CODE],
    period='1d',
    start_time=START_DATE,
    end_time=END_DATE,
    count=-1,
    dividend_type='none',
    fill_data=False
)

if STOCK_CODE in res and len(res[STOCK_CODE]) > 0:
    df_stock = res[STOCK_CODE]
    save_path = os.path.join(base_data_path, f"{STOCK_CODE}.parquet")
    df_stock.to_parquet(save_path)
    print(f"✅ Saved {len(df_stock)} rows to {save_path}")
else:
    print(f"⚠️ No data for {STOCK_CODE}")
