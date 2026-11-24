"""Order-flow imbalance after Cont, Kukanov and Stoikov, and the regressions run on it.

Formulas are from arXiv:1011.6402v3 (the working-paper version of the 2014 article); see
PAPER.md for the section of each.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def event_contributions(
    bid: FloatArray, bid_qty: FloatArray, ask: FloatArray, ask_qty: FloatArray
) -> FloatArray:
    """Contribution e_n of each quote update to order-flow imbalance (CKS section 2.1).

        e_n = 1{Pb_n >= Pb_{n-1}} qb_n - 1{Pb_n <= Pb_{n-1}} qb_{n-1}
            - 1{Pa_n <= Pa_{n-1}} qa_n + 1{Pa_n >= Pa_{n-1}} qa_{n-1}

    The first update has no predecessor and contributes zero.
    """
    e = np.zeros(len(bid))
    if len(bid) < 2:
        return e
    pb, pb0 = bid[1:], bid[:-1]
    pa, pa0 = ask[1:], ask[:-1]
    e[1:] = (
        (pb >= pb0) * bid_qty[1:]
        - (pb <= pb0) * bid_qty[:-1]
        - (pa <= pa0) * ask_qty[1:]
        + (pa >= pa0) * ask_qty[:-1]
    )
    return e


@dataclass(frozen=True)
class Intervals:
    """Quantities over consecutive intervals of ``step`` seconds.

    ``dp`` is the mid-price change over the interval in ticks. ``ok`` is False for an interval
    that contains an invalid second.
    """

    step: int
    dp: FloatArray
    ofi: FloatArray
    ti: FloatArray
    depth: FloatArray
    ok: NDArray[np.bool_]


def aggregate(
    mid: FloatArray,
    ofi: FloatArray,
    buy_volume: FloatArray,
    sell_volume: FloatArray,
    depth: FloatArray,
    updates: FloatArray,
    valid: NDArray[np.bool_],
    step: int,
    tick: float,
) -> Intervals:
    """Sum one-second bars into intervals of ``step`` seconds.

    Interval k covers seconds ``[k*step, (k+1)*step)``. Its price change is the last mid in the
    interval minus the last mid in the interval before, so the first interval is dropped.
    Depth is the average over quote updates of (bid size + ask size) / 2, as CKS define AD.
    """
    m = len(mid) // step
    if m < 2:
        raise ValueError("not enough bars for this interval")

    def total(x: FloatArray) -> FloatArray:
        summed: FloatArray = x[: m * step].reshape(m, step).sum(axis=1)
        return summed

    close = mid[: m * step].reshape(m, step)[:, -1]
    dp = np.diff(close) / tick
    weight = total(updates)
    weighted_depth = total(depth * updates)
    plain_depth = total(depth) / step
    avg_depth = np.where(weight > 0, weighted_depth / np.maximum(weight, 1.0), plain_depth)
    ok_all = valid[: m * step].reshape(m, step).all(axis=1)
    ok = ok_all[1:] & ok_all[:-1]
    return Intervals(
        step=step,
        dp=dp,
        ofi=total(ofi)[1:],
        ti=(total(buy_volume) - total(sell_volume))[1:],
        depth=avg_depth[1:],
        ok=ok,
    )


@dataclass(frozen=True)
class Fit:
    """OLS of y on a constant and regressors, with White (HC0) t-statistics."""

    coef: FloatArray
    tstat: FloatArray
    r2: float
    n: int


def ols(y: FloatArray, x: FloatArray) -> Fit:
    """Ordinary least squares with an intercept. ``coef[0]`` is the intercept.

    ``x`` is one regressor (1-D) or several (2-D, one column each). Standard errors are White's
    heteroskedasticity-consistent ones without a small-sample correction.
    """
    design = np.column_stack([np.ones(len(y)), x])
    xtx_inv = np.linalg.pinv(design.T @ design)
    coef = xtx_inv @ design.T @ y
    resid = y - design @ coef
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - float((resid**2).sum()) / sst if sst > 0 else float("nan")
    meat = (design * (resid**2)[:, None]).T @ design
    cov = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        tstat = np.where(se > 0, coef / se, np.nan)
    return Fit(coef=coef, tstat=tstat, r2=r2, n=len(y))


@dataclass(frozen=True)
class WindowFits:
    """Per-window regression results. One entry per window that passed the filters."""

    r2_ofi: FloatArray
    beta_ofi: FloatArray
    t_ofi: FloatArray
    r2_ti: FloatArray
    r2_both: FloatArray
    t_ti_given_ofi: FloatArray
    r2_next: FloatArray
    r2_next_oos: FloatArray
    hit_next_oos: FloatArray
    gain_next_oos: FloatArray
    r2_next_oos_return: FloatArray
    hit_next_oos_return: FloatArray
    depth: FloatArray


def window_fits(iv: Intervals, window: int = 180) -> WindowFits:
    """Run the CKS regressions in consecutive windows of ``window`` intervals.

    In each window:

    * dP_k on OFI_k (CKS eq. 4), on TI_k (eq. 8b) and on both (eq. 8c);
    * dP_{k+1} on OFI_k, the predictive version, in sample;
    * the same out of sample: the slope and intercept fitted in the previous window forecast
      dP_{k+1} in this one. ``r2_next_oos`` is 1 - SSE / sum(dP^2), measured against a
      forecast of zero. ``hit_next_oos`` is the share of non-zero price changes whose sign the
      forecast got right. ``gain_next_oos`` is the mean of sign(forecast) * dP_{k+1} in ticks:
      what following the forecast's sign every interval would collect before any cost;
    * the same out-of-sample forecast built from the lagged price change dP_k instead of the
      imbalance (``r2_next_oos_return``, ``hit_next_oos_return``), to see whether imbalance
      says more than the last move does.

    Windows with an invalid interval or with no price variation are skipped.
    """
    out: dict[str, list[float]] = {name: [] for name in WindowFits.__dataclass_fields__}
    nan = float("nan")

    def forecast_scores(
        coef: FloatArray | None, lag: FloatArray, lead: FloatArray
    ) -> tuple[float, float, float]:
        if coef is None:
            return nan, nan, nan
        forecast = coef[0] + coef[1] * lag
        sse = float(((lead - forecast) ** 2).sum())
        base = float((lead**2).sum())
        moved = lead != 0
        hit = float(np.mean(np.sign(forecast[moved]) == np.sign(lead[moved])))
        return (
            1.0 - sse / base if base > 0 else nan,
            hit if moved.any() else nan,
            float(np.mean(np.sign(forecast) * lead)),
        )

    previous: FloatArray | None = None
    previous_return: FloatArray | None = None
    for start in range(0, len(iv.dp) - window + 1, window):
        sl = slice(start, start + window)
        dp, x, ti = iv.dp[sl], iv.ofi[sl], iv.ti[sl]
        if not iv.ok[sl].all() or np.ptp(dp) == 0 or np.ptp(x) == 0:
            previous = previous_return = None
            continue
        fit = ols(dp, x)
        fit_ti = ols(dp, ti)
        fit_both = ols(dp, np.column_stack([x, ti]))
        lead, lag, lag_return = dp[1:], x[:-1], dp[:-1]
        fit_next = ols(lead, lag) if np.ptp(lead) > 0 else None
        fit_return = ols(lead, lag_return) if np.ptp(lead) > 0 else None
        r2_oos, hit, gain = forecast_scores(previous, lag, lead)
        r2_oos_return, hit_return, _ = forecast_scores(previous_return, lag_return, lead)
        out["r2_next_oos"].append(r2_oos)
        out["hit_next_oos"].append(hit)
        out["gain_next_oos"].append(gain)
        out["r2_next_oos_return"].append(r2_oos_return)
        out["hit_next_oos_return"].append(hit_return)
        previous = fit_next.coef if fit_next is not None else None
        previous_return = fit_return.coef if fit_return is not None else None
        out["r2_ofi"].append(fit.r2)
        out["beta_ofi"].append(float(fit.coef[1]))
        out["t_ofi"].append(float(fit.tstat[1]))
        out["r2_ti"].append(fit_ti.r2)
        out["r2_both"].append(fit_both.r2)
        out["t_ti_given_ofi"].append(float(fit_both.tstat[2]))
        out["r2_next"].append(fit_next.r2 if fit_next is not None else float("nan"))
        out["depth"].append(float(iv.depth[sl].mean()))
    return WindowFits(**{name: np.asarray(values) for name, values in out.items()})


def depth_relation(beta: FloatArray, depth: FloatArray) -> tuple[float, float, float, int]:
    """Fit log(beta_i) = log(c) - lambda * log(AD_i) across windows (CKS eq. 5).

    Returns ``(c, lambda, r2, n)``. Windows with a non-positive slope cannot be logged and are
    left out; ``n`` is the number used.
    """
    keep = (beta > 0) & (depth > 0)
    fit = ols(np.log(beta[keep]), np.log(depth[keep]))
    return float(np.exp(fit.coef[0])), float(-fit.coef[1]), fit.r2, int(keep.sum())
