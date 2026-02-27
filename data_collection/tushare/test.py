
import tushare as ts
import pandas as pd

token = ""
pro = ts.pro_api(token)

#获取浦发银行60000.SH的历史分钟数据
# df = pro.stk_mins(ts_code='300750.SZ', freq='1min', start_date='2026-01-30 09:00:00', end_date='2026-01-30 19:00:00')
df = pro.daily(ts_code='000018.SZ', start_date='20181203', end_date='20200106')
print(df)