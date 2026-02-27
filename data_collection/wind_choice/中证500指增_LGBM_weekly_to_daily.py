import pandas as pd
import os
import yaml
from pathlib import Path

# Load paths from config (project root = backtest folder)
_project_root = Path(__file__).resolve().parents[2]
with open(_project_root / "config" / "paths.yaml", "r", encoding="utf-8") as f:
    _paths = yaml.safe_load(f)
_strategy = "中证500指增_LGBM"
_p = _paths["input"][_strategy]
_name = _p["name"]
_sdir = (_project_root / _p["strategy_data_dir"]).resolve()
_year = _p["year"]

EXCEL_PATH = _sdir / "result" / str(_year) / f"{_name}.xlsx"
DATE_WEEKLY_PATH = _sdir / _p["date_weekly_file"]
DATE_DAILY_PATH = _sdir / _p["date_daily_file"]
output_dir = _project_root / _p["base_dir"] / str(_year)
output_path_full = output_dir / f"daily_{_name}.xlsx"

df = pd.read_excel(EXCEL_PATH)
date_weekly = pd.read_excel(DATE_WEEKLY_PATH)
date_daily = pd.read_excel(DATE_DAILY_PATH)
date_daily = date_daily.rename(columns={'daily': 'Date'})

print(date_weekly)
print(date_daily)
print(df)


df = pd.merge_asof(
    df, 
    date_weekly.rename(columns={'Date': 'week_end'}), 
    left_on='Date', 
    right_on='week_end', 
    direction='forward',
    allow_exact_matches=False 
)

print(df)


# 2. Define a helper function to get the trading days in the range
def get_daily_dates(row):
    start = row['Date']
    end = row['week_end']
    
    # Filter date_daily for: start < Date <= end
    mask = (date_daily['Date'] > start) & (date_daily['Date'] <= end)
    return date_daily.loc[mask, 'Date'].tolist()

# 3. Create the list of dates for each row
df['daily_date'] = df.apply(get_daily_dates, axis=1)

# 4. Explode the list into individual rows
# This duplicates all stock info (Name, Predicted, etc.) for each date in the list
df_expanded = df.explode('daily_date')

# 5. Clean up: reset index and remove the helper column if not needed
df_expanded = df_expanded.reset_index(drop=True)

# Add first_trading_day: 1 if row has min daily_date in its Date+Name group, else 0
idx_first_day = df_expanded.groupby(['Date', 'Name'])['daily_date'].idxmin()
df_expanded['first_trading_day'] = 0
df_expanded.loc[idx_first_day, 'first_trading_day'] = 1

# Add last_trading_day: 1 if row has max daily_date in its Date+Name group, else 0
idx_last_day = df_expanded.groupby(['Date', 'Name'])['daily_date'].idxmax()
df_expanded['last_trading_day'] = 0
df_expanded.loc[idx_last_day, 'last_trading_day'] = 1

# Save to Excel (includes first_trading_day, last_trading_day)
output_path_full.parent.mkdir(parents=True, exist_ok=True)
df_expanded.to_excel(output_path_full, index=False)
print(f"Full expanded data saved to: {output_path_full}")
print(df_expanded)








