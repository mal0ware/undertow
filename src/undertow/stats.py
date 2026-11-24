"""Uncertainty for averages of serially dependent series.

The window regressions give one number per window, and neighbouring windows share market
conditions, so their average is not an average of independent draws. The quoter's profit
comes in days. Both are summarised here.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def block_length(n: int) -> int:
    """Block length for :func:`block_bootstrap`: the cube root of ``n``, rounded up.

    A common rule of thumb. It was chosen once for this project and not varied, and no
    block length was estimated from the data.
    """
    root: float = math.pow(n, 1.0 / 3.0)
    return max(1, math.ceil(root - 1e-9))  # so that a perfect cube gives its exact root


def block_bootstrap(
    x: FloatArray,
    block: int | None = None,
    resamples: int = 2000,
    level: float = 0.95,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Mean of ``x`` and a percentile interval from a circular block bootstrap.

    NaN entries are dropped first, keeping the order of the rest. Each resample joins
    ``ceil(n / block)`` blocks of ``block`` consecutive values, starting at uniform random
    positions and wrapping around the end, and is cut to length ``n``. Returns
    ``(mean, low, high)``.
    """
    values = np.asarray(x, dtype=np.float64)
    values = values[np.isfinite(values)]
    n = len(values)
    if n == 0:
        nan = float("nan")
        return nan, nan, nan
    size = block if block is not None else block_length(n)
    size = min(max(size, 1), n)
    count = math.ceil(n / size)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(resamples, count))
    index = (starts[:, :, None] + np.arange(size)[None, None, :]) % n
    means = values[index.reshape(resamples, -1)[:, :n]].mean(axis=1)
    tail = (1.0 - level) / 2.0
    low, high = np.quantile(means, [tail, 1.0 - tail])
    return float(values.mean()), float(low), float(high)


def day_summary(totals: FloatArray) -> tuple[float, float, float, int]:
    """Mean of per-day totals, its standard error, the t-ratio, and the days with a profit.

    The standard error treats days as independent: ``sd / sqrt(days)`` with ``ddof = 1``.
    """
    values = np.asarray(totals, dtype=np.float64)
    days = len(values)
    mean = float(values.mean()) if days else float("nan")
    if days < 2:
        return mean, float("nan"), float("nan"), int((values > 0).sum())
    se = float(values.std(ddof=1) / math.sqrt(days))
    t = mean / se if se > 0 else float("nan")
    return mean, se, t, int((values > 0).sum())
