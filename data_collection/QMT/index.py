from xtquant import xtdata
import pandas as pd
import os

# 保存到指数文件夹
index_base_path = r'E:\妖魔鬼怪\backtest\data\level1\daily\index'

# 使用尽可能早的日期
index_code = '000905.SH'

# 沪深300是2005年4月8日发布的
# 但可以尝试更早的日期，QMT会返回它能给的最早数据
xtdata.download_history_data(
    stock_code=index_code,
    period='1d',
    start_time='19900101',  # 尝试非常早的日期
    end_time='20991231'     # 尝试非常晚的日期
)

res = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume', 'amount'],
    stock_list=[index_code],
    period='1d',
    start_time='19900101',  # 同样范围
    end_time='20991231',
    count=-1
)

if index_code in res:
    df = res[index_code]
    print(f"实际获取到 {len(df)} 个交易日")
    print(f"最早日期: {df.index[0]}")
    print(f"最晚日期: {df.index[-1]}")
    # 这就是QMT能提供的"全部历史"
    print(df)

# 保存指数数据（和股票一样的保存逻辑）
save_path = os.path.join(index_base_path, f"{index_code}.parquet")
df.to_parquet(save_path)
print(f"✅ 指数 {index_code} 已保存到 {save_path}")