"""The experiments behind the tables in results/. Each returns a pandas DataFrame.

Everything here is deterministic given its inputs. The only random numbers are in the two
simulations (the Avellaneda-Stoikov Monte Carlo and the spread-estimator test), and their seeds
are fixed arguments.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from undertow import quoter, spread, stats
from undertow.data import Bars, Trades
from undertow.ofi import WindowFits, aggregate, depth_relation, window_fits

FloatArray = NDArray[np.float64]

HORIZONS = [1, 5, 10, 30, 60, 300]
WINDOW = 180

# Dimensionless settings of the paper's simulation (section 3.3): gamma / k for its three
# risk aversions with k = 1.5, and sigma^2 T k^2 = 2^2 * 1 * 1.5^2.
PAPER_GAMMA_OVER_K = [0.01 / 1.5, 0.1 / 1.5, 1.0 / 1.5]
PAPER_GAMMAS = [0.01, 0.1, 1.0]
PAPER_SIGMA2_T_K2 = 9.0

# Published tables 1 to 3: gamma, strategy, spread, profit, std(profit), final q, std(final q).
PAPER_TABLES = [
    (0.1, "inventory", 1.49, 65.0, 6.6, 0.08, 2.9),
    (0.1, "symmetric", 1.49, 68.4, 12.7, 0.26, 8.4),
    (0.01, "inventory", 1.35, 68.6, 8.7, 0.12, 5.1),
    (0.01, "symmetric", 1.35, 68.8, 12.8, 0.09, 8.7),
    (1.0, "inventory", 3.02, 31.4, 5.0, 0.02, 1.7),
    (1.0, "symmetric", 3.02, 44.0, 11.0, 0.00, 5.1),
]


def fits_at(bars: Bars, step: int, tick: float, window: int = WINDOW) -> WindowFits:
    """Window regressions for one interval length."""
    iv = aggregate(
        bars.mid,
        bars.ofi,
        bars.buy_volume,
        bars.sell_volume,
        bars.depth,
        bars.updates,
        bars.valid,
        step,
        tick,
    )
    return window_fits(iv, window)


def _mean(x: FloatArray) -> float:
    return float(np.nanmean(x)) if np.isfinite(x).any() else float("nan")


def sample_table(days: list[Bars], labels: list[str], tick: float) -> pd.DataFrame:
    """Plain facts about the tape, day by day and for all days together.

    Per one-second bar: quote updates, bars with no update, the mid at the first and last bar
    and the change between them, the absolute change in the mid from one bar to the next
    (mean, median, standard deviation, in ticks), the share of bars that end with the spread at
    one tick, and the first-order autocorrelation of the bar-to-bar mid change. Bar pairs that
    touch an invalid bar are left out of the change statistics.
    """

    def row(label: str, parts: list[Bars]) -> dict[str, object]:
        changes: list[FloatArray] = []
        lead: list[FloatArray] = []
        lag: list[FloatArray] = []
        for b in parts:
            dm = np.diff(b.mid) / tick
            ok = b.valid[1:] & b.valid[:-1]
            changes.append(dm[ok])
            both = ok[1:] & ok[:-1]
            lag.append(dm[:-1][both])
            lead.append(dm[1:][both])
        change = np.concatenate(changes)
        x, y = np.concatenate(lag), np.concatenate(lead)
        spread_ticks = np.concatenate(
            [np.round((b.ask[b.valid] - b.bid[b.valid]) / tick) for b in parts]
        )
        first, last = parts[0].mid[0], parts[-1].mid[-1]
        return {
            "day": label,
            "seconds": int(sum(len(b) for b in parts)),
            "quote_updates": int(sum(b.updates.sum() for b in parts)),
            "seconds_without_update": int(sum((b.updates == 0).sum() for b in parts)),
            "mid_first": float(first),
            "mid_last": float(last),
            "change_pct": 100.0 * float(last / first - 1.0),
            "abs_change_mean_ticks": float(np.mean(np.abs(change))),
            "abs_change_median_ticks": float(np.median(np.abs(change))),
            "change_sd_ticks": float(np.std(change, ddof=1)),
            "spread_one_tick_share": float(np.mean(spread_ticks == 1)),
            "change_autocorr_1": float(np.corrcoef(x, y)[0, 1]),
        }

    rows = [row(label, [b]) for label, b in zip(labels, days, strict=True)]
    rows.append(row("all", days))
    return pd.DataFrame(rows)


BOOTSTRAP_STATISTICS = [
    "r2_ofi",
    "r2_next_out_of_sample",
    "sign_hit_out_of_sample",
    "sign_gain_bps",
    "sign_hit_lagged_return",
]


def ofi_bootstrap(
    bars: Bars,
    tick: float,
    horizons: list[int] | None = None,
    window: int = WINDOW,
    resamples: int = 2000,
    seed: int = 0,
) -> pd.DataFrame:
    """95% block-bootstrap intervals for the window averages in table 1.

    The windows of each interval length form a series in time order. Blocks of
    :func:`stats.block_length` consecutive windows are resampled (circular block bootstrap,
    percentile interval). One row per interval length and statistic.
    """
    rows = []
    price = float(np.mean(bars.mid))
    for step in horizons or HORIZONS:
        if len(bars) // step < window + 1:
            continue
        w = fits_at(bars, step, tick, window)
        if len(w.r2_ofi) == 0:
            continue
        series = {
            "r2_ofi": w.r2_ofi,
            "r2_next_out_of_sample": w.r2_next_oos,
            "sign_hit_out_of_sample": w.hit_next_oos,
            "sign_gain_bps": 1e4 * tick * w.gain_next_oos / price,
            "sign_hit_lagged_return": w.hit_next_oos_return,
        }
        for name in BOOTSTRAP_STATISTICS:
            x = series[name]
            used = int(np.isfinite(x).sum())
            block = stats.block_length(used)
            mean, low, high = stats.block_bootstrap(x, block, resamples=resamples, seed=seed)
            rows.append(
                {
                    "interval_s": step,
                    "statistic": name,
                    "estimate": mean,
                    "ci95_low": low,
                    "ci95_high": high,
                    "windows": used,
                    "block_windows": block,
                }
            )
    return pd.DataFrame(rows)


def ofi_by_horizon(
    bars: Bars, tick: float, horizons: list[int] | None = None, window: int = WINDOW
) -> pd.DataFrame:
    """Average window regression results at each interval length.

    Columns: interval in seconds, number of windows, mean R-squared of the price change on
    order-flow imbalance, on trade imbalance and on both, mean t-statistic and share of windows
    where the imbalance slope is significant at 5%, share where trade imbalance stays
    significant next to it, and the predictive regression of the next interval's price change
    on this interval's imbalance: in-sample R-squared, out-of-sample R-squared,
    out-of-sample share of signs called correctly, and the mean price change collected by
    following the forecast's sign, in ticks and in basis points of price, before any cost.
    The last two columns repeat the out-of-sample forecast with the lagged price change in
    place of the imbalance.
    """
    rows = []
    price = float(np.mean(bars.mid))
    for step in horizons or HORIZONS:
        if len(bars) // step < window + 1:
            continue
        w = fits_at(bars, step, tick, window)
        if len(w.r2_ofi) == 0:
            continue
        rows.append(
            {
                "interval_s": step,
                "windows": len(w.r2_ofi),
                "r2_ofi": _mean(w.r2_ofi),
                "r2_ti": _mean(w.r2_ti),
                "r2_both": _mean(w.r2_both),
                "t_ofi": _mean(w.t_ofi),
                "ofi_significant": float(np.mean(np.abs(w.t_ofi) > 1.96)),
                "ti_significant_given_ofi": float(np.mean(np.abs(w.t_ti_given_ofi) > 1.96)),
                "r2_next_in_sample": _mean(w.r2_next),
                "r2_next_out_of_sample": _mean(w.r2_next_oos),
                "sign_hit_out_of_sample": _mean(w.hit_next_oos),
                "sign_gain_ticks": _mean(w.gain_next_oos),
                "sign_gain_bps": 1e4 * tick * _mean(w.gain_next_oos) / price,
                "r2_next_oos_lagged_return": _mean(w.r2_next_oos_return),
                "sign_hit_lagged_return": _mean(w.hit_next_oos_return),
            }
        )
    return pd.DataFrame(rows)


def depth_table(bars: Bars, tick: float, step: int = 10, window: int = WINDOW) -> pd.DataFrame:
    """The fit of log(beta) on log(average depth) across windows (CKS eq. 5)."""
    w = fits_at(bars, step, tick, window)
    c, lam, r2, n = depth_relation(w.beta_ofi, w.depth)
    return pd.DataFrame([{"interval_s": step, "windows_used": n, "c": c, "lambda": lam, "r2": r2}])


def paper_simulation(paths: int = 1000, seed: int = 0) -> pd.DataFrame:
    """The paper's Monte Carlo next to its published tables 1 to 3."""
    rows = []
    for gamma, strategy, p_spread, p_profit, p_std, p_q, p_q_std in PAPER_TABLES:
        run = quoter.simulate_paper(gamma, strategy == "inventory", paths=paths, seed=seed)
        rows.append(
            {
                "gamma": gamma,
                "strategy": strategy,
                "spread": run.spread,
                "paper_spread": p_spread,
                "profit": run.profit_mean,
                "paper_profit": p_profit,
                "profit_std": run.profit_std,
                "paper_profit_std": p_std,
                "final_q": run.q_mean,
                "paper_final_q": p_q,
                "final_q_std": run.q_std,
                "paper_final_q_std": p_q_std,
            }
        )
    return pd.DataFrame(rows)


