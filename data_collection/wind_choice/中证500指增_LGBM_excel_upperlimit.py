"""
Faster version of 中证500指增_LGBM_excel_upperlimit.py.
Same logic and identical result; speeds up by batching all range writes
instead of per-cell COM calls in for loops.
"""
import pandas as pd
import time
import yaml
from pathlib import Path
from datetime import datetime
import xlwings as xw

# Load paths from config (project root = backtest folder)
_project_root = Path(__file__).resolve().parents[2]
with open(_project_root / "config" / "paths.yaml", "r", encoding="utf-8") as f:
    _paths = yaml.safe_load(f)
_strategy = "中证500指增_LGBM"
_p = _paths["input"][_strategy]
_name = _p["name"]
output_dir = _project_root / _p["base_dir"] / str(_p["year"])
input_path = output_dir / f"daily_{_name}.xlsx"
saving_path = output_dir / f"daily_{_name}_停牌.xlsx"

def _flatten_values(values):
    """Flatten nested list from 2D Excel range to 1D."""
    if values is None:
        return []
    out = []
    for v in values:
        if isinstance(v, (list, tuple)):
            out.extend(_flatten_values(v))
        else:
            out.append(v)
    return out


def _is_pending_status(v):
    """True if cell shows Refreshing, Fetching, Fatching, fatch, etc."""
    s = str(v).lower() if v is not None else ""
    return any(x in s for x in ("refreshing", "fetching", "fatching", "fatch"))


def wait_until_not_refreshing(sheet, cell_range, max_wait_time=300, check_interval=2):
    """
    等待直到公式计算完成，避免假显示“计算完成”
    """
    start_time = time.time()
    while True:
        values = sheet.range(cell_range).value
        flat = _flatten_values(values)
        if not any(_is_pending_status(v) for v in flat):
            elapsed_time = time.time() - start_time
            print(f"计算完成，耗时 {elapsed_time:.2f} 秒")
            break
        if time.time() - start_time > max_wait_time:
            print(f"Warning: Max wait time of {max_wait_time} seconds exceeded.")
            break
        time.sleep(check_interval)


# --- Same paths and setup as original ---
app = xw.App(visible=True)
wb = app.books.open(str(input_path))
sheet = wb.sheets[0]

df = sheet.range("A1").expand('table').options(pd.DataFrame, index=False, header=True).value
total_rows = len(df)
existing_columns = sheet.range("A1").expand('right').value
existing_column_count = len(existing_columns)

COL_K = 11
new_columns = ["UpperLimit", "LowerLimit", "停牌起始日期", "停牌结束日期", "停牌结束最后交易日"]
sheet.range(1, COL_K).value = new_columns

first_trading_excel_rows = set(i + 2 for i in df.index[df["first_trading_day"] == 1])
last_trading_excel_rows = set(i + 2 for i in df.index[df["last_trading_day"] == 1])
first_or_last_rows = first_trading_excel_rows | last_trading_excel_rows

UpperLimit_formula = "=@s_dq_maxup(B{row},H{row})"
LowerLimit_formula = "=@s_dq_maxdown(B{row},H{row})"
suspension_start_formula = "=@EM_S_DQ_TRADESUSPENDTIME(B{row},H{row})"
suspension_end_formula = "=@EM_S_DQ_TRADERESUMPTIONTIME(B{row},H{row})"

# --- Batched: build full K:N block then one formula write ---
rows_formulas = []
for row in range(2, total_rows + 2):
    k = UpperLimit_formula.format(row=row) if row in first_trading_excel_rows else None
    l_ = LowerLimit_formula.format(row=row) if row in last_trading_excel_rows else None
    m = suspension_start_formula.format(row=row) if row in first_or_last_rows else None
    n = suspension_end_formula.format(row=row) if row in first_or_last_rows else None
    rows_formulas.append([k, l_, m, n])
sheet.range(f"K2:N{total_rows + 1}").formula = rows_formulas

# --- Batched: set entire O column to None in one write ---
sheet.range(f"O2:O{total_rows + 1}").value = [[None] for _ in range(total_rows)]

wait_until_not_refreshing(sheet, f"K2:O{total_rows + 1}")

# Paste values (same as original)
sheet_range = sheet.used_range
values = sheet_range.value
sheet_range.value = values

# --- Compute O column in memory, then one batched write ---
df_after = sheet.range("A1").expand('table').options(pd.DataFrame, index=False, header=True).value
today = datetime.now().date()
col_susp_end_last = COL_K + 4

df_after["daily_date"] = pd.to_datetime(df_after["daily_date"], errors="coerce").dt.date
df_after["week_end"] = pd.to_datetime(df_after["week_end"], errors="coerce").dt.date


def _is_valid_susp_val(v):
    if v is None or pd.isna(v):
        return False
    if v == "" or v == 0:
        return False
    return True


o_column_values = [None] * len(df_after)
for idx in range(len(df_after)):
    row = df_after.iloc[idx]
    start_val = row.get("停牌起始日期")
    end_val = row.get("停牌结束日期")
    if not _is_valid_susp_val(start_val) or not _is_valid_susp_val(end_val):
        continue
    end_date = pd.to_datetime(end_val, errors="coerce").date()
    if pd.isna(end_date):
        continue
    matching_row = df_after.loc[df_after["daily_date"] == end_date]
    if end_date > today:
        result = today
    else:
        result = matching_row.iloc[0]["week_end"]
        if result is None:
            continue
    o_column_values[idx] = result

sheet.range(f"O2:O{total_rows + 1}").value = [[v] for v in o_column_values]

wb.save(str(saving_path))
app.quit()
