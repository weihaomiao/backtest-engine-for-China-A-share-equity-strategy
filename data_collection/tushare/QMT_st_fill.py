
"""
Scan parquet files, find those with any 0, refetch from Tushare API and overwrite.
"""

import pandas as pd
from pathlib import Path
import tushare as ts
import time

STOCK_PATH = r"E:\妖魔鬼怪\backtest\data\level1\daily\stock"
token = ""
pro = ts.pro_api(token)


def main():
    path = Path(STOCK_PATH)
    if not path.exists():
        print(f"Path does not exist: {path}")
        return

    parquet_files = list(path.glob("*.parquet"))
    print(f"Scanning {len(parquet_files)} parquet files...")

    for f in parquet_files:
        df = pd.read_parquet(f)
        if not (df == 0).any().any():
            continue

        stock_name = f.stem
        start_date = df.index[0]
        end_date = df.index[-1]

        time.sleep(1.2)
        new_df = pro.daily(ts_code=stock_name, start_date=start_date, end_date=end_date)
        new_df = new_df.rename(columns={"vol": "volume"})[
            ["open", "high", "low", "close", "volume", "amount", "trade_date"]
        ]
        new_df.set_index("trade_date", inplace=True)
        new_df.sort_index(ascending=True, inplace=True)
        new_df["volume"] = new_df["volume"].astype("int64")
        new_df[["open", "high", "low", "close", "amount"]] = new_df[
            ["open", "high", "low", "close", "amount"]
        ].astype(float)
        new_df.index.name = None

        new_df.to_parquet(f)
        print(f"Replaced {stock_name}")

    print("Done.")


if __name__ == "__main__":
    main()

