"""
Test market value calculation: sum(volume * close) for each position.
Matches the logic in backtest/engine.py for market_value_today.
"""
import pytest


def market_value_from_results(results: list[dict], prices: dict[str, float]) -> float:
    """Sum of (volume * close) for each item in results. Uses close from prices."""
    return sum(
        item["volume"] * prices.get(item["symbol"], 0.0)
        for item in results
    )


def test_market_value_sum_sample_data():
    """Verify market value sum with sample results and prices (from engine run)."""
    results = [
        {"symbol": "000415.SZ", "price": 4.21, "volume": 19700},
        {"symbol": "600390.SH", "price": 5.98, "volume": 13900},
        {"symbol": "600517.SH", "price": 6.33, "volume": 13000},
        {"symbol": "000060.SZ", "price": 6.62, "volume": 12500},
        {"symbol": "002044.SZ", "price": 6.74, "volume": 12200},
        {"symbol": "000958.SZ", "price": 6.8, "volume": 12100},
        {"symbol": "000683.SZ", "price": 7.57, "volume": 10900},
        {"symbol": "002131.SZ", "price": 8.21, "volume": 10100},
        {"symbol": "600497.SH", "price": 8.70, "volume": 9500},
        {"symbol": "000039.SZ", "price": 9.73, "volume": 8500},
        {"symbol": "002065.SZ", "price": 9.99, "volume": 8300},
        {"symbol": "000050.SZ", "price": 10.0, "volume": 8300},
        {"symbol": "000009.SZ", "price": 10.29, "volume": 8000},
        {"symbol": "002195.SZ", "price": 10.80, "volume": 7700},
        {"symbol": "002312.SZ", "price": 11.33, "volume": 7300},
        {"symbol": "002064.SZ", "price": 11.91, "volume": 6900},
        {"symbol": "000528.SZ", "price": 11.96, "volume": 6900},
        {"symbol": "002153.SZ", "price": 12.22, "volume": 6800},
        {"symbol": "002152.SZ", "price": 13.75, "volume": 6000},
        {"symbol": "002203.SZ", "price": 14.5, "volume": 5700},
        {"symbol": "603766.SH", "price": 15.0, "volume": 5500},
        {"symbol": "002007.SZ", "price": 15.65, "volume": 5300},
        {"symbol": "002414.SZ", "price": 16.37, "volume": 5100},
        {"symbol": "000739.SZ", "price": 16.43, "volume": 5100},
        {"symbol": "002085.SZ", "price": 16.68, "volume": 5000},
        {"symbol": "000951.SZ", "price": 16.95, "volume": 4900},
        {"symbol": "000830.SZ", "price": 16.99, "volume": 4900},
        {"symbol": "002532.SZ", "price": 18.28, "volume": 4400},
        {"symbol": "000519.SZ", "price": 19.72, "volume": 4100},
        {"symbol": "000559.SZ", "price": 19.85, "volume": 4100},
        {"symbol": "000623.SZ", "price": 20.25, "volume": 4000},
        {"symbol": "600765.SH", "price": 20.44, "volume": 4000},
        {"symbol": "001696.SZ", "price": 22.88, "volume": 3500},
        {"symbol": "000738.SZ", "price": 23.5, "volume": 3400},
        {"symbol": "300207.SZ", "price": 25.3, "volume": 3200},
        {"symbol": "000062.SZ", "price": 25.3, "volume": 3200},
        {"symbol": "000021.SZ", "price": 26.90, "volume": 3000},
        {"symbol": "000400.SZ", "price": 28.0, "volume": 2900},
        {"symbol": "002130.SZ", "price": 28.06, "volume": 2900},
        {"symbol": "300390.SZ", "price": 53.0, "volume": 1500},
    ]
    prices = {
        "000050.SZ": 10.33,
        "002130.SZ": 28.26,
        "002152.SZ": 14.02,
        "000830.SZ": 16.72,
        "603766.SH": 14.83,
        "000415.SZ": 4.09,
        "600517.SH": 6.36,
        "002532.SZ": 17.84,
        "002065.SZ": 10.36,
        "000958.SZ": 6.72,
        "002195.SZ": 11.39,
        "000559.SZ": 20.45,
        "000009.SZ": 10.26,
        "600497.SH": 8.57,
        "002203.SZ": 14.41,
        "000528.SZ": 11.94,
        "000951.SZ": 16.92,
        "600765.SH": 20.92,
        "002414.SZ": 16.79,
        "300207.SZ": 25.43,
        "000400.SZ": 27.74,
        "002007.SZ": 15.58,
        "002064.SZ": 11.79,
        "000519.SZ": 19.89,
        "002153.SZ": 12.92,
        "000039.SZ": 9.63,
        "000060.SZ": 6.5,
        "600390.SH": 6.04,
        "002312.SZ": 11.47,
        "000739.SZ": 16.25,
        "000738.SZ": 24.87,
        "000683.SZ": 7.37,
        "002044.SZ": 6.74,
        "002085.SZ": 16.99,
        "000021.SZ": 27.50,
        "001696.SZ": 23.25,
        "000062.SZ": 25.95,
        "002131.SZ": 8.21,
        "300390.SZ": 52.90,
        "000623.SZ": 20.33,
    }

    mv = market_value_from_results(results, prices)
    expected = 3_307_532.0
    assert abs(mv - expected) < 1.0, f"market_value_today: got {mv}, expected ~{expected}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