def calibrate_bars(bars: Bars, tick: float) -> quoter.Calibration:
    """Calibrate the quoter on bars. Rates and volatility are per bar, not per second."""
    return quoter.calibrate(bars.mid, bars.max_buy, bars.min_sell, bars.valid, tick)


def paper_tau(cal: quoter.Calibration) -> float:
    """The horizon, in bars, that solves sigma^2 tau k^2 = 9 (the paper's value)."""
    return PAPER_SIGMA2_T_K2 / (cal.sigma**2 * cal.k**2)


def calibration_row(cal: quoter.Calibration, calibration: Bars, test: Bars) -> dict[str, float]:
    """Calibration in per-second units, whatever the bar length."""
    bar = calibration.bar
    return {
        "requote_s": bar,
        "A_per_s": cal.a / bar,
        "k_per_usdt": cal.k,
        "fit_r2": cal.r2,
        "sigma_usdt_per_sqrt_s": cal.sigma / float(np.sqrt(bar)),
        "tau_s": paper_tau(cal) * bar,
        "calibration_hours": len(calibration) * bar / 3600.0,
        "test_hours": len(test) * bar / 3600.0,
    }


def calibration_table(cal: quoter.Calibration, bar: float) -> pd.DataFrame:
    """Measured fill rate at each distance next to the fitted exponential."""
    return pd.DataFrame(
        {
            "requote_s": bar,
            "delta": cal.delta,
            "rate_per_s": cal.rate / bar,
            "fitted_rate_per_s": quoter.intensity(cal.delta, cal.a, cal.k) / bar,
        }
    )


