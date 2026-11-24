"""The quoter: formulas against the paper, its simulation against its tables, tape accounting."""

from __future__ import annotations

import math

import numpy as np
import pytest

from undertow import quoter

A = np.asarray


def test_reservation_price_formula() -> None:
    # eq. (29) with the paper's parameters: sigma = 2, gamma = 0.1, T - t = 1
    assert quoter.reservation_price(100.0, 0.0, 0.1, 2.0, 1.0) == 100.0
    assert quoter.reservation_price(100.0, 3.0, 0.1, 2.0, 1.0) == pytest.approx(98.8)
    assert quoter.reservation_price(100.0, -3.0, 0.1, 2.0, 1.0) == pytest.approx(101.2)
    # the skew dies out at the horizon
    assert quoter.reservation_price(100.0, 3.0, 0.1, 2.0, 0.0) == 100.0


def test_reservation_bid_and_ask_average_to_the_reservation_price() -> None:
    # eqs. (6) and (7): r_a = s + (1 - 2q) g s2 tau / 2, r_b = s + (-1 - 2q) g s2 tau / 2
    s, q, g, sigma, tau = 100.0, 2.0, 0.1, 2.0, 0.6
    ra = s + (1 - 2 * q) * g * sigma**2 * tau / 2
    rb = s + (-1 - 2 * q) * g * sigma**2 * tau / 2
    assert (ra + rb) / 2 == pytest.approx(quoter.reservation_price(s, q, g, sigma, tau))


@pytest.mark.parametrize(("gamma", "published"), [(0.1, 1.49), (0.01, 1.35), (1.0, 3.02)])
def test_average_spread_matches_published_tables(gamma: float, published: float) -> None:
    # the tables report the average of eq. (30) over the session: tau averages to T / 2
    assert quoter.optimal_spread(gamma, 2.0, 0.5, 1.5) == pytest.approx(published, abs=0.006)


def test_spread_limits() -> None:
    # as gamma -> 0 the spread tends to 2 / k, the risk-neutral quote
    assert quoter.optimal_spread(1e-9, 2.0, 1.0, 1.5) == pytest.approx(2 / 1.5, rel=1e-6)
    # at the horizon only the intensity term is left
    assert quoter.optimal_spread(0.1, 2.0, 0.0, 1.5) == pytest.approx(20 * math.log(1 + 0.1 / 1.5))
    assert quoter.optimal_spread(0.1, 3.0, 1.0, 1.5) > quoter.optimal_spread(0.1, 2.0, 1.0, 1.5)


def test_intensity() -> None:
    assert quoter.intensity(0.0, 140.0, 1.5) == pytest.approx(140.0)
    assert quoter.intensity(A([1.0, 2.0]), 140.0, 1.5) == pytest.approx(
        [140 * math.exp(-1.5), 140 * math.exp(-3.0)]
    )


def test_paper_simulation_reproduces_table_1() -> None:
    inventory = quoter.simulate_paper(0.1, True, paths=4000, seed=1)
    symmetric = quoter.simulate_paper(0.1, False, paths=4000, seed=1)
    # published: inventory 65.0 (6.6), final q std 2.9; symmetric 68.4 (12.7), final q std 8.4
    assert inventory.spread == pytest.approx(1.49, abs=0.005)
    assert inventory.profit_mean == pytest.approx(65.0, abs=0.6)
    assert inventory.profit_std == pytest.approx(6.6, abs=0.5)
    assert inventory.q_std == pytest.approx(2.9, abs=0.25)
    assert symmetric.profit_mean == pytest.approx(68.4, abs=0.9)
    assert symmetric.profit_std == pytest.approx(12.7, abs=0.9)
    assert symmetric.q_std == pytest.approx(8.4, abs=0.6)
    assert abs(inventory.q_mean) < 0.3


