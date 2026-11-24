"""Spread estimators: closed forms on constructed prices and recovery on simulated ones."""

from __future__ import annotations

import math

import numpy as np
import pytest

from undertow.spread import abdi_ranaldo, corwin_schultz, roll, simulate_daily

A = np.asarray


def test_roll_on_a_pure_bounce() -> None:
    # constant efficient price, trades alternate in a pattern with known autocovariance
    rng = np.random.default_rng(0)
    s = 0.02
    side = rng.choice([-1.0, 1.0], size=200_000)
    close = np.exp(side * s / 2)
    assert roll(close) == pytest.approx(s, rel=0.02)


def test_roll_is_zero_when_changes_are_positively_correlated() -> None:
    close = np.exp(np.cumsum(np.cumsum(np.full(50, 0.001))))  # steadily accelerating
    assert roll(close) == 0.0
    trend = np.exp(np.cumsum(A([0.01, 0.02] * 30)))
    assert roll(trend) >= 0.0


def test_roll_covariance_by_hand() -> None:
    close = np.exp(A([0.0, 0.01, 0.0, 0.01, 0.0, 0.01, 0.0]))
    dp = np.diff(np.log(close))
    cov = np.cov(dp[1:], dp[:-1])[0, 1]
    assert cov < 0
    assert roll(close) == pytest.approx(2 * math.sqrt(-cov))


def test_corwin_schultz_two_days_by_hand() -> None:
    high, low, close = A([10.5, 10.6]), A([10.0, 10.2]), A([10.3, 10.4])
    beta = math.log(10.5 / 10.0) ** 2 + math.log(10.6 / 10.2) ** 2
    gamma = math.log(10.6 / 10.0) ** 2
    d = 3 - 2 * math.sqrt(2)
    alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / d - math.sqrt(gamma / d)
    expected = max(2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha)), 0.0)
    assert corwin_schultz(high, low, close) == pytest.approx(expected)


def test_corwin_schultz_overnight_adjustment() -> None:
    # day 2 trades wholly above day 1's close: the gap of 0.5 is taken out of its range
    high, low, close = A([10.5, 11.4]), A([10.0, 11.0]), A([10.5, 11.2])
    shifted = corwin_schultz(A([10.5, 10.9]), A([10.0, 10.5]), A([10.5, 10.7]))
    assert corwin_schultz(high, low, close) == pytest.approx(shifted)
    # and wholly below: raised by the gap
    down = corwin_schultz(A([10.5, 9.8]), A([10.0, 9.4]), A([10.2, 9.6]))
    assert down == pytest.approx(corwin_schultz(A([10.5, 10.2]), A([10.0, 9.8]), A([10.2, 10.0])))


def test_corwin_schultz_floors_negative_estimates_at_zero() -> None:
    # a two-day range much wider than either day gives a negative alpha
    assert corwin_schultz(A([10.1, 12.1]), A([10.0, 12.0]), A([10.05, 12.05])) >= 0.0
    assert corwin_schultz(A([10.0, 10.0]), A([10.0, 10.0]), A([10.0, 10.0])) == 0.0


def test_abdi_ranaldo_by_hand() -> None:
    high, low, close = A([10.4, 10.6, 10.5]), A([10.0, 10.2, 10.1]), A([10.35, 10.25, 10.3])
    c = np.log(close)
    eta = (np.log(high) + np.log(low)) / 2
    products = [4 * (c[t] - eta[t]) * (c[t] - eta[t + 1]) for t in range(2)]
    two_day = np.mean([math.sqrt(max(x, 0.0)) for x in products])
    whole = math.sqrt(max(float(np.mean(products)), 0.0))
    assert abdi_ranaldo(close, high, low, two_day=True) == pytest.approx(two_day)
    assert abdi_ranaldo(close, high, low, two_day=False) == pytest.approx(whole)


def test_abdi_ranaldo_whole_sample_is_zero_when_the_mean_is_negative() -> None:
    # closes on opposite sides of consecutive mid-ranges make every product negative
    high, low = A([10.2, 10.6, 10.2, 10.6]), A([10.0, 10.4, 10.0, 10.4])
    close = A([10.2, 10.4, 10.2, 10.4])
    assert abdi_ranaldo(close, high, low, two_day=False) == 0.0
    assert abdi_ranaldo(close, high, low, two_day=True) == 0.0


def test_simulator_shapes_and_seed() -> None:
    high, low, close = simulate_daily(50, 0.02, 0.01, seed=3)
    assert high.shape == low.shape == close.shape == (50,)
    assert np.all(high >= close) and np.all(close >= low)
    again = simulate_daily(50, 0.02, 0.01, seed=3)
    assert np.array_equal(high, again[0])
    assert not np.array_equal(high, simulate_daily(50, 0.02, 0.01, seed=4)[0])


def test_estimators_recover_a_wide_spread() -> None:
    # spread 2% against daily volatility 1%: the regime the estimators were built for
    true = 0.02
    est = {"roll": [], "cs": [], "ar": []}
    for seed in range(40):
        high, low, close = simulate_daily(250, 0.01, true, seed=seed)
        est["roll"].append(roll(close))
        est["cs"].append(corwin_schultz(high, low, close))
        est["ar"].append(abdi_ranaldo(close, high, low, two_day=False))
    assert np.mean(est["roll"]) == pytest.approx(true, rel=0.1)
    assert np.mean(est["ar"]) == pytest.approx(true, rel=0.1)
    # Corwin-Schultz assumes the high is a buy and the low a sell and is biased by discreteness
    assert np.mean(est["cs"]) == pytest.approx(true, rel=0.25)


def test_estimators_cannot_see_a_tiny_spread_under_high_volatility() -> None:
    # one basis point of spread under 3% daily volatility: estimates are noise, far above truth
    true = 0.0001
    cs, ar2 = [], []
    for seed in range(20):
        high, low, close = simulate_daily(300, 0.03, true, seed=seed)
        cs.append(corwin_schultz(high, low, close))
        ar2.append(abdi_ranaldo(close, high, low, two_day=True))
    assert np.mean(cs) > 20 * true
    assert np.mean(ar2) > 20 * true