QUOTE_SIZE = 1.0
DAY_SECONDS = 86_400


def _day_labels(test: Bars) -> NDArray[np.int64]:
    """Day number (days since the Unix epoch) of each bar."""
    bar_ms = round(test.bar * 1000)
    first = test.start * bar_ms
    return (first + np.arange(len(test), dtype=np.int64) * bar_ms) // (DAY_SECONDS * 1000)


def quoter_runs(
    test: Bars, cal: quoter.Calibration, tick: float, trades: Trades | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay the quoter on ``test`` bars with parameters calibrated elsewhere.

    The two free parameters are set by matching the paper's simulation in dimensionless form,
    not by search: ``gamma / k`` takes the paper's three values and the horizon ``tau`` solves
    ``sigma^2 tau k^2 = 9``. Each setting is run with and without the inventory skew, under
    the kind and the unkind fill rule, and under two size rules: ``full``, where every fill is
    the whole 1 BTC quote, and ``traded``, where a fill is capped by the taker volume that
    printed at the prices the fill rule counts (needs ``trades``).

    Money is USDT, for a quote of 1 BTC. Per-BTC columns divide by the BTC filled.
    ``breakeven_fee_bps`` is profit over traded notional: the largest fee per fill the result
    could pay. Negative means it needs a rebate that large to break even. The day columns
    split the profit by calendar day (UTC) and treat days as independent.

    Returns the summary table and a table of profit per day.
    """
    tau = paper_tau(cal)
    step_day = _day_labels(test)[:-1]
    day_ids = np.unique(step_day)
    ladder = (
        None
        if trades is None
        else quoter.TradeLadder(
            trades.time_ms, trades.price, trades.qty, trades.buy, test.start, test.bar, len(test)
        )
    )
    size_rules = ["full"] if ladder is None else ["full", "traded"]
    rows = []
    day_rows = []
    for ratio, label in zip(PAPER_GAMMA_OVER_K, PAPER_GAMMAS, strict=True):
        gamma = ratio * cal.k
        for inventory in (True, False):
            for kind in (True, False):
                for size_rule in size_rules:
                    run = quoter.simulate_tape(
                        test.bid,
                        test.ask,
                        test.max_buy,
                        test.min_sell,
                        test.valid,
                        gamma=gamma,
                        sigma=cal.sigma,
                        tau=tau,
                        k=cal.k,
                        tick=tick,
                        inventory=inventory,
                        kind=kind,
                        ladder=ladder if size_rule == "traded" else None,
                        size=QUOTE_SIZE,
                    )
                    key = {
                        "requote_s": test.bar,
                        "paper_gamma": label,
                        "strategy": "inventory" if inventory else "symmetric",
                        "fills_rule": "kind" if kind else "unkind",
                        "size_rule": size_rule,
                    }
                    per_day = np.array(
                        [run.step_pnl[step_day == d].sum() for d in day_ids], dtype=np.float64
                    )
                    mean, se, t, positive = stats.day_summary(per_day)
                    filled = run.filled
                    bps = 1e4 * run.pnl / run.traded_notional if run.traded_notional else np.nan
                    rows.append(
                        {
                            **key,
                            "gamma": gamma,
                            "quoted_spread": run.mean_quoted_spread,
                            "fills": run.fills,
                            "filled_btc": filled,
                            "spread_earned": run.spread_earned,
                            "inventory_pnl": run.inventory_pnl,
                            "pnl": run.pnl,
                            "spread_per_btc": run.spread_earned / filled if filled else np.nan,
                            "inventory_per_btc": run.inventory_pnl / filled if filled else np.nan,
                            "pnl_per_btc": run.pnl / filled if filled else np.nan,
                            "breakeven_fee_bps": bps,
                            "days": len(per_day),
                            "day_pnl_mean": mean,
                            "day_pnl_se": se,
                            "day_pnl_t": t,
                            "days_positive": positive,
                            "q_std": run.q_std,
                            "q_abs_max": run.q_abs_max,
                            "q_final": run.q_final,
                        }
                    )
                    for d, value in zip(day_ids, per_day, strict=True):
                        date = pd.Timestamp(int(d) * DAY_SECONDS, unit="s").strftime("%Y-%m-%d")
                        day_rows.append({**key, "day": date, "pnl": float(value)})
    return pd.DataFrame(rows), pd.DataFrame(day_rows)


def quoter_table(
    test: Bars, cal: quoter.Calibration, tick: float, trades: Trades | None = None
) -> pd.DataFrame:
    """The summary table of :func:`quoter_runs`."""
    return quoter_runs(test, cal, tick, trades)[0]


def spread_simulation(
    spreads: list[float] | None = None,
    sigma: float = 0.03,
    days: int = 300,
    runs: int = 200,
    seed: int = 0,
) -> pd.DataFrame:
    """Mean estimate of each estimator on simulated prices with a known spread.

    Daily volatility is ``sigma``. Each run is ``days`` days long, about the length of the
    real sample. The standard deviation across runs is reported next to each mean.
    """
    rows = []
    for true in spreads or [0.02, 0.005, 0.001, 0.0001, 0.0]:
        estimates: dict[str, list[float]] = {"roll": [], "cs": [], "ar2": [], "ar": []}
        for run in range(runs):
            high, low, close = spread.simulate_daily(days, sigma, true, seed=seed + run)
            estimates["roll"].append(spread.roll(close))
            estimates["cs"].append(spread.corwin_schultz(high, low, close))
            estimates["ar2"].append(spread.abdi_ranaldo(close, high, low, two_day=True))
            estimates["ar"].append(spread.abdi_ranaldo(close, high, low, two_day=False))
        row: dict[str, float] = {"true_spread_bps": 1e4 * true}
        for name, values in estimates.items():
            row[f"{name}_mean_bps"] = 1e4 * float(np.mean(values))
            row[f"{name}_sd_bps"] = 1e4 * float(np.std(values, ddof=1))
        rows.append(row)
    return pd.DataFrame(rows)


def spread_real(klines: pd.DataFrame, bars: Bars | None) -> pd.DataFrame:
    """The estimators on real daily bars, next to the quoted spread measured from the bars."""
    high = klines["high"].to_numpy(dtype=np.float64)
    low = klines["low"].to_numpy(dtype=np.float64)
    close = klines["close"].to_numpy(dtype=np.float64)
    rows = [
        {"estimator": "Roll", "spread_bps": 1e4 * spread.roll(close)},
        {
            "estimator": "Corwin-Schultz",
            "spread_bps": 1e4 * spread.corwin_schultz(high, low, close),
        },
        {
            "estimator": "Abdi-Ranaldo, two-day",
            "spread_bps": 1e4 * spread.abdi_ranaldo(close, high, low, two_day=True),
        },
        {
            "estimator": "Abdi-Ranaldo, whole sample",
            "spread_bps": 1e4 * spread.abdi_ranaldo(close, high, low, two_day=False),
        },
    ]
    table = pd.DataFrame(rows)
    table["days"] = len(klines)
    if bars is not None:
        ok = bars.valid
        quoted = float(np.mean((bars.ask[ok] - bars.bid[ok]) / bars.mid[ok]))
        table.loc[len(table)] = {
            "estimator": "Quoted spread, measured",
            "spread_bps": 1e4 * quoted,
            "days": round(len(bars) * bars.bar / 86400.0),
        }
    return table