def test_paper_simulation_is_seeded() -> None:
    assert quoter.simulate_paper(0.1, True, paths=50, seed=3) == quoter.simulate_paper(
        0.1, True, paths=50, seed=3
    )
    assert quoter.simulate_paper(0.1, True, paths=50, seed=3) != quoter.simulate_paper(
        0.1, True, paths=50, seed=4
    )


def test_calibrate_recovers_an_exponential_fill_rate() -> None:
    rng = np.random.default_rng(0)
    n, a, k, tick = 200_000, 0.8, 1.2, 0.1
    mid = np.full(n, 100.0)
    # largest excursion each second: exponential with rate k, present with the right frequency
    # so that P(excursion >= d) = 1 - exp(-a exp(-k d)) is matched in the tail
    u = rng.random((2, n))
    reach = -np.log(-np.log1p(-u) / a) / k  # invert the Poisson survival function
    max_buy = np.where(np.isfinite(reach[0]), 100.0 + reach[0], -np.inf)
    min_sell = np.where(np.isfinite(reach[1]), 100.0 - reach[1], np.inf)
    cal = quoter.calibrate(mid, max_buy, min_sell, np.ones(n, dtype=np.bool_), tick, levels=20)
    assert cal.k == pytest.approx(k, rel=0.03)
    assert cal.a == pytest.approx(a, rel=0.03)
    assert cal.r2 > 0.995
    assert cal.sigma == 0.0


def test_calibrate_sigma_and_validity_mask() -> None:
    rng = np.random.default_rng(1)
    n = 50_000
    mid = 100.0 + np.cumsum(rng.normal(0, 0.25, n))
    max_buy = mid + rng.exponential(0.5, n)
    min_sell = mid - rng.exponential(0.5, n)
    valid = np.ones(n, dtype=np.bool_)
    cal = quoter.calibrate(mid, max_buy, min_sell, valid, 0.1)
    assert cal.sigma == pytest.approx(0.25, rel=0.02)
    mid[1000] += 500.0  # a wild value in a second flagged invalid must not leak in
    valid[1000] = False
    assert quoter.calibrate(mid, max_buy, min_sell, valid, 0.1).sigma == pytest.approx(
        0.25, rel=0.02
    )


# ---------------------------------------------------------------- tape replay

PARAMS = {"gamma": 0.1, "sigma": 1.0, "tau": 1.0, "k": 5.0, "tick": 0.1}


def tape(
    mids: list[float], buys: list[float], sells: list[float]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mid = A(mids, dtype=np.float64)
    return (
        mid - 0.05,
        mid + 0.05,
        A(buys, dtype=np.float64),
        A(sells, dtype=np.float64),
        np.ones(len(mid), dtype=np.bool_),
    )


NONE_UP, NONE_DOWN = -np.inf, np.inf


def test_quotes_by_hand_and_a_round_trip_earns_the_spread() -> None:
    # spread: 0.1 * 1 * 1 + 20 ln(1.02) = 0.496; half 0.248; ask rounds up to 100.3, bid to 99.7
    mids = [100.0, 100.0, 100.0, 100.0]
    run = quoter.simulate_tape(
        *tape(mids, [NONE_UP, 100.3, NONE_UP, NONE_UP], [NONE_DOWN, NONE_DOWN, 99.8, NONE_DOWN]),
        **PARAMS,
        inventory=False,
    )
    # second 1: a buy prints at 100.3 and lifts the ask. second 2: a sell at 99.8 misses the bid.
    assert run.fills == 1
    assert run.q_final == -1.0
    assert run.spread_earned == pytest.approx(0.3)
    assert run.inventory_pnl == pytest.approx(0.0)
    assert run.mean_quoted_spread == pytest.approx(0.6)
    assert run.traded_notional == pytest.approx(100.3)
    assert run.seconds == 3


def test_inventory_skew_moves_both_quotes_against_the_position() -> None:
    # after selling one, q = -1 and the centre rises by gamma sigma^2 tau = 0.1:
    # ask ceil(100.348) = 100.4, bid floor(99.852) = 99.8, so the 99.8 sell now fills the bid
    mids = [100.0, 100.0, 100.0, 100.0]
    run = quoter.simulate_tape(
        *tape(mids, [NONE_UP, 100.3, NONE_UP, NONE_UP], [NONE_DOWN, NONE_DOWN, 99.8, NONE_DOWN]),
        **PARAMS,
        inventory=True,
    )
    assert run.fills == 2
    assert run.q_final == 0.0
    assert run.spread_earned == pytest.approx(0.3 + 0.2)
    assert run.pnl == pytest.approx(0.5)


def test_unkind_rule_needs_a_trade_through() -> None:
    mids = [100.0, 100.0, 100.0]
    at = tape(mids, [NONE_UP, 100.3, NONE_UP], [NONE_DOWN] * 3)
    through = tape(mids, [NONE_UP, 100.4, NONE_UP], [NONE_DOWN] * 3)
    assert quoter.simulate_tape(*at, **PARAMS, inventory=False, kind=True).fills == 1
    assert quoter.simulate_tape(*at, **PARAMS, inventory=False, kind=False).fills == 0
    assert quoter.simulate_tape(*through, **PARAMS, inventory=False, kind=False).fills == 1


def test_adverse_fill_is_charged_to_inventory() -> None:
    # the price jumps 1.0 through the ask: the fill earns 0.3 of spread and loses 1.0 on the move
    run = quoter.simulate_tape(
        *tape([100.0, 101.0], [NONE_UP, 101.05], [NONE_DOWN, NONE_DOWN]),
        **PARAMS,
        inventory=False,
    )
    assert run.fills == 1
    assert run.spread_earned == pytest.approx(0.3)
    assert run.inventory_pnl == pytest.approx(-1.0)
    assert run.pnl == pytest.approx(-0.7)
    assert run.pnl_after_fee(0.001) == pytest.approx(-0.7 - 0.1003)


def test_invalid_seconds_are_not_quoted_but_inventory_is_still_marked() -> None:
    bid, ask, buys, sells, valid = tape(
        [100.0, 100.0, 100.0, 101.0], [NONE_UP, 100.3, 100.3, 100.3], [NONE_DOWN] * 4
    )
    valid[2] = False
    run = quoter.simulate_tape(bid, ask, buys, sells, valid, **PARAMS, inventory=False)
    # only the first second is quoted: seconds 1->2 and 2->3 touch the invalid one
    assert run.seconds == 1
    assert run.fills == 1
    assert run.inventory_pnl == pytest.approx(-1.0)


def test_post_only_clamp() -> None:
    # sigma = 10 makes the skew 10 per unit of inventory and the spread 10.396.
    # flat: ask ceil(105.248) = 105.3, bid floor(94.852) = 94.8. A sell at 94.8 fills the bid.
    # long one: the centre drops to 90.05 and the ask would be 95.3, far below the market.
    # It is held at the best bid plus one tick, 100.1, and a buy at 100.1 fills it there.
    run = quoter.simulate_tape(
        *tape([100.05, 100.05, 100.05], [NONE_UP, NONE_UP, 100.1], [NONE_DOWN, 94.8, NONE_DOWN]),
        **{**PARAMS, "sigma": 10.0},
        inventory=True,
    )
    assert run.fills == 2
    assert run.traded_notional == pytest.approx(94.8 + 100.1)
    assert run.spread_earned == pytest.approx(5.25 + 0.05)
    assert run.q_final == 0.0


def test_accounting_identity_on_a_random_tape() -> None:
    rng = np.random.default_rng(5)
    n = 5000
    mid = 100.0 + np.round(np.cumsum(rng.normal(0, 0.2, n)), 1) + 0.05
    bid, ask = mid - 0.05, mid + 0.05
    max_buy = np.where(rng.random(n) < 0.6, ask + np.round(rng.exponential(0.3, n), 1), -np.inf)
    min_sell = np.where(rng.random(n) < 0.6, bid - np.round(rng.exponential(0.3, n), 1), np.inf)
    valid = rng.random(n) > 0.01
    for inventory in (True, False):
        for kind in (True, False):
            run = quoter.simulate_tape(
                bid, ask, max_buy, min_sell, valid, **PARAMS, inventory=inventory, kind=kind
            )
            cash, q = _cash_and_inventory(bid, ask, max_buy, min_sell, valid, inventory, kind)
            assert run.q_final == q
            assert run.pnl == pytest.approx(cash + q * mid[-1], abs=1e-6)
            assert run.spread_earned >= 0
            assert run.fills > 100
    kind_run = quoter.simulate_tape(bid, ask, max_buy, min_sell, valid, **PARAMS, inventory=False)
    unkind_run = quoter.simulate_tape(
        bid, ask, max_buy, min_sell, valid, **PARAMS, inventory=False, kind=False
    )
    assert unkind_run.fills < kind_run.fills


def _cash_and_inventory(
    bid: np.ndarray,
    ask: np.ndarray,
    max_buy: np.ndarray,
    min_sell: np.ndarray,
    valid: np.ndarray,
    inventory: bool,
    kind: bool,
) -> tuple[float, float]:
    """Plain cash-and-position bookkeeping, written separately from the simulator."""
    g, sigma, tau, k, tick = (PARAMS[name] for name in ("gamma", "sigma", "tau", "k", "tick"))
    half = (g * sigma**2 * tau + (2 / g) * math.log(1 + g / k)) / 2
    cash, q = 0.0, 0.0
    for i in range(len(bid) - 1):
        if not (valid[i] and valid[i + 1]):
            continue
        mid = (bid[i] + ask[i]) / 2
        centre = mid - (q * g * sigma**2 * tau if inventory else 0.0)
        my_ask = max(round(math.ceil(round((centre + half) / tick, 6))) * tick, bid[i] + tick)
        my_bid = min(round(math.floor(round((centre - half) / tick, 6))) * tick, ask[i] - tick)
        sold = max_buy[i + 1] >= my_ask - 1e-7 if kind else max_buy[i + 1] > my_ask + 1e-7
        bought = min_sell[i + 1] <= my_bid + 1e-7 if kind else min_sell[i + 1] < my_bid - 1e-7
        if sold:
            cash += my_ask
            q -= 1
        if bought:
            cash -= my_bid
            q += 1
    return cash - 0.0, q


# ---------------------------------------------------------------- fill size from traded volume


def ladder(
    times_ms: list[int], prices: list[float], qtys: list[float], buys: list[bool], n: int
) -> quoter.TradeLadder:
    return quoter.TradeLadder(
        A(times_ms, dtype=np.int64),
        A(prices, dtype=np.float64),
        A(qtys, dtype=np.float64),
        A(buys, dtype=np.bool_),
        start=0,
        bar=1.0,
        n=n,
    )


def test_ladder_volumes_by_hand() -> None:
    lad = ladder(
        [1500, 1200, 1900, 1100, 2500, 99_000],
        [100.4, 100.3, 99.8, 99.9, 100.3, 100.0],
        [0.5, 0.4, 2.0, 0.7, 9.0, 1.0],
        [True, True, False, False, True, True],
        n=3,
    )
    assert lad.bought_at_or_above(1, 100.3) == pytest.approx(0.9)
    assert lad.bought_at_or_above(1, 100.35) == pytest.approx(0.5)
    assert lad.bought_at_or_above(1, 100.5) == 0.0
    assert lad.bought_at_or_above(0, 0.0) == 0.0
    assert lad.bought_at_or_above(2, 100.3) == pytest.approx(9.0)
    assert lad.sold_at_or_below(1, 99.8) == pytest.approx(2.0)
    assert lad.sold_at_or_below(1, 99.9) == pytest.approx(2.7)
    assert lad.sold_at_or_below(1, 99.7) == 0.0
    # the trade at 99 s is outside the three-bar grid and is dropped
    assert lad.bought_at_or_above(2, 0.0) == pytest.approx(9.0)


def test_a_small_trade_gives_a_partial_fill() -> None:
    # the ask is 100.3 (see the first tape test). A buy of 0.4 at 100.3 in second 1.
    mids = [100.0, 100.0, 100.0]
    bars = tape(mids, [NONE_UP, 100.3, NONE_UP], [NONE_DOWN] * 3)
    lad = ladder([1500], [100.3], [0.4], [True], n=3)
    run = quoter.simulate_tape(*bars, **PARAMS, inventory=False, ladder=lad)
    assert run.fills == 1
    assert run.filled == pytest.approx(0.4)
    assert run.q_final == pytest.approx(-0.4)
    assert run.spread_earned == pytest.approx(0.4 * 0.3)
    assert run.traded_notional == pytest.approx(0.4 * 100.3)
    # behind the queue, a trade at the quote fills nothing
    unkind = quoter.simulate_tape(*bars, **PARAMS, inventory=False, kind=False, ladder=lad)
    assert unkind.fills == 0 and unkind.filled == 0.0
    # without the ladder the same tape fills the whole unit
    full = quoter.simulate_tape(*bars, **PARAMS, inventory=False)
    assert full.filled == 1.0 and full.fills == 1


def test_fill_is_capped_at_the_quote_size() -> None:
    mids = [100.0, 100.0, 100.0]
    bars = tape(mids, [NONE_UP, 100.4, NONE_UP], [NONE_DOWN] * 3)
    lad = ladder([1500, 1600], [100.3, 100.4], [0.4, 2.0], [True, True], n=3)
    for kind in (True, False):
        run = quoter.simulate_tape(*bars, **PARAMS, inventory=False, kind=kind, ladder=lad)
        assert run.filled == 1.0
    half = quoter.simulate_tape(*bars, **PARAMS, inventory=False, ladder=lad, size=0.5)
    assert half.filled == 0.5


def test_step_pnl_adds_up_and_traded_size_never_fills_more() -> None:
    rng = np.random.default_rng(7)
    n = 3000
    mid = 100.0 + np.round(np.cumsum(rng.normal(0, 0.2, n)), 1) + 0.05
    bid, ask = mid - 0.05, mid + 0.05
    # trades: a few per second around the touch, with random sizes
    m = 4 * n
    second = rng.integers(0, n, m)
    buy = rng.random(m) < 0.5
    away = np.round(rng.exponential(0.3, m), 1)
    price = np.where(buy, ask[second] + away, bid[second] - away)
    qty = np.round(rng.exponential(0.6, m), 3)
    max_buy = np.full(n, -np.inf)
    min_sell = np.full(n, np.inf)
    np.maximum.at(max_buy, second[buy], price[buy])
    np.minimum.at(min_sell, second[~buy], price[~buy])
    lad = quoter.TradeLadder(second * 1000 + 500, price, qty, buy, start=0, bar=1.0, n=n)
    valid = np.ones(n, dtype=np.bool_)
    for inventory in (True, False):
        for kind in (True, False):
            args = (bid, ask, max_buy, min_sell, valid)
            full = quoter.simulate_tape(*args, **PARAMS, inventory=inventory, kind=kind)
            sized = quoter.simulate_tape(
                *args, **PARAMS, inventory=inventory, kind=kind, ladder=lad
            )
            for run in (full, sized):
                assert run.step_pnl.sum() == pytest.approx(run.pnl, abs=1e-6)
                assert len(run.step_pnl) == n - 1
            assert full.filled == full.fills
            assert 0 < sized.filled < sized.fills
