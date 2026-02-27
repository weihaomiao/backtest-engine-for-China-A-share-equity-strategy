import tushare as ts
import pandas as pd
import time
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 1. API Setup ---
pro = ts.pro_api(token='不用管这里')
pro._DataApi__token = '3222828411494429852'
pro._DataApi__http_url = 'http://stk_mins.xiximiao.com/dataapi'

# --- 2. Data Preparation ---
file_path = r'E:\妖魔鬼怪\backtest\data\level1\minute\stock\daily_stockpool.parquet'
base_data_path = r'E:\妖魔鬼怪\backtest\data\level1\minute\stock'

df = pd.read_parquet(file_path)

# 删除第一列（Unnamed: 0）
if 'Unnamed: 0' in df.columns:
    df = df.drop(columns=['Unnamed: 0'])

# 删除前两行（索引0和1的行）
df_cleaned = df.iloc[2:].reset_index(drop=True)

print(df_cleaned)

df_long = df_cleaned.melt(var_name='date', value_name='ts_code').dropna()
df_long['date'] = pd.to_datetime(df_long['date'], format='%Y%m%d')
df_long = df_long.sort_values(['ts_code', 'date'])

# 1. Add Month-Year identity to your long-format stock pool
df_long['month'] = df_long['date'].dt.strftime('%Y%m')

print(df_long)

task_groups = df_long.groupby(['ts_code', 'month'])['date'].agg(['min', 'max']).reset_index()

# Filter out existing stock folders
if os.path.exists(base_data_path):
    existing_stocks = {d for d in os.listdir(base_data_path) if os.path.isdir(os.path.join(base_data_path, d))}
    task_groups = task_groups[~task_groups['ts_code'].isin(existing_stocks)]
    print(f"Skipping {len(existing_stocks)} existing stocks. Remaining tasks: {len(task_groups)}")

# --- 3. Define the Thread Task Function ---
def download_stock_month(task):
    """Function to be executed by each thread"""
    stock = task.ts_code
    month = task.month
    year = month[:4]
    start_dt = task.min.strftime('%Y-%m-%d 09:00:00')
    end_dt = task.max.strftime('%Y-%m-%d 15:05:00')
    
    # Setup directory (exist_ok is vital for multithreading)
    stock_year_dir = os.path.join(base_data_path, stock, year)
    os.makedirs(stock_year_dir, exist_ok=True)
        
    save_path = os.path.join(stock_year_dir, f"{stock}_{month}.parquet")
    if os.path.exists(save_path):
        return

    success = False
    while not success:
        try:
            # Monthly Batch Request
            df_min = pro.stk_mins(
                ts_code=stock,
                freq='1min',
                start_date=start_dt,
                end_date=end_dt
            )
            
            if not df_min.empty:
                # Chronological Sort & Clean Index
                df_min = df_min.sort_values('trade_time', ascending=True).reset_index(drop=True)
                df_min.to_parquet(save_path)
                print(f"✅ Success: {stock} | Month: {month} | Rows: {len(df_min)}")
            
            success = True # Exit the while loop for this task

        except Exception as e:
            err_msg = str(e)
            # Both "请求过于频繁" and "每分钟最多访问该接口500次" → wait & retry same task
            if "请求过于频繁" in err_msg or "抱歉，您每分钟最多访问该接口500次，建议稍晚点再试" in err_msg:
                # "500次" = limit, not wait time. Use 60s for per-minute limit; parse wait only from 请求过于频繁.
                if "抱歉，您每分钟最多访问该接口500次" in err_msg:
                    sleep_sec = 60
                else:
                    wait_nums = re.findall(r'\d+', err_msg)
                    sleep_sec = int(wait_nums[0]) if wait_nums else 60
                print(f"🛑 Rate Limit hit for {stock} {month}. Waiting {sleep_sec}s...")
                time.sleep(sleep_sec + 1)
            else:
                # Fail-fast on timeouts / unknown errors.
                print(f"❌ Fatal Error at {stock} {month}: {err_msg}")
                raise

# --- 4. Launch Thread Pool ---
# Start with max_workers=10. If the server is 100-concurrency stable, you can increase this.
MAX_THREADS = 5

print(f"🚀 Starting Multi-threaded Engine with {MAX_THREADS} threads...")
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = [executor.submit(download_stock_month, task) for task in task_groups.itertuples()]
    try:
        for fut in as_completed(futures):
            # Propagate exceptions to the main thread immediately.
            fut.result()
    except Exception:
        # Cancel all other tasks and exit program by re-raising.
        for fut in futures:
            fut.cancel()
        raise

print("🏁 All tasks processed.")
