import pandas as pd
import os
import time
from datetime import datetime
import xlwings as xw

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
    
    :param sheet: 需要检查的 Excel sheet
    :param cell_range: 需要检查的单元格范围
    :param max_wait_time: 最大等待时间，单位：秒
    :param check_interval: 检查间隔时间，单位：秒
    """
    start_time = time.time()
    while True:
        values = sheet.range(cell_range).value
        flat = _flatten_values(values)
        if not any(_is_pending_status(v) for v in flat):
            end_time = time.time()  # 记录结束时间
            elapsed_time = end_time - start_time  # 计算消耗的时间
            print(f"计算完成，耗时 {elapsed_time:.2f} 秒")
            break
        
        # 检查超时
        if time.time() - start_time > max_wait_time:
            print(f"Warning: Max wait time of {max_wait_time} seconds exceeded.")
            break
        time.sleep(check_interval)  # 每隔一定时间检查一次
        

# 启动 Excel 应用实例（设置 visible=True 可看到 Excel 窗口）
app = xw.App(visible=True)

# 打开已存在的工作簿
output_dir = r"E:\妖魔鬼怪\backtest\data\portfolio\中证500指增_LGBM\2025" # 改
input_path = os.path.join(output_dir, "daily_全A_10个行业.xlsx") # 改
wb = app.books.open(input_path)

saving_path = os.path.join(output_dir, "daily_全A_10个行业_停牌.xlsx") # 改

# 获取工作簿中的第一个工作表
sheet = wb.sheets[0]

# 将 Excel 数据读取到 DataFrame
df = sheet.range("A1").expand('table').options(pd.DataFrame, index=False, header=True).value

# 获取 DataFrame 的总行数
total_rows = len(df)

# 获取现有数据的总列数
existing_columns = sheet.range("A1").expand('right').value  # 获取第一行的所有列名
existing_column_count = len(existing_columns)

# 新增列从 K 列开始 (K=11): UpperLimit, LowerLimit, 停牌起始日期, 停牌结束日期, 停牌结束最后交易日
COL_K = 11
new_columns = ["UpperLimit", "LowerLimit", "停牌起始日期", "停牌结束日期", "停牌结束最后交易日"]
sheet.range(1, COL_K).value = new_columns

first_trading_excel_rows = set(i + 2 for i in df.index[df["first_trading_day"] == 1])
last_trading_excel_rows = set(i + 2 for i in df.index[df["last_trading_day"] == 1])
first_or_last_rows = first_trading_excel_rows | last_trading_excel_rows

# K: UpperLimit (仅 first_trading_day=1), L: LowerLimit (仅 last_trading_day=1)
# M,N: 停牌起始日期, 停牌结束日期 (first_trading_day=1 OR last_trading_day=1)
# O: 停牌结束最后交易日 - 在公式计算并粘贴值后由 Python 计算
UpperLimit_formula = "=@s_dq_maxup(B{row},H{row})"
LowerLimit_formula = "=@s_dq_maxdown(B{row},H{row})"
suspension_start_formula = "=@EM_S_DQ_TRADESUSPENDTIME(B{row},H{row})"
suspension_end_formula = "=@EM_S_DQ_TRADERESUMPTIONTIME(B{row},H{row})"

for row in range(2, total_rows + 2):
    if row in first_trading_excel_rows:
        sheet.range(row, COL_K).formula = UpperLimit_formula.format(row=row)
    else:
        sheet.range(row, COL_K).value = None
    if row in last_trading_excel_rows:
        sheet.range(row, COL_K + 1).formula = LowerLimit_formula.format(row=row)
    else:
        sheet.range(row, COL_K + 1).value = None
    if row in first_or_last_rows:
        sheet.range(row, COL_K + 2).formula = suspension_start_formula.format(row=row)
        sheet.range(row, COL_K + 3).formula = suspension_end_formula.format(row=row)
    else:
        sheet.range(row, COL_K + 2).value = None
        sheet.range(row, COL_K + 3).value = None

# O 列暂不写公式，等粘贴值后再用 Python 计算
for row in range(2, total_rows + 2):
    sheet.range(row, COL_K + 4).value = None

wait_until_not_refreshing(sheet, f"K2:O{total_rows + 1}")

# Now the calculation is complete, paste values instead of formulas
sheet_range = sheet.used_range  # Get the used range
values = sheet_range.value  # Get values from the range

# Paste the values back into the sheet, replacing the formulas
sheet_range.value = values

# 计算 停牌结束最后交易日 (O列): 仅对 first_or_last 行且 停牌起始/结束日期 均存在且非 0 的行
df_after = sheet.range("A1").expand('table').options(pd.DataFrame, index=False, header=True).value
today = datetime.now().date()
col_susp_end_last = COL_K + 4  # O

df_after["daily_date"] = pd.to_datetime(df_after["daily_date"], errors="coerce").dt.date
df_after["week_end"] = pd.to_datetime(df_after["week_end"], errors="coerce").dt.date

def _is_valid_susp_val(v):
    """Non-empty and non-zero."""
    if v is None or pd.isna(v):
        return False
    if v == "" or v == 0:
        return False
    return True

for idx in range(len(df_after)):
    excel_row = idx + 2
    row = df_after.iloc[idx]
    start_val = row.get("停牌起始日期")
    end_val = row.get("停牌结束日期")
    # Pass only if both have value and neither is 0
    if not _is_valid_susp_val(start_val) or not _is_valid_susp_val(end_val):
        continue

    end_date = pd.to_datetime(end_val, errors="coerce").date()
    matching_row = df_after.loc[df_after["daily_date"] == end_date]
 
    if pd.isna(end_date):
        continue

    if end_date > today:
        result = today
    else:
        result = matching_row.iloc[0]["week_end"]
        if result is None:
            continue

    sheet.range(excel_row, col_susp_end_last).value = result

# 保存修改后的数据到另一个 Excel 文件
wb.save(saving_path)  # 保存到新文件

# Quit the Excel application
app.quit()




