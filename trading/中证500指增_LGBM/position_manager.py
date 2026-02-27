from utils.中证500指增_LGBM.fees import (
    calc_buy_total_cost,
    calc_sell_net_proceeds,
    exchange_from_symbol,
    calc_incremental_cost_for_additional_volume,
)

class PositionManager:
    def __init__(self, buy_fee_schedule, sell_fee_schedule=None):
        if buy_fee_schedule is None:
            raise ValueError("buy_fee_schedule is required. PositionManager must be initialized with a valid BuyFeeSchedule.")
        self.buy_fee_schedule = buy_fee_schedule
        if sell_fee_schedule is None:
            raise ValueError("sell_fee_schedule is required. PositionManager must be initialized with a valid SellFeeSchedule.")
        self.sell_fee_schedule = sell_fee_schedule


    def _max_volume_for_budget(self, symbol: str, price: float, budget: float) -> int:
        """
        Find max volume (step=100) such that total_cost_with_fees <= budget.
        Requires fee_schedule to be set (enforced in __init__).
        """
        if budget <= 0 or price <= 0:
            return 0

        ex = exchange_from_symbol(symbol)
        if ex is None:
            return 0

        # Upper bound: ignore fees for initial bound
        hi = int((budget / price) // 100) * 100
        if hi <= 0:
            return 0

        # Binary search on 100-share steps
        lo = 0
        while lo < hi:
            mid = ((lo + hi + 100) // 200) * 100  # round up to nearest 100-step mid
            if calc_buy_total_cost(price, mid, ex, self.buy_fee_schedule) <= budget:
                lo = mid
            else:
                hi = mid - 100
        return max(lo, 0)

    def calculate_full_allocation(self, stock_pool, total_budget, market_data_today):
        """
        等权重优先策略：每只股票最多补偿 100 股，最大化利用资金。
        """
        if not stock_pool: return []
        
        # --- 1. 初始等权重分配 ---
        per_stock_budget = total_budget / len(stock_pool)
        results = []
        total_allocated = 0.0  # includes fees

        for symbol in stock_pool:
            price = market_data_today[symbol]['open']
            close = market_data_today[symbol]['close']
            volume = self._max_volume_for_budget(symbol, price, per_stock_budget)
            results.append({
                "symbol": symbol, 
                "open_buy_price": price, 
                "close": close,
                "volume": volume
            })

            ex = exchange_from_symbol(symbol)
            if ex is None:
                raise ValueError(f"无法识别股票 {symbol} 的交易所，symbol 格式应为 'CODE.EXCHANGE' (例如 '600519.SH' 或 '000001.SZ')")
            total_allocated += calc_buy_total_cost(price, volume, ex, self.buy_fee_schedule)

        # --- 2. 补余阶段：轮次补仓，最大化利用资金，保持接近等权重 ---
        remaining_money = total_budget - total_allocated
        
        # 关键：按价格从小到大排序。
        # 理由：低价股补 100 股需要的钱最少，最能"榨干"零头，且对总权重的干扰最小。
        results.sort(key=lambda x: x['open_buy_price'])
        
        # 轮次补仓：每轮给所有能补的股票都补100股，持续直到无法再补
        round_num = 0
        while True:
            round_num += 1
            has_any_added = False  # 标记本轮是否有任何股票被补仓
            
            for item in results:
                # 补 100 股所需的金额（含费用的增量成本）
                ex = exchange_from_symbol(item["symbol"])
                if ex is None:
                    raise ValueError(f"无法识别股票 {item['symbol']} 的交易所，symbol 格式应为 'CODE.EXCHANGE' (例如 '600519.SH' 或 '000001.SZ')")
                
                if item["open_buy_price"] <= 0:
                    continue
                cost_to_add = calc_incremental_cost_for_additional_volume(
                    item["open_buy_price"], item["volume"], 100, ex, self.buy_fee_schedule
                )
                if cost_to_add < 1.0:
                    continue

                if remaining_money >= cost_to_add:
                    item['volume'] += 100
                    remaining_money -= cost_to_add
                    has_any_added = True
                    # 继续检查下一只股票，本轮可以给多只股票补仓
            
            # 如果本轮没有任何股票被补仓，说明剩余资金不够任何股票补100股，退出循环
            if not has_any_added:
                break
        
        if round_num > 1:
            print(f"补余阶段完成，共进行了 {round_num - 1} 轮补仓")

        total_cost_with_fees = total_budget-remaining_money

        print(f"分配完成, 总预算:{total_budget:.2f}, 实际分配:{total_cost_with_fees}, 零头:{remaining_money:.2f}")
        return results

    def calculate_total_cost(self, results):
        """
        Given results (list of dicts with 'symbol', 'open_buy_price', 'volume', ...), return total cost including fees.
        Uses the same fee schedule as allocation.
        """
        total = 0.0
        for item in results:
            ex = exchange_from_symbol(item["symbol"])
            if ex is None:
                raise ValueError(f"无法识别股票 {item['symbol']} 的交易所")
            total += calc_buy_total_cost(item["open_buy_price"], item["volume"], ex, self.buy_fee_schedule)
        return total

    def calculate_net_sell_proceeds(self, positions_to_sell, market_data_today):
        """
        Given positions to sell (list of dicts with 'symbol', 'volume', ...) and market data,
        return total net cash received after deducting sell fees (commission, stamp tax, etc.).
        Mirrors calculate_total_cost but for the sell side.
        """

        total = 0.0
        for pos in positions_to_sell:
            symbol = pos["symbol"]
            close_price = market_data_today[symbol]["close"]
            ex = exchange_from_symbol(symbol)
            if ex is not None:
                total += calc_sell_net_proceeds(
                    close_price, pos["volume"], ex, self.sell_fee_schedule
                )
        return total