import pandas as pd
import os

def get_market_data(stock_list, target_date, base_path):
    """
    target_date: str '20250303'
    returns: dict { '000011.SZ': {'open': 8.3, 'close': 8.35, 'volume': 5000} }
    """
    results = {}
    
    for code in stock_list:
        # Construct path: E:\妖魔鬼怪\...\000011.SZ.parquet
        file_path = os.path.join(base_path, f"{code}.parquet")

        df = pd.read_parquet(file_path)

        # 杜绝数据=0的情况， 因为QMT 无权提供ST 和停牌股票的行情
        if (df == 0).any().any():
            raise ValueError(f"Parquet {code} contains zero values")

        try:
            day_data = df.loc[target_date]
        except KeyError:
            # Use last available close before target_date (pre-suspend)
            idx_str = pd.to_datetime(df.index).strftime("%Y%m%d")
            available = df.index[idx_str <= target_date]
            if len(available) == 0:
                continue
            day_data = df.loc[available[-1]]
            print(f"Stock {code} has no data for date {target_date}. Using last available close from {available[-1]}, price: {day_data['close']}")
            
        results[code] = {
            'open': day_data['open'],
            'close': day_data['close'],
            'high': day_data['high'],
            'low': day_data['low'],
            'volume': day_data['volume'],
            'amount': day_data['amount']
        }

    return results


def get_benchmark_series(dates: list, index_code: str, base_path: str) -> dict:
    """
    Get benchmark (index) close prices for given dates.
    dates: list of date strings 'YYYYMMDD'
    returns: dict {date_str: close}
    """
    file_path = os.path.join(base_path, f"{index_code}.parquet")
    if not os.path.exists(file_path):
        return {}
    df = pd.read_parquet(file_path)
    idx_str = pd.to_datetime(df.index).strftime("%Y%m%d")
    result = {}
    for d in dates:
        try:
            result[d] = float(df.loc[d]["close"])
        except (KeyError, TypeError):
            available = df.index[idx_str <= d]
            if len(available) > 0:
                result[d] = float(df.loc[available[-1]]["close"])
    return result