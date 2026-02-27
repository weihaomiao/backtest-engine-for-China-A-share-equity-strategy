from xtquant import xtdata
import pandas as pd

# # 1. 下载涨跌停价数据（VIP权限）
# xtdata.download_history_data(
#     stock_code='300114.SZ', 
#     period='1d',  # 改为日线
#     start_time='20200303',  # 去掉时分秒，只需日期
#     end_time='20200310',    # 只需日期
# )

# # 2. 获取历史涨跌停价
# data = xtdata.get_market_data_ex(
#     field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
#     stock_list=['000011.SZ'],
#     period='1d',  # 改为日线
#     start_time='20200303',  # 改为YYYYMMDD格式
#     end_time='20200310',    # 改为YYYYMMDD格式
#     count=-1,
#     dividend_type='none',
#     fill_data=True
# )

# print(data)

import pandas as pd

df = pd.read_parquet(r"E:\妖魔鬼怪\backtest\data\level1\daily\stock\300064.SZ.parquet")

print(df.index.dtype)
print(df)

# 1. Get a full structural summary
df.info()

print(type(df.index[0]))

start_date = df.index[0]
print(start_date)




