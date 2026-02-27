from dataclasses import dataclass
from typing import Dict, Optional

# Python 3.7 compatibility: use str instead of Literal
# Exchange should be "SH" or "SZ"
Exchange = str


@dataclass(frozen=True)
class BuyFeeSchedule:
    """
    Buy-side fee schedule (用户需求版本). 买入无印花税.
    - SH: commission + csrc + handling + transfer
    - SZ: commission + csrc + handling
    - Minimum applies to (commission + csrc + handling): min_fee
    Notes:
    - Rates are expressed as decimal fractions (e.g. 0.00025 for 0.025%).
    """

    commission_rate: float
    csrc_fee_rate: float
    handling_fee_rate: float
    transfer_fee_rate_sh: float
    min_fee: float

    @staticmethod
    def from_config(cfg: Dict) -> "BuyFeeSchedule":
        fees = (cfg or {}).get("fees")
        buy = (fees or {}).get("buy")
        commission = float(buy.get("commission_rate"))
        csrc = float(buy.get("csrc_fee_rate"))
        handling = float(buy.get("handling_fee_rate"))
        transfer_sh = float(buy.get("transfer_fee_rate_sh"))
        min_fee = float(buy.get("min_fee"))
        return BuyFeeSchedule(
            commission_rate=commission,
            csrc_fee_rate=csrc,
            handling_fee_rate=handling,
            transfer_fee_rate_sh=transfer_sh,
            min_fee=min_fee,
        )


@dataclass(frozen=True)
class SellFeeSchedule:
    """
    Sell-side fee schedule. 卖出含印花税.
    - SH: commission + csrc + handling + transfer + stamp_tax
    - SZ: commission + csrc + handling + stamp_tax
    - Minimum applies to (commission + csrc + handling): min_fee
    Notes:
    - Rates are expressed as decimal fractions (e.g. 0.00025 for 0.025%).
    """

    commission_rate: float
    csrc_fee_rate: float
    handling_fee_rate: float
    stamp_tax_rate: float
    transfer_fee_rate_sh: float
    min_fee: float

    @staticmethod
    def from_config(cfg: Dict) -> "SellFeeSchedule":
        fees = (cfg or {}).get("fees")
        sell = (fees or {}).get("sell")
        commission = float(sell.get("commission_rate"))
        csrc = float(sell.get("csrc_fee_rate"))
        handling = float(sell.get("handling_fee_rate"))
        stamp = float(sell.get("stamp_tax_rate"))
        transfer_sh = float(sell.get("transfer_fee_rate_sh"))
        min_fee = float(sell.get("min_fee"))
        return SellFeeSchedule(
            commission_rate=commission,
            csrc_fee_rate=csrc,
            handling_fee_rate=handling,
            stamp_tax_rate=stamp,
            transfer_fee_rate_sh=transfer_sh,
            min_fee=min_fee,
        )


def exchange_from_symbol(full_symbol: str) -> Optional[Exchange]:
    if not full_symbol or "." not in full_symbol:
        return None
    suffix = full_symbol.rsplit(".", 1)[-1].upper()
    if suffix in ("SH", "SSE"):
        return "SH"
    if suffix in ("SZ", "SZSE"):
        return "SZ"
    return None


def calc_buy_fees(amount: float, exchange: Exchange, schedule: BuyFeeSchedule) -> float:
    """
    Calculate buy-side fees for a given notional amount.
    """
    if amount <= 0:
        return 0.0

    base_fee = amount * (schedule.commission_rate + schedule.csrc_fee_rate + schedule.handling_fee_rate)
    base_fee = max(base_fee, schedule.min_fee)

    transfer = amount * schedule.transfer_fee_rate_sh if exchange == "SH" else 0.0

    return base_fee + transfer


def calc_buy_total_cost(open_buy_price: float, volume: int, exchange: Exchange, schedule: BuyFeeSchedule) -> float:
    """
    Total cash required for a buy order = notional + fees.
    """
    if open_buy_price <= 0 or volume <= 0:
        return 0.0
    amount = float(open_buy_price) * int(volume)
    return amount + calc_buy_fees(amount, exchange, schedule)


def calc_sell_fees(amount: float, exchange: Exchange, schedule: SellFeeSchedule) -> float:
    """
    Calculate sell-side fees for a given notional amount (includes 印花税).
    """
    if amount <= 0:
        return 0.0

    base_fee = amount * (schedule.commission_rate + schedule.csrc_fee_rate + schedule.handling_fee_rate)
    base_fee = max(base_fee, schedule.min_fee)

    transfer = amount * schedule.transfer_fee_rate_sh if exchange == "SH" else 0.0
    stamp = amount * schedule.stamp_tax_rate

    return base_fee + transfer + stamp


def calc_sell_net_proceeds(price: float, volume: int, exchange: Exchange, schedule: SellFeeSchedule) -> float:
    """
    Net cash received from a sell order = notional - fees.
    """
    if price <= 0 or volume <= 0:
        return 0.0
    amount = float(price) * int(volume)
    return amount - calc_sell_fees(amount, exchange, schedule)


def calc_incremental_cost_for_additional_volume(
    price: float, current_volume: int, add_volume: int, exchange: Exchange, schedule: BuyFeeSchedule
) -> float:
    """
    Incremental cash required to increase an existing planned buy order by add_volume shares.
    This respects the min-fee rule by comparing total costs before/after.
    """
    if add_volume <= 0:
        return 0.0
    before = calc_buy_total_cost(price, current_volume, exchange, schedule)
    after = calc_buy_total_cost(price, current_volume + add_volume, exchange, schedule)
    return max(after - before, 0.0)

