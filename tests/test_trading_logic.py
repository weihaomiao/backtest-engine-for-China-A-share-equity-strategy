"""
Test that allocation results match fee logic: sum of per-position costs equals
total_cost_with_fees and total_budget - sum_cost == remaining_money.

Run from project root: python -m pytest tests/test_trading_logic.py -v
Or: python tests/test_trading_logic.py
"""
import json
import sys
from pathlib import Path

# Allow imports from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.中证500指增_LGBM.fees import (
    BuyFeeSchedule,
    calc_buy_total_cost,
    exchange_from_symbol,
)


# Snapshot from engine run: 20260112, budget 3287211.99
CURRENT_DATE_STR = "20260112"
TOTAL_BUDGET = 3287211.99
EXPECTED_TOTAL_COST = 3286988.3912585005
EXPECTED_REMAINING = 223.59874149960524

RESULTS = [
    {"symbol": "000415.SZ", "open_buy_price": 4.21, "volume": 19700},
    {"symbol": "600390.SH", "open_buy_price": 5.9799999999999995, "volume": 13900},
    {"symbol": "600517.SH", "open_buy_price": 6.33, "volume": 13000},
    {"symbol": "000060.SZ", "open_buy_price": 6.62, "volume": 12500},
    {"symbol": "002044.SZ", "open_buy_price": 6.74, "volume": 12200},
    {"symbol": "000958.SZ", "open_buy_price": 6.8, "volume": 12100},
    {"symbol": "000683.SZ", "open_buy_price": 7.57, "volume": 10900},
    {"symbol": "002131.SZ", "open_buy_price": 8.21, "volume": 10100},
    {"symbol": "600497.SH", "open_buy_price": 8.700000000000001, "volume": 9500},
    {"symbol": "000039.SZ", "open_buy_price": 9.729999999999999, "volume": 8500},
    {"symbol": "002065.SZ", "open_buy_price": 9.99, "volume": 8300},
    {"symbol": "000050.SZ", "open_buy_price": 10.0, "volume": 8300},
    {"symbol": "000009.SZ", "open_buy_price": 10.290000000000001, "volume": 8000},
    {"symbol": "002195.SZ", "open_buy_price": 10.799999999999999, "volume": 7700},
    {"symbol": "002312.SZ", "open_buy_price": 11.33, "volume": 7300},
    {"symbol": "002064.SZ", "open_buy_price": 11.91, "volume": 6900},
    {"symbol": "000528.SZ", "open_buy_price": 11.96, "volume": 6900},
    {"symbol": "002153.SZ", "open_buy_price": 12.22, "volume": 6800},
    {"symbol": "002152.SZ", "open_buy_price": 13.75, "volume": 6000},
    {"symbol": "002203.SZ", "open_buy_price": 14.5, "volume": 5700},
    {"symbol": "603766.SH", "open_buy_price": 15.0, "volume": 5500},
    {"symbol": "002007.SZ", "open_buy_price": 15.65, "volume": 5300},
    {"symbol": "002414.SZ", "open_buy_price": 16.37, "volume": 5100},
    {"symbol": "000739.SZ", "open_buy_price": 16.43, "volume": 5100},
    {"symbol": "002085.SZ", "open_buy_price": 16.68, "volume": 5000},
    {"symbol": "000951.SZ", "open_buy_price": 16.950000000000003, "volume": 4900},
    {"symbol": "000830.SZ", "open_buy_price": 16.99, "volume": 4900},
    {"symbol": "002532.SZ", "open_buy_price": 18.28, "volume": 4400},
    {"symbol": "000519.SZ", "open_buy_price": 19.720000000000002, "volume": 4100},
    {"symbol": "000559.SZ", "open_buy_price": 19.85, "volume": 4100},
    {"symbol": "000623.SZ", "open_buy_price": 20.25, "volume": 4000},
    {"symbol": "600765.SH", "open_buy_price": 20.44, "volume": 4000},
    {"symbol": "001696.SZ", "open_buy_price": 22.880000000000003, "volume": 3500},
    {"symbol": "000738.SZ", "open_buy_price": 23.5, "volume": 3400},
    {"symbol": "000062.SZ", "open_buy_price": 25.3, "volume": 3200},
    {"symbol": "300207.SZ", "open_buy_price": 25.3, "volume": 3200},
    {"symbol": "000021.SZ", "open_buy_price": 26.900000000000002, "volume": 3000},
    {"symbol": "000400.SZ", "open_buy_price": 28.0, "volume": 2900},
    {"symbol": "002130.SZ", "open_buy_price": 28.06, "volume": 2900},
    {"symbol": "300390.SZ", "open_buy_price": 53.0, "volume": 1500},
]

