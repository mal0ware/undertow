"""Three estimators of the bid-ask spread from daily prices, and a simulator to test them.

All three return a proportional spread (0.01 is one percent of price).

* Roll (1984), as restated in Corwin and Schultz, eqs. (17) to (20).
* Corwin and Schultz (2012), eqs. (6), (9), (15), (16), from the 2009 NBER draft.
* Abdi and Ranaldo (2017), eqs. (10) and (11), from the April 2017 working paper.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def roll(close: FloatArray) -> float:
    """Roll: S = 2 sqrt(-Cov(dp_t, dp_{t-1})) on log closes. Zero if the covariance is positive.

    Setting a positive covariance to zero is the convention Corwin and Schultz use.
    """
    dp = np.diff(np.log(close))
    cov = float(np.cov(dp[1:], dp[:-1], ddof=1)[0, 1])
    return 2.0 * math.sqrt(-cov) if cov < 0 else 0.0


def corwin_schultz(high: FloatArray, low: FloatArray, close: FloatArray) -> float:
    """Corwin-Schultz high-low estimator, averaged over overlapping two-day periods.

    For days t and t+1:

        beta  = ln(H_t / L_t)^2 + ln(H_{t+1} / L_{t+1})^2                      (6)
        gamma = ln(H_{t,t+1} / L_{t,t+1})^2                                    (9)
        alpha = (sqrt(2 beta) - sqrt(beta)) / (3 - 2 sqrt 2)
                - sqrt(gamma / (3 - 2 sqrt 2))                                 (15)
        S     = 2 (e^alpha - 1) / (1 + e^alpha)                                (16)

    Overnight adjustment (their section 2.1): if day t+1 trades entirely above the close of
    day t, its high and low are lowered by the gap; if entirely below, raised by the gap.
    Negative two-day estimates are set to zero before averaging, as in the paper.
    """
    h0, l0, c0 = high[:-1], low[:-1], close[:-1]
    h1, l1 = high[1:].copy(), low[1:].copy()
    up = np.maximum(l1 - c0, 0.0)
    down = np.maximum(c0 - h1, 0.0)
    h1 = h1 - up + down
    l1 = l1 - up + down
    beta = np.log(h0 / l0) ** 2 + np.log(h1 / l1) ** 2
    gamma = np.log(np.maximum(h0, h1) / np.minimum(l0, l1)) ** 2
    denom = 3.0 - 2.0 * math.sqrt(2.0)
    alpha = (np.sqrt(2.0 * beta) - np.sqrt(beta)) / denom - np.sqrt(gamma / denom)
    s = 2.0 * (np.exp(alpha) - 1.0) / (1.0 + np.exp(alpha))
    return float(np.maximum(s, 0.0).mean())


def abdi_ranaldo(
    close: FloatArray, high: FloatArray, low: FloatArray, two_day: bool = True
) -> float:
    """Abdi-Ranaldo close-high-low estimator.

    With c, h, l in logs and eta_t = (h_t + l_t) / 2:

        two-day (11): mean over t of sqrt(max(4 (c_t - eta_t)(c_t - eta_{t+1}), 0))
        whole-sample (10): sqrt(max(4 mean((c_t - eta_t)(c_t - eta_{t+1})), 0))

    The paper applies (10) month by month; here it is applied to whatever sample is passed in.
    """
    c = np.log(close)
    eta = (np.log(high) + np.log(low)) / 2.0
    product = 4.0 * (c[:-1] - eta[:-1]) * (c[:-1] - eta[1:])
    if two_day:
        return float(np.sqrt(np.maximum(product, 0.0)).mean())
    return math.sqrt(max(float(product.mean()), 0.0))


def simulate_daily(
    days: int, sigma: float, spread: float, trades_per_day: int = 390, seed: int = 0
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Daily high, low, close from a random walk observed through a bid-ask bounce.

    The efficient log price is a Gaussian random walk with daily volatility ``sigma``, moving
    only while the market is open. Each of ``trades_per_day`` trades prints at the efficient
    price times ``1 + spread / 2`` or ``1 - spread / 2`` with equal probability. This is the
    model all three estimators assume.
    """
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, sigma / math.sqrt(trades_per_day), size=(days, trades_per_day))
    efficient = np.exp(np.cumsum(steps.ravel())).reshape(days, trades_per_day)
    side = rng.choice(np.array([-1.0, 1.0]), size=(days, trades_per_day))
    traded = efficient * (1.0 + side * spread / 2.0)
    high: FloatArray = traded.max(axis=1)
    low: FloatArray = traded.min(axis=1)
    close: FloatArray = traded[:, -1]
    return high, low, close
