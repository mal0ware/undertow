"""Block bootstrap and per-day summaries."""

from __future__ import annotations

import math

import numpy as np
import pytest

from undertow import stats


def test_block_length_is_the_rounded_up_cube_root() -> None:
    assert stats.block_length(1) == 1
    assert stats.block_length(8) == 2
    assert stats.block_length(9) == 3
    assert stats.block_length(1000) == 10
    assert stats.block_length(2399) == 14


def test_bootstrap_of_a_constant_has_no_width() -> None:
    mean, low, high = stats.block_bootstrap(np.full(50, 3.0), block=5)
    assert (mean, low, high) == (3.0, 3.0, 3.0)


def test_bootstrap_drops_nan_and_handles_empty() -> None:
    mean, low, high = stats.block_bootstrap(np.array([1.0, np.nan, 3.0]), block=1, seed=1)
    assert mean == 2.0
    assert 1.0 <= low <= high <= 3.0
    assert all(math.isnan(v) for v in stats.block_bootstrap(np.array([np.nan])))


def test_bootstrap_is_seeded() -> None:
    x = np.random.default_rng(0).normal(size=200)
    assert stats.block_bootstrap(x, seed=4) == stats.block_bootstrap(x, seed=4)
    assert stats.block_bootstrap(x, seed=4) != stats.block_bootstrap(x, seed=5)


def test_iid_interval_matches_the_normal_one() -> None:
    x = np.random.default_rng(1).normal(size=4000)
    mean, low, high = stats.block_bootstrap(x, block=1, resamples=4000)
    half = 1.96 * x.std(ddof=1) / math.sqrt(len(x))
    assert low < mean < high
    assert (high - low) / 2 == pytest.approx(half, rel=0.08)


def test_blocks_widen_the_interval_for_a_persistent_series() -> None:
    rng = np.random.default_rng(2)
    e = rng.normal(size=3000)
    x = np.empty_like(e)
    x[0] = e[0]
    for i in range(1, len(e)):
        x[i] = 0.9 * x[i - 1] + e[i]
    _, low_1, high_1 = stats.block_bootstrap(x, block=1)
    _, low_b, high_b = stats.block_bootstrap(x, block=60)
    # an AR(1) with phi = 0.9 has a long-run variance 19 times the iid one; the blocks see some
    assert (high_b - low_b) > 2.5 * (high_1 - low_1)


def test_day_summary_by_hand() -> None:
    mean, se, t, positive = stats.day_summary(np.array([1.0, 2.0, 3.0, -2.0]))
    assert mean == 1.0
    assert se == pytest.approx(np.std([1.0, 2.0, 3.0, -2.0], ddof=1) / 2.0)
    assert t == pytest.approx(1.0 / se)
    assert positive == 3
    one = stats.day_summary(np.array([5.0]))
    assert one[0] == 5.0 and math.isnan(one[1]) and math.isnan(one[2]) and one[3] == 1
