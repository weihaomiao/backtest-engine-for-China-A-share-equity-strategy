from xtquant import xtdata
import pandas as pd
import yaml
from pathlib import Path

# Load paths from config (project root = backtest folder)
_project_root = Path(__file__).resolve().parents[2]
with open(_project_root / "config" / "paths.yaml", "r", encoding="utf-8") as f:
    _paths = yaml.safe_load(f)
_stock = _paths["level1"]["daily"]["stock"]
file_path = _project_root / _stock["stockpool"]
base_data_path = _project_root / _stock["base_dir"]

# --- 2. Data Preparation ---
df = pd.read_excel(file_path)

# 删除第一列（Unnamed: 0）
if 'Unnamed: 0' in df.columns:
    df = df.drop(columns=['Unnamed: 0'])

# 删除前两行（索引0和1的行）
df_cleaned = df.iloc[2:].reset_index(drop=True)

print(df_cleaned)

df_long = df_cleaned.melt(var_name='date', value_name='ts_code').dropna()
df_long['date'] = pd.to_datetime(df_long['date'], format='%Y%m%d')
df_long = df_long.sort_values(['ts_code', 'date'])

print(df_long)

# Group by unique ts_code (one task per stock, full date range)
task_groups = df_long.groupby('ts_code').agg(date_min=('date', 'min'), date_max=('date', 'max')).reset_index()

print(task_groups.iloc[0])
print(task_groups.iloc[-1])


# 主循环：下载并保存数据
for idx, row in task_groups.iterrows():
    ts_code = row['ts_code']
    start_date = row['date_min'].strftime('%Y%m%d')
    end_date = row['date_max'].strftime('%Y%m%d')
    
    print(f"Processing {idx+1}/{len(task_groups)}: {ts_code} ({start_date} to {end_date})")
    
    # 下载数据
    xtdata.download_history_data(
        stock_code=ts_code,
        period='1d',
        start_time=start_date,
        end_time=end_date
    )
    
    # 获取数据
    res = xtdata.get_market_data_ex(
        field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
        stock_list=[ts_code],
        period='1d',
        start_time=start_date,
        end_time=end_date,
        count=-1,
        dividend_type='none',
        fill_data=False
    )
    
    # 提取并保存
    if ts_code in res and len(res[ts_code]) > 0:
        df_stock = res[ts_code]
        save_path = base_data_path / f"{ts_code}.parquet"
        df_stock.to_parquet(save_path)
        print(f"  ✅ Saved {len(df_stock)} rows to {save_path}")
        # print(df_stock)
    else:
        print(f"  ⚠️ No data for {ts_code}")
            
print("All data downloaded and saved!")