"""
Backtest performance metrics (pro-style).
Computes annualized return, Sharpe, max drawdown, Calmar, Sortino, etc.,
optionally vs benchmark (alpha, beta, tracking error, information ratio).
Saves to .txt by category; optionally prints.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Annualization: assume daily-ish series; 252 trading days per year
TRADING_DAYS_PER_YEAR = 252


def _to_returns_series(equity_history: Dict[str, float]) -> pd.Series:
    """Convert equity_history (date_str -> NAV) to sorted series, then compute period returns."""
    s = pd.Series(equity_history).sort_index()
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    return s.pct_change().dropna()


def _annualized_return(s: pd.Series) -> float:
    """CAGR from first to last value."""
    if len(s) < 2 or s.iloc[0] <= 0:
        return np.nan
    n_years = (s.index[-1] - s.index[0]).days / 365.0
    if n_years <= 0:
        return np.nan
    total_return = s.iloc[-1] / s.iloc[0] - 1.0
    return (1.0 + total_return) ** (1.0 / n_years) - 1.0


def _annualized_volatility(returns: pd.Series) -> float:
    if returns.empty or len(returns) < 2:
        return np.nan
    return returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def _sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe: (mean_excess_return) / (annualized_vol)."""
    if returns.empty:
        return np.nan
    excess = returns - (risk_free_rate / TRADING_DAYS_PER_YEAR)
    vol = _annualized_volatility(returns)
    if vol <= 0:
        return np.nan
    return excess.mean() * TRADING_DAYS_PER_YEAR / vol


def _sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Downside deviation (only negative returns)."""
    if returns.empty:
        return np.nan
    excess = returns - (risk_free_rate / TRADING_DAYS_PER_YEAR)
    downside = returns[returns < 0]
    if downside.empty:
        return np.nan
    downside_vol = np.sqrt((downside ** 2).mean()) * np.sqrt(TRADING_DAYS_PER_YEAR)
    if downside_vol <= 0:
        return np.nan
    return excess.mean() * TRADING_DAYS_PER_YEAR / downside_vol


def _max_drawdown(s: pd.Series) -> tuple:
    """Return (max_dd, max_dd_pct). Max DD in absolute and in % of peak."""
    if len(s) < 2:
        return np.nan, np.nan
    cummax = s.cummax()
    dd = s - cummax
    dd_pct = (s - cummax) / cummax.replace(0, np.nan)
    return dd.min(), dd_pct.min()


def _max_drawdown_duration(s: pd.Series) -> int:
    """Longest number of periods (e.g. days) underwater from a peak."""
    if len(s) < 2:
        return 0
    cummax = s.cummax()
    underwater = s < cummax
    # count consecutive True
    grp = (~underwater).cumsum()
    dur = underwater.groupby(grp).sum()
    return int(dur.max()) if len(dur) else 0


def _calmar_ratio(equity_series: pd.Series, ann_return: float) -> float:
    """Annualized return / abs(max drawdown %)."""
    _, dd_pct = _max_drawdown(equity_series)
    if dd_pct is np.nan or dd_pct >= 0:
        return np.nan
    return ann_return / abs(dd_pct)


def _win_rate(returns: pd.Series) -> float:
    """Fraction of periods with positive return."""
    if returns.empty:
        return np.nan
    return (returns > 0).mean()


def _alpha_beta_tracking(ret_strategy: pd.Series, ret_bench: pd.Series) -> tuple:
    """Align by index, then alpha (annualized), beta, tracking error (annualized)."""
    common = ret_strategy.index.intersection(ret_bench.index)
    if len(common) < 2:
        return np.nan, np.nan, np.nan
    r_s = ret_strategy.loc[common].dropna()
    r_b = ret_bench.loc[common].reindex(r_s.index).ffill().bfill()
    valid = r_b.notna()
    r_s, r_b = r_s[valid], r_b[valid]
    if len(r_s) < 2:
        return np.nan, np.nan, np.nan
    cov = np.cov(r_s, r_b)
    beta = cov[0, 1] / cov[1, 1] if cov[1, 1] != 0 else np.nan
    alpha_series = r_s - beta * r_b
    alpha_ann = alpha_series.mean() * TRADING_DAYS_PER_YEAR
    te = alpha_series.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    return alpha_ann, beta, te


def _information_ratio(ret_strategy: pd.Series, ret_bench: pd.Series) -> float:
    """Annualized active return / tracking error."""
    alpha_ann, _, te = _alpha_beta_tracking(ret_strategy, ret_bench)
    if te is np.nan or te <= 0:
        return np.nan
    return alpha_ann / te


def compute_performance_metrics(
    equity_history: Dict[str, float],
    benchmark: Optional[Dict[str, float]] = None,
    risk_free_rate: float = 0.0,
) -> Dict[str, object]:
    """
    Compute strategy metrics and optionally benchmark-relative metrics.
    Returns a dict: metric_key -> value (float, int, or str).
    """
    if not equity_history or len(equity_history) < 2:
        return {}

    s = pd.Series(equity_history).sort_index()
    s.index = pd.to_datetime(s.index, format="%Y%m%d")
    returns = _to_returns_series(equity_history)

    ann_ret = _annualized_return(s)
    vol = _annualized_volatility(returns)
    total_ret = s.iloc[-1] / s.iloc[0] - 1.0
    dd_abs, dd_pct = _max_drawdown(s)

    out = {
        "start_date": s.index[0].strftime("%Y-%m-%d"),
        "end_date": s.index[-1].strftime("%Y-%m-%d"),
        "n_observations": len(s),
        "total_return": total_ret,
        "annualized_return": ann_ret,
        "annualized_volatility": vol,
        "sharpe_ratio": _sharpe_ratio(returns, risk_free_rate),
        "sortino_ratio": _sortino_ratio(returns, risk_free_rate),
        "max_drawdown": dd_abs,
        "max_drawdown_pct": dd_pct,
        "max_drawdown_duration_periods": _max_drawdown_duration(s),
        "calmar_ratio": _calmar_ratio(s, ann_ret),
        "win_rate": _win_rate(returns),
    }

    if benchmark and len(benchmark) >= 2:
        b = pd.Series(benchmark).sort_index()
        b.index = pd.to_datetime(b.index, format="%Y%m%d")
        ret_bench = b.pct_change().dropna()
        alpha_ann, beta, te = _alpha_beta_tracking(returns, ret_bench)
        out["benchmark_annualized_return"] = _annualized_return(b)
        out["alpha_annualized"] = alpha_ann
        out["beta"] = beta
        out["tracking_error_annualized"] = te
        out["information_ratio"] = _information_ratio(returns, ret_bench)

    return out


# Section titles (no numbering); metric_key -> display label (English + 中文)
# Layout follows common fund/quant fact-sheet style: Period, Returns, Risk, Drawdown, Risk-Adjusted, Benchmark-Relative.
_PERFORMANCE_CATEGORIES: List[Tuple[str, List[Tuple[str, str]]]] = [
    ("Period", [
        ("start_date", "Start Date"),
        ("end_date", "End Date"),
        ("n_observations", "Observations"),
    ]),
    ("Returns", [
        ("total_return", "Total Return"),
        ("annualized_return", "Annualized Return (CAGR)"),
    ]),
    ("Risk", [
        ("annualized_volatility", "Volatility (Ann.)"),
    ]),
    ("Drawdown", [
        ("max_drawdown", "Max Drawdown"),
        ("max_drawdown_pct", "Max Drawdown (%)"),
        ("max_drawdown_duration_periods", "Max DD Duration (periods)"),
    ]),
    ("Risk-Adjusted Returns", [
        ("sharpe_ratio", "Sharpe Ratio"),
        ("sortino_ratio", "Sortino Ratio"),
        ("calmar_ratio", "Calmar Ratio"),
        ("win_rate", "Win Rate"),
    ]),
    ("Benchmark-Relative", [
        ("benchmark_annualized_return", "Benchmark Return (Ann.)"),
        ("alpha_annualized", "Alpha (Ann.)"),
        ("beta", "Beta"),
        ("tracking_error_annualized", "Tracking Error (Ann.)"),
        ("information_ratio", "Information Ratio"),
    ]),
]


def _format_value(v: object) -> str:
    """Format a metric value for display."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    if isinstance(v, (int, np.integer)):
        return str(v)
    if isinstance(v, str):
        return v
    if isinstance(v, (float, np.floating)):
        if abs(v) < 1e-4 and v != 0:
            return f"{v:.6g}"
        if abs(v) >= 1e4 or abs(v) < 0.0001:
            return f"{v:.4g}"
        return f"{v:.4f}"
    return str(v)


