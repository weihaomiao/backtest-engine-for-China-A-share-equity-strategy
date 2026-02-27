from dataclasses import dataclass
from typing import Dict, Optional

@dataclass(frozen=True)
class LiabilityFeeSchedule:
    """
    Liability fee schedule.
    """
    management_fee_rate: float
    custodian_fee_rate: float
    administration_services_fee_rate: float
    tax_fee_rate: float

    @staticmethod
    def from_config(cfg: Dict) -> "LiabilityFeeSchedule":
        fees = (cfg or {}).get("fees")
        operational = (fees or {}).get("operational")
        management_fee_rate = float(operational.get("management_fee_rate"))
        custodian_fee_rate = float(operational.get("custodian_fee_rate"))
        administration_services_fee_rate = float(operational.get("administration_services_fee_rate"))
        tax_fee_rate = float(operational.get("tax_fee_rate"))
        return LiabilityFeeSchedule(
            management_fee_rate=management_fee_rate,
            custodian_fee_rate=custodian_fee_rate,
            administration_services_fee_rate=administration_services_fee_rate,
            tax_fee_rate=tax_fee_rate,
        )

class LiabilityManager:
    def __init__(self, liability_fee_schedule):
        self.liability_fee_schedule = liability_fee_schedule

    def calculate_total_liabilities(self, yesterday_nav, stocks_to_sell, last_trade_date, sell_prices):
        """
        Calculates the daily 'leak' (Operating Fees) based on yesterday's NAV.
        """
        # 1. Extract rates from your schedule
        mgmt_rate = self.liability_fee_schedule.management_fee_rate
        cust_rate = self.liability_fee_schedule.custodian_fee_rate
        admin_rate = self.liability_fee_schedule.administration_services_fee_rate
        tax_rate = self.liability_fee_schedule.tax_fee_rate

        # 2. Sum the total daily operating fee rate
        total_daily_rate = mgmt_rate + cust_rate + admin_rate

        # 3. Apply logic: Fees accrue every day; add capital gains tax on sell days (incl. single-day case)
        if last_trade_date == 1:
            daily_fee = yesterday_nav * total_daily_rate
            daily_fee += self.calculate_tax_liabilities(stocks_to_sell, sell_prices, tax_rate)
        else:
            daily_fee = yesterday_nav * total_daily_rate

        return daily_fee


    def calculate_tax_liabilities(self, stocks_to_sell, prices, tax_rate):
        """
        Calculates the total tax liabilities based on the stock list and market data.
        """
        total_tax_liabilities = 0
        for stock in stocks_to_sell:
            if stock['open_buy_price'] < prices.get(stock['symbol']):
                tax_liabilities = stock['volume'] * (prices.get(stock['symbol']) - stock['open_buy_price']) * tax_rate
                total_tax_liabilities += tax_liabilities
        return total_tax_liabilities