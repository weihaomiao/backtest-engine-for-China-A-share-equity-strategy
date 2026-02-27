# --- inside backtest/engine.py ---
import pandas as pd
from datetime import date
from account.account import Account 
from utils.中证500指增_LGBM.中证500指增_LGBM_data_loader import get_market_data
from trading.中证500指增_LGBM.position_manager import PositionManager
from account.liability import LiabilityManager

class 中证500指增_LGBM_BacktestEngine:
    def __init__(self, df_expanded, market_path, initial_cash, buy_fee_schedule, sell_fee_schedule, liability_fee_schedule):
        # 1. Initialize the Ledger
        self.account = Account(initial_cash) 
        self.position_manager = PositionManager(buy_fee_schedule, sell_fee_schedule)
        self.liability_manager = LiabilityManager(liability_fee_schedule)
        self.df = df_expanded.sort_values('daily_date')
        self.equity_history = {}
        self.market_path = market_path
        self._diag = {
            "total_buy_cost": 0.0,
            "total_sell_proceeds": 0.0,
            "total_liabilities": 0.0,
            "buy_days": 0,
            "sell_days": 0,
            "excluded_suspended": 0,
            "excluded_upper_limit": 0,
            "stuck_limit_down": [],
            "stuck_suspension": [],
        }
        self._daily_records = []  # per-day diagnostic

    def run(self):
        # Record initial NAV (before first trading day) as starting point
        today = date.today()
        # today = date(2026, 2, 23)  # 测试用固定日；正式用 date.today()
        self.df = self.df[
            pd.to_datetime(self.df["daily_date"]).dt.date <= today
        ].copy() # only run until today

        first_date = self.df["daily_date"].min()
        start_date = (pd.to_datetime(first_date) - pd.offsets.BDay(1)).strftime("%Y%m%d")
        self.equity_history[start_date] = self.account.NAV

        for current_date, daily_snapshot in self.df.groupby('daily_date'):
            stocks_to_sell = []
            stocks_to_buy = []
            cash_start = self.account.cash
            buy_cost_today = 0.0
            sell_proceeds_today = 0.0
            liabilities_paid_today = 0.0

            # 1. Update Market Prices (Mark-to-Market)
            # Union of (Stocks the model wants) AND (Stocks we currently hold)
            stocks_in_position = [p['symbol'] for p in self.account.positions]
            stocks_excel_list = daily_snapshot['Name'].tolist()
            all_relevant_stocks = list(set(stocks_in_position + stocks_excel_list))


            first_trade_date = daily_snapshot['first_trading_day'].iloc[0]
            last_trade_date = daily_snapshot['last_trading_day'].iloc[0]

            # 2. 行情数据获取
            current_date_str = current_date.strftime('%Y%m%d')     
            market_data_today = get_market_data(
                stock_list=all_relevant_stocks, 
                target_date=current_date_str, 
                base_path=self.market_path) # a helper function to get the market data

            #### BUY DAY ####
            if first_trade_date == 1 and last_trade_date == 0: 
                # 3. Exclude symbols: suspended, no/invalid data (price<=0), upper limit
                symbols_to_exclude = set()
                for _, row in daily_snapshot.iterrows():
                    symbol = row["Name"]
                    is_suspended = False
                    for col in ("停牌起始日期", "停牌结束日期"):
                        if row[col] != 0:
                            symbols_to_exclude.add(symbol)
                            is_suspended = True
                            self._diag["excluded_suspended"] += 1
                            break
                    if is_suspended:
                        continue
                    if symbol not in market_data_today:
                        raise ValueError(f"Stock {symbol} has no market data for date {current_date_str}, plz check API data collection")

                    m = market_data_today[symbol]
                    open_price = m["open"]
                    if open_price >= row["UpperLimit"]:
                        symbols_to_exclude.add(symbol)
                        self._diag["excluded_upper_limit"] += 1
                stocks_to_buy = [s for s in stocks_excel_list if s not in symbols_to_exclude]

                # 3. Use Position Manager to calculate total buy volumes
                results = self.position_manager.calculate_full_allocation(
                    stock_pool=stocks_to_buy, 
                    total_budget=self.account.cash,
                    market_data_today=market_data_today) # choosen stocks and their volumes

                total_cost_with_fees = self.position_manager.calculate_total_cost(results)
                buy_cost_today = total_cost_with_fees
                self._diag["total_buy_cost"] += total_cost_with_fees
                self._diag["buy_days"] += 1

                # 4. Update Account's positions
                # CRITICAL: Merge stuck positions (from previous sell) with new buys.
                # Previously we REPLACED positions, discarding stuck stocks and losing their value.
                stuck_from_previous = self.account.positions
                if stuck_from_previous:
                    results = results + stuck_from_previous
                self.account.update_positions(results)

                # 5. Update Account's cash
                cash_after_buy = self.account.cash - total_cost_with_fees # cash after monday trade
                self.account.update_cash(cash_after_buy)
            
            #### HOLD DAY ####
            elif first_trade_date == 0 and last_trade_date == 0:
                pass

            #### SELL DAY ####
            elif last_trade_date == 1:
                # 1. Identify which items in the list are sellable
                stocks_to_keep = [] # These stay in your portfolio (Stuck)

                for pos in self.account.positions:
                    symbol = pos['symbol']
                    row = daily_snapshot[daily_snapshot['Name'] == symbol] # might be empty if pre stuck stocks is not selected this week
                    m_data = market_data_today.get(symbol)

                    # A. Check if it was already stuck or is new trouble
                    is_stuck = False
                    if not m_data:
                        raise ValueError(f"Stock {symbol} has no market data for date {current_date_str}, plz check API data collection")

                    # Check Previous Suspension State
                    if pos.get('stuck_cause') == 'SUSPENSION':
                        end_date = pos.get('suspension_end_date')
                        if end_date is None:
                            is_stuck = True
                        elif current_date_str < end_date:
                            is_stuck = True

                    # 假设上期跌停股票在下一卖出日期不会stuck

                    # Check Today's Market Constraints (if not already stuck by date)
                    if not is_stuck and not row.empty:
                        # 1. Check for New/Continued Suspension in Excel
                        for col in ("停牌起始日期", "停牌结束日期"):
                            if pd.notna(row[col].iloc[0]) and row[col].iloc[0] != 0:
                                pos['stuck_cause'] = 'SUSPENSION'
                                val = row['停牌结束最后交易日'].iloc[0]
                                if pd.notna(val):
                                    if hasattr(val, 'strftime'):
                                        pos['suspension_end_date'] = val.strftime("%Y%m%d")
                                    else:
                                        pos['suspension_end_date'] = str(int(val))
                                else:
                                    pos['suspension_end_date'] = None

                                is_stuck = True
                                break
                        
                        # 2. Check for Limit Down (Price Floor)
                        if not is_stuck and m_data['close'] <= row['LowerLimit'].iloc[0]:
                            pos['stuck_cause'] = 'LIMIT_DOWN'
                            is_stuck = True

                    # B. Execute Decision
                    if is_stuck:
                        stocks_to_keep.append(pos)
                        cause = pos.get("stuck_cause", "UNKNOWN")
                        if cause == "LIMIT_DOWN":
                            self._diag["stuck_limit_down"].append((current_date_str, symbol))
                        elif cause == "SUSPENSION":
                            self._diag["stuck_suspension"].append((current_date_str, symbol))
                        else:
                            raise ValueError(f"Unknown stuck cause: {cause}")

                results = stocks_to_keep

                # 2 Sell and update Account's cash and positions
                stuck_symbols = {pos['symbol'] for pos in stocks_to_keep}
                stocks_to_sell = [pos for pos in self.account.positions if pos['symbol'] not in stuck_symbols]
                self.account.update_positions(results) # update positions after sell

                net_sell_proceeds = self.position_manager.calculate_net_sell_proceeds(stocks_to_sell, market_data_today)
                sell_proceeds_today = net_sell_proceeds
                self._diag["total_sell_proceeds"] += net_sell_proceeds
                self._diag["sell_days"] += 1
                cash_after_sell = self.account.cash + net_sell_proceeds
                self.account.update_cash(cash_after_sell)

            ### OTHER CASES JUST RAISE ERROR ###
            else:
                raise ValueError(f"Invalid trade date: {first_trade_date} and {last_trade_date}")

 

            # 6. Update Account's market value
            # market value calculation: sum(volume * close) for each position.
            prices = {symbol: data['close'] for symbol, data in market_data_today.items()}
            market_value_today = sum(
                item['volume'] * prices.get(item['symbol'])
                for item in self.account.positions
            )
            self.account.update_market_value(market_value_today)

            # 7. Update account's liabilities after trade
            liabilities_today = self.liability_manager.calculate_total_liabilities(
                yesterday_nav=self.account.NAV, 
                stocks_to_sell=stocks_to_sell, 
                last_trade_date=last_trade_date,
                sell_prices=prices)

            self.account.update_liabilities(liabilities_today)
            self.account.update_accumulated_liabilities(liabilities_today)
            self._diag["total_liabilities"] += liabilities_today

            if last_trade_date == 1:  # selling day (normal or single-day)
                cumulative_liabilities = self.account.accumulated_liabilities
                liabilities_paid_today = cumulative_liabilities
                self.account.reset_accumulated_liabilities()  # liabilities reset on selling day

                # actual cash deduction on selling day
                self.account.cash -= cumulative_liabilities

                # NAV calculation
                NAV_today = self.account.cash + self.account.market_value

            else:
                # 8. Update account's NAV
                NAV_today = self.account.cash + self.account.market_value - self.account.accumulated_liabilities

            self.account.update_NAV(NAV_today)

            # record performance
            self.equity_history[current_date_str] = self.account.NAV

            # Per-day record for diagnostic
            day_type = "buy" if (first_trade_date == 1 and last_trade_date == 0) else ("sell" if last_trade_date == 1 else "hold")
            self._daily_records.append({
                "date": current_date_str,
                "day_type": day_type,
                "cash_start": cash_start,
                "buy_cost": buy_cost_today,
                "sell_proceeds": sell_proceeds_today,
                "liabilities_today": liabilities_today,
                "accumulated_liabilities": self.account.accumulated_liabilities,
                "liabilities_paid": liabilities_paid_today,
                "cash_end": self.account.cash,
                "market_value": market_value_today,
                "nav": self.account.NAV,
                "positions": len(self.account.positions),
            })

        return self.equity_history




    
