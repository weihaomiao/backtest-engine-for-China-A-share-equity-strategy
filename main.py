from pathlib import Path
import pandas as pd
import yaml
import json

from backtest.engine import 中证500指增_LGBM_BacktestEngine
from utils.中证500指增_LGBM.fees import BuyFeeSchedule, SellFeeSchedule
from utils.中证500指增_LGBM.中证500指增_LGBM_data_loader import get_benchmark_series
from account.liability import LiabilityFeeSchedule
from analysis.plot import plot_equity_curve
from analysis.diagnostic import print_backtest_diagnostic
from analysis.performance_matrix import save_performance_summary

# load paths
with open('config/paths.yaml', 'r', encoding="utf-8") as f:
    paths = yaml.safe_load(f)

# paths
market_base_path = paths['level1']['daily']['stock']['base_dir']
index_base_path = paths['level1']['daily']['index']['base_dir']
stock_trade_fees_path = paths['config']['stock_trade_fees']
liability_fee_path = paths['config']['liability_fee']
strategy = "中证500指增_LGBM"
p = paths['input'][strategy]
out = paths['output'][strategy]
name = p["name"]
_base = Path(p["base_dir"]) / str(p["year"])
excel_list_path = _base / f"daily_{name}_停牌.xlsx"
plot_save_path = _base / f"{name}_{out['plot_equity']}"
diagnostic_log_path = _base / f"{name}_{out['diagnostic_log']}"
diagnostic_daily_path = _base / f"{name}_{out['diagnostic_daily_csv']}"
performance_summary_path = _base / f"{name}_{out['performance_summary']}"

# import daily data
df = pd.read_excel(excel_list_path)
print(df)

# load trading config
with open(stock_trade_fees_path, "r", encoding="utf-8") as f:
    stock_trade_fees = json.load(f) or {}

# load buy and sell fee schedules
buy_fee_schedule = BuyFeeSchedule.from_config(stock_trade_fees)
sell_fee_schedule = SellFeeSchedule.from_config(stock_trade_fees)

# load liability fee
with open(liability_fee_path, "r", encoding="utf-8") as f:
    liability_fees = json.load(f) or {}

# load liability fee schedule
liability_fee_schedule = LiabilityFeeSchedule.from_config(liability_fees)

# run engine
engine = 中证500指增_LGBM_BacktestEngine(
    df_expanded=df, 
    market_path=market_base_path, 
    initial_cash=10000000,
    buy_fee_schedule=buy_fee_schedule,
    sell_fee_schedule=sell_fee_schedule,
    liability_fee_schedule=liability_fee_schedule
)

engine.run()

# diagnostic
print_backtest_diagnostic(engine, save_path=diagnostic_log_path, daily_csv_path=diagnostic_daily_path)

# benchmark and plot equity curve
benchmark = get_benchmark_series(list(engine.equity_history.keys()), "000905.SH", index_base_path)
plot_equity_curve(
    equity_history=engine.equity_history, 
    benchmark=benchmark,
    title="test",
    save_path=plot_save_path
)

# performance analysis
save_performance_summary(
    equity_history=engine.equity_history,
    save_path=performance_summary_path,
    benchmark=benchmark,
)