# Float tolerance for comparisons
TOL = 0.01


def load_fee_schedule():
    config_path = PROJECT_ROOT / "config" / "stock_trade_fees.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return BuyFeeSchedule.from_config(cfg)


def test_allocation_total_cost_matches_fee_logic():
    """Sum of per-position buy costs must equal total_cost_with_fees."""
    schedule = load_fee_schedule()
    total_cost = 0.0
    total_notional = 0.0

    for item in RESULTS:
        symbol = item["symbol"]
        price = item["open_buy_price"]
        volume = item["volume"]
        ex = exchange_from_symbol(symbol)
        assert ex is not None, f"Unknown exchange for {symbol}"
        cost = calc_buy_total_cost(price, volume, ex, schedule)
        total_cost += cost
        total_notional += price * volume

    assert abs(total_cost - EXPECTED_TOTAL_COST) < TOL, (
        f"Total cost mismatch: computed {total_cost}, expected {EXPECTED_TOTAL_COST}"
    )
    remaining = TOTAL_BUDGET - total_cost
    assert abs(remaining - EXPECTED_REMAINING) < TOL, (
        f"Remaining mismatch: computed {remaining}, expected {EXPECTED_REMAINING}"
    )


def test_budget_conservation():
    """total_cost_with_fees + remaining_money must equal total_budget."""
    assert abs(EXPECTED_TOTAL_COST + EXPECTED_REMAINING - TOTAL_BUDGET) < TOL


def test_volumes_multiple_of_100():
    """All volumes must be multiples of 100 (lot size)."""
    for item in RESULTS:
        assert item["volume"] % 100 == 0, (
            f"{item['symbol']}: volume {item['volume']} is not a multiple of 100"
        )


def test_result_count():
    """Expect 40 positions (one per stock in pool)."""
    assert len(RESULTS) == 40


def run_verbose():
    """Run checks and print summary (when executed as script)."""
    schedule = load_fee_schedule()
    total_cost = 0.0
    total_notional = 0.0

    for item in RESULTS:
        symbol, price, volume = item["symbol"], item["open_buy_price"], item["volume"]
        ex = exchange_from_symbol(symbol)
        cost = calc_buy_total_cost(price, volume, ex, schedule)
        total_cost += cost
        total_notional += price * volume

    remaining = TOTAL_BUDGET - total_cost
    print(f"current_date_str: {CURRENT_DATE_STR}")
    print(f"total_budget: {TOTAL_BUDGET}")
    print(f"sum notional (price*volume): {total_notional:.4f}")
    print(f"sum total_cost_with_fees:    {total_cost:.4f}")
    print(f"expected total_cost:        {EXPECTED_TOTAL_COST}")
    print(f"remaining (budget - cost):   {remaining:.4f}")
    print(f"expected remaining:         {EXPECTED_REMAINING}")
    print(f"total_cost match: {abs(total_cost - EXPECTED_TOTAL_COST) < TOL}")
    print(f"remaining match:  {abs(remaining - EXPECTED_REMAINING) < TOL}")
    print(f"budget conserved: {abs(total_cost + remaining - TOTAL_BUDGET) < TOL}")


if __name__ == "__main__":
    run_verbose()
    # Run pytest-style assertions
    test_volumes_multiple_of_100()
    test_result_count()
    test_budget_conservation()
    test_allocation_total_cost_matches_fee_logic()
    print("All checks passed.")
