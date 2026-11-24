"""Order-flow imbalance: the event rule case by case, the regression maths, and alignment."""

from __future__ import annotations

import numpy as np
import pytest

from undertow.ofi import Intervals, aggregate, depth_relation, event_contributions, ols, window_fits

A = np.asarray


def e_of(prev: tuple[float, float, float, float], cur: tuple[float, float, float, float]) -> float:
    """e_n for one pair of quotes given as (bid, bid size, ask, ask size)."""
    rows = np.array([prev, cur], dtype=np.float64)
    return float(event_contributions(rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3])[1])


@pytest.mark.parametrize(
    ("prev", "cur", "expected"),
    [
        # sizes change at unchanged prices: the change in bid size minus the change in ask size
        ((100.0, 5.0, 100.1, 7.0), (100.0, 8.0, 100.1, 7.0), 3.0),
        ((100.0, 5.0, 100.1, 7.0), (100.0, 2.0, 100.1, 7.0), -3.0),
        ((100.0, 5.0, 100.1, 7.0), (100.0, 5.0, 100.1, 9.0), -2.0),
        ((100.0, 5.0, 100.1, 7.0), (100.0, 5.0, 100.1, 4.0), 3.0),
        # bid moves up: the whole new bid queue counts as added demand
        ((100.0, 5.0, 100.2, 7.0), (100.1, 2.0, 100.2, 7.0), 2.0),
        # bid moves down: the whole old bid queue was removed
        ((100.0, 5.0, 100.2, 7.0), (99.9, 9.0, 100.2, 7.0), -5.0),
        # ask moves down: the whole new ask queue counts as added supply
        ((100.0, 5.0, 100.2, 7.0), (100.0, 5.0, 100.1, 3.0), -3.0),
        # ask moves up: the whole old ask queue was removed
        ((100.0, 5.0, 100.2, 7.0), (100.0, 5.0, 100.3, 1.0), 7.0),
        # both sides step up one tick
        ((100.0, 5.0, 100.1, 7.0), (100.1, 2.0, 100.2, 6.0), 9.0),
    ],
)
def test_event_contribution_cases(
    prev: tuple[float, float, float, float], cur: tuple[float, float, float, float], expected: float
) -> None:
    assert e_of(prev, cur) == pytest.approx(expected)


def test_first_event_contributes_nothing_and_short_inputs_work() -> None:
    assert event_contributions(A([1.0]), A([2.0]), A([3.0]), A([4.0])).tolist() == [0.0]
    assert len(event_contributions(A([]), A([]), A([]), A([]))) == 0


def test_ofi_telescopes_when_prices_do_not_move() -> None:
    rng = np.random.default_rng(0)
    n = 500
    bid_qty = rng.uniform(1, 10, n)
    ask_qty = rng.uniform(1, 10, n)
    e = event_contributions(np.full(n, 50.0), bid_qty, np.full(n, 50.1), ask_qty)
    assert e.sum() == pytest.approx((bid_qty[-1] - bid_qty[0]) - (ask_qty[-1] - ask_qty[0]))


def test_ofi_is_antisymmetric_under_swapping_sides() -> None:
    rng = np.random.default_rng(1)
    n = 300
    bid = 100 + np.cumsum(rng.integers(-1, 2, n)) * 0.1
    ask = bid + 0.1
    bq, aq = rng.uniform(1, 5, n), rng.uniform(1, 5, n)
    e = event_contributions(bid, bq, ask, aq)
    mirrored = event_contributions(-ask, aq, -bid, bq)
    assert np.allclose(e, -mirrored)


def test_ols_exact_fit_and_against_polyfit() -> None:
    rng = np.random.default_rng(2)
    x = rng.normal(size=200)
    exact = ols(1.5 + 2.0 * x, x)
    assert exact.coef == pytest.approx([1.5, 2.0])
    assert exact.r2 == pytest.approx(1.0)
    y = 0.3 - 0.7 * x + rng.normal(size=200)
    fit = ols(y, x)
    slope, intercept = np.polyfit(x, y, 1)
    assert fit.coef == pytest.approx([intercept, slope])
    assert fit.r2 == pytest.approx(np.corrcoef(x, y)[0, 1] ** 2)
    assert fit.n == 200


def test_ols_white_t_statistic_by_hand() -> None:
    rng = np.random.default_rng(3)
    x = rng.normal(size=400)
    y = 1.0 + 0.5 * x + rng.normal(size=400) * (1 + np.abs(x))
    fit = ols(y, x)
    xc = x - x.mean()
    resid = y - fit.coef[0] - fit.coef[1] * x
    var_slope = (xc**2 * resid**2).sum() / (xc**2).sum() ** 2
    assert fit.tstat[1] == pytest.approx(fit.coef[1] / np.sqrt(var_slope))


def test_ols_two_regressors() -> None:
    rng = np.random.default_rng(4)
    x = rng.normal(size=(300, 2))
    y = 2.0 + x @ A([1.0, -3.0])
    assert ols(y, x).coef == pytest.approx([2.0, 1.0, -3.0])


def _bars(n: int) -> dict[str, np.ndarray]:
    return {
        "buy_volume": np.zeros(n),
        "sell_volume": np.zeros(n),
        "depth": np.ones(n),
        "updates": np.ones(n),
        "valid": np.ones(n, dtype=np.bool_),
    }


def test_aggregate_aligns_flow_with_the_price_change_of_the_same_interval() -> None:
    # the mid moves by exactly the order flow of each second, in ticks
    rng = np.random.default_rng(5)
    n, step, tick = 600, 5, 0.1
    flow = rng.integers(-3, 4, n).astype(np.float64)
    mid = 100.0 + np.cumsum(flow) * tick
    iv = aggregate(mid, flow, **_bars(n), step=step, tick=tick)
    assert len(iv.dp) == n // step - 1
    assert np.allclose(iv.dp, iv.ofi)
    assert iv.ok.all()
    # by hand for the second interval
    assert iv.ofi[0] == pytest.approx(flow[5:10].sum())
    assert iv.dp[0] == pytest.approx((mid[9] - mid[4]) / tick)


def test_aggregate_trade_imbalance_and_depth() -> None:
    n = 40
    kw = _bars(n)
    kw["buy_volume"] = np.full(n, 2.0)
    kw["sell_volume"] = np.full(n, 0.5)
    kw["depth"] = np.tile([1.0, 3.0], n // 2)
    kw["updates"] = np.tile([3.0, 1.0], n // 2)
    iv = aggregate(np.full(n, 10.0), np.zeros(n), **kw, step=10, tick=0.1)
    assert np.allclose(iv.ti, 15.0)
    assert np.allclose(iv.depth, 1.5)  # update-weighted: (3*1 + 1*3) / 4


def test_aggregate_flags_intervals_that_touch_a_gap() -> None:
    n = 100
    kw = _bars(n)
    kw["valid"][37] = False
    iv = aggregate(np.full(n, 10.0), np.zeros(n), **kw, step=10, tick=0.1)
    # interval 3 holds second 37; its change and the next one both use it
    assert iv.ok.tolist() == [True, True, False, False, True, True, True, True, True]


def test_aggregate_needs_two_intervals() -> None:
    with pytest.raises(ValueError):
        aggregate(np.ones(5), np.zeros(5), **_bars(5), step=5, tick=0.1)


def _intervals(dp: np.ndarray, ofi: np.ndarray, ti: np.ndarray | None = None) -> Intervals:
    n = len(dp)
    return Intervals(
        step=1,
        dp=dp,
        ofi=ofi,
        ti=np.zeros(n) if ti is None else ti,
        depth=np.ones(n),
        ok=np.ones(n, dtype=np.bool_),
    )


def test_window_fits_contemporaneous() -> None:
    rng = np.random.default_rng(6)
    ofi = rng.normal(size=720)
    ti = rng.normal(size=720)
    dp = 2.0 * ofi + rng.normal(size=720)
    w = window_fits(_intervals(dp, ofi, ti), window=180)
    assert len(w.r2_ofi) == 4
    assert np.all((w.r2_ofi > 0.7) & (w.r2_ofi < 0.9))  # population value is 0.8
    assert np.all(w.r2_ti < 0.1)
    assert np.all(w.r2_both >= w.r2_ofi - 1e-12)
    assert np.allclose(w.beta_ofi, 2.0, atol=0.3)
    assert np.all(w.t_ofi > 10)
    # no predictive content was built in
    assert np.nanmean(w.r2_next_oos) < 0.02
    assert np.isnan(w.r2_next_oos[0])  # the first window has no earlier fit to forecast with


def test_window_fits_predictive_uses_the_lag_not_the_same_interval() -> None:
    rng = np.random.default_rng(7)
    ofi = rng.normal(size=541)
    dp = np.concatenate([[0.0], 3.0 * ofi[:-1]])  # this interval's move is last interval's flow
    w = window_fits(_intervals(dp, ofi), window=180)
    assert np.allclose(w.r2_next, 1.0)
    assert np.allclose(w.r2_next_oos[1:], 1.0)
    assert np.allclose(w.hit_next_oos[1:], 1.0)
    assert np.allclose(
        w.gain_next_oos[1:], [np.abs(dp[181:360]).mean(), np.abs(dp[361:540]).mean()]
    )
    assert np.all(w.r2_ofi < 0.1)  # and nothing contemporaneous


def test_window_fits_skips_bad_windows_and_does_not_forecast_across_them() -> None:
    rng = np.random.default_rng(8)
    ofi = rng.normal(size=720)
    dp = ofi + rng.normal(size=720)
    iv = _intervals(dp, ofi)
    iv.ok[200] = False
    w = window_fits(iv, window=180)
    assert len(w.r2_ofi) == 3
    # window 3 follows the skipped one, so it has no forecast; window 4 does
    assert np.isnan(w.r2_next_oos[0]) and np.isnan(w.r2_next_oos[1])
    assert np.isfinite(w.r2_next_oos[2])


def test_depth_relation_recovers_known_parameters() -> None:
    depth = np.linspace(1.0, 50.0, 40)
    beta = 0.45 / depth**0.98
    c, lam, r2, n = depth_relation(beta, depth)
    assert (c, lam, r2, n) == pytest.approx((0.45, 0.98, 1.0, 40))
    beta[3] = -0.1  # a negative slope cannot be logged
    assert depth_relation(beta, depth)[3] == 39
