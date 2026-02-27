"""
Backtest diagnostic: print and optionally save a summary report.
"""

import pandas as pd
from pathlib import Path

def get_daily_df(engine):
    """Return per-day diagnostic as DataFrame."""
    if not getattr(engine, "_daily_records", None):
        return None
    return pd.DataFrame(engine._daily_records)


def print_backtest_diagnostic(engine, save_path=None, daily_csv_path=None):
    """
    Print diagnostic summary. If save_path is provided, also write to file.

    Args:
        engine: 中证500指增_LGBM_BacktestEngine after run()
        save_path: optional path to save summary log (e.g. Path or str)
        daily_csv_path: optional path to save per-day DataFrame as CSV
    """
    if not engine.equity_history:
        msg = "No equity history."
        print(msg)
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            Path(save_path).write_text(msg, encoding="utf-8")
        return

    hist = pd.Series(engine.equity_history).sort_index()
    first_nav = hist.iloc[0]
    last_nav = hist.iloc[-1]
    ret_pct = (last_nav / first_nav - 1) * 100
    d = engine._diag

    lines = [
        "",
        "=" * 50,
        "BACKTEST DIAGNOSTIC",
        "=" * 50,
        f"Initial NAV:     {first_nav:>15,.2f}",
        f"Final NAV:       {last_nav:>15,.2f}",
        f"Return:          {ret_pct:>14.2f}%",
        "",
        "--- Cash flow ---",
        f"Total buy cost:      {d['total_buy_cost']:>15,.2f}  (over {d['buy_days']} buy days)",
        f"Total sell proceeds: {d['total_sell_proceeds']:>15,.2f}  (over {d['sell_days']} sell days)",
        f"Net trading:         {d['total_sell_proceeds'] - d['total_buy_cost']:>15,.2f}",
        f"Total liabilities:   {d['total_liabilities']:>15,.2f}  (fees + tax)",
        "",
        "--- Exclusions (buy-side) ---",
        f"Suspended:      {d['excluded_suspended']:>6}",
        f"Upper limit:    {d['excluded_upper_limit']:>6}",
        "",
        "--- Stuck (sell-side) ---",
        f"Limit down:   {len(d['stuck_limit_down'])} occurrences",
    ]
    for dt, sym in d["stuck_limit_down"][:5]:
        lines.append(f"  {dt} {sym}")
    if len(d["stuck_limit_down"]) > 5:
        lines.append(f"  ... and {len(d['stuck_limit_down']) - 5} more")
    lines.extend([
        f"Suspension:   {len(d['stuck_suspension'])} occurrences",
    ])
    for dt, sym in d["stuck_suspension"][:5]:
        lines.append(f"  {dt} {sym}")
    if len(d["stuck_suspension"]) > 5:
        lines.append(f"  ... and {len(d['stuck_suspension']) - 5} more")
    lines.extend([
        "",
        "--- Final state ---",
        f"Cash:          {engine.account.cash:>15,.2f}",
        f"Market value:  {engine.account.market_value:>15,.2f}",
        f"Positions:     {len(engine.account.positions)}",
    ])
    if engine.account.positions:
        for p in engine.account.positions[:5]:
            lines.append(f"  {p['symbol']}: {p['volume']} @ {p.get('open_buy_price', '?')}")
        if len(engine.account.positions) > 5:
            lines.append(f"  ... and {len(engine.account.positions) - 5} more")
    lines.append("=" * 50)

    text = "\n".join(lines)
    print(text)

    # Per-day DataFrame
    daily_df = get_daily_df(engine)
    if daily_df is not None and len(daily_df) > 0:
        print("\n--- Per-day record (first 10, last 10) ---")
        pd.set_option("display.max_columns", None)
        pd.set_option("display.width", None)
        print(daily_df.head(10).to_string())
        print("...")
        print(daily_df.tail(10).to_string())
        if daily_csv_path:
            daily_csv_path = Path(daily_csv_path)
            daily_csv_path.parent.mkdir(parents=True, exist_ok=True)
            daily_df.to_csv(daily_csv_path, index=False, encoding="utf-8-sig")
            print(f"\nDaily record saved to {daily_csv_path}")

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(text, encoding="utf-8")
        print(f"Diagnostic log saved to {save_path}")