def _build_summary_lines(metrics: Dict[str, object]) -> List[str]:
    """Build categorized txt lines. Skips sections where all keys are missing."""
    width = 56
    lines = []
    lines.append("")
    lines.append("  PERFORMANCE SUMMARY")
    lines.append("  " + "=" * (width - 2))
    lines.append("")

    for section_title, items in _PERFORMANCE_CATEGORIES:
        row_lines = []
        for key, label in items:
            if key not in metrics:
                continue
            val = metrics[key]
            row_lines.append((label, _format_value(val)))
        if not row_lines:
            continue
        lines.append("  " + section_title)
        lines.append("  " + "-" * (width - 2))
        label_w = max(len(l) for l, _ in row_lines)
        for label, val_str in row_lines:
            lines.append(f"    {label:<{label_w}}  {val_str}")
        lines.append("")

    lines.append("  " + "=" * (width - 2))
    return lines


def save_performance_summary(
    equity_history: Dict[str, float],
    save_path,
    benchmark: Optional[Dict[str, float]] = None,
    risk_free_rate: float = 0.0,
) -> None:
    """
    Compute performance metrics, save to .txt by category, optionally print.
    save_path: path to .txt file (e.g. from paths['output'][strategy]['performance_summary']).
    """
    metrics = compute_performance_metrics(
        equity_history=equity_history,
        benchmark=benchmark,
        risk_free_rate=risk_free_rate,
    )
    if not metrics:
        raise ValueError("No equity history; performance summary skipped.")

    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    txt_lines = _build_summary_lines(metrics)
    txt_content = "\n".join(txt_lines)
    save_path.write_text(txt_content, encoding="utf-8")
    print(f"Performance summary saved to: {save_path}")
