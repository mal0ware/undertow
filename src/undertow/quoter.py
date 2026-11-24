"""The Avellaneda-Stoikov quoter: the formulas, the paper's own simulation, and a tape replay.

Equation numbers are those of the published article (Quantitative Finance 8(3), 2008).

The tape replay is a simulation with stated fill assumptions, not a backtest of anything that
could be traded. The simulated quoter never moves the market and its orders never rest in a
real queue.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


def reservation_price(s: float, q: float, gamma: float, sigma: float, tau: float) -> float:
    """Eq. (29): r = s - q * gamma * sigma^2 * (T - t)."""
    return s - q * gamma * sigma**2 * tau


def optimal_spread(gamma: float, sigma: float, tau: float, k: float) -> float:
    """Eq. (30): delta_a + delta_b = gamma sigma^2 (T - t) + (2 / gamma) ln(1 + gamma / k)."""
    return gamma * sigma**2 * tau + (2.0 / gamma) * math.log1p(gamma / k)


def intensity(delta: FloatArray | float, a: float, k: float) -> FloatArray:
    """Eq. (12): lambda(delta) = A exp(-k delta)."""
    return np.asarray(a * np.exp(-k * np.asarray(delta, dtype=np.float64)))


@dataclass(frozen=True)
class PaperRun:
    """Summary of the paper's Monte Carlo for one strategy, as in its tables 1 to 3."""

    spread: float
    profit_mean: float
    profit_std: float
    q_mean: float
    q_std: float


def simulate_paper(
    gamma: float,
    inventory: bool,
    paths: int = 1000,
    seed: int = 0,
    s0: float = 100.0,
    horizon: float = 1.0,
    sigma: float = 2.0,
    dt: float = 0.005,
    k: float = 1.5,
    a: float = 140.0,
) -> PaperRun:
    """The simulation of section 3.3 with the paper's parameters as defaults.

    At each step the quotes are set from the current state. With probability
    ``lambda(delta) * dt`` the ask is hit (inventory down one, cash up ``s + delta_a``) and the
    same on the bid. The mid then moves by ``+sigma * sqrt(dt)`` or ``-sigma * sqrt(dt)`` with
    equal probability. The inventory strategy centres the spread of eq. (30) on the reservation
    price. The symmetric strategy centres a constant spread, the time average of the inventory
    strategy's, on the mid.
    """
    rng = np.random.default_rng(seed)
    steps = round(horizon / dt)
    mid = np.full(paths, s0)
    cash = np.zeros(paths)
    q = np.zeros(paths)
    average_spread = gamma * sigma**2 * horizon / 2.0 + (2.0 / gamma) * math.log1p(gamma / k)
    for step in range(steps):
        tau = horizon - step * dt
        if inventory:
            centre = mid - q * gamma * sigma**2 * tau
            half = optimal_spread(gamma, sigma, tau, k) / 2.0
        else:
            centre = mid
            half = average_spread / 2.0
        delta_a = centre + half - mid
        delta_b = mid - (centre - half)
        sold = rng.random(paths) < np.minimum(a * np.exp(-k * delta_a) * dt, 1.0)
        bought = rng.random(paths) < np.minimum(a * np.exp(-k * delta_b) * dt, 1.0)
        cash += sold * (mid + delta_a) - bought * (mid - delta_b)
        q += bought.astype(np.float64) - sold.astype(np.float64)
        mid = mid + np.where(rng.random(paths) < 0.5, 1.0, -1.0) * sigma * math.sqrt(dt)
    profit = cash + q * mid
    return PaperRun(
        spread=average_spread,
        profit_mean=float(profit.mean()),
        profit_std=float(profit.std(ddof=1)),
        q_mean=float(q.mean()),
        q_std=float(q.std(ddof=1)),
    )


@dataclass(frozen=True)
class Calibration:
    """Fill intensity lambda(delta) = A exp(-k delta) and volatility, measured from bars."""

    a: float
    k: float
    r2: float
    sigma: float
    delta: FloatArray
    rate: FloatArray


def calibrate(
    mid: FloatArray,
    max_buy: FloatArray,
    min_sell: FloatArray,
    valid: NDArray[np.bool_],
    tick: float,
    levels: int = 51,
) -> Calibration:
    """Estimate A, k and sigma from one-second bars.

    For each distance ``delta`` on a grid of ``levels`` points from half a tick upward in steps
    of one tick, count the share ``p`` of seconds in which a trade printed at least ``delta``
    beyond the mid of the second before. Under Poisson arrivals the rate per second is
    ``-ln(1 - p)``. The two sides are averaged. ``A`` and ``k`` come from a least-squares line
    through ``ln(rate)`` against ``delta``. ``sigma`` is the standard deviation of one-second
    mid changes in price units.
    """
    ok = valid[:-1] & valid[1:]
    base = mid[:-1][ok]
    up = max_buy[1:][ok] - base
    down = base - min_sell[1:][ok]
    delta = (tick / 2.0 + tick * np.arange(levels)).astype(np.float64)
    p = np.array([(np.mean(up >= d - 1e-9) + np.mean(down >= d - 1e-9)) / 2.0 for d in delta])
    use = (p > 0) & (p < 1)
    rate = np.full(levels, np.nan)
    rate[use] = -np.log1p(-p[use])
    x, y = delta[use], np.log(rate[use])
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    r2 = 1.0 - float(((y - fitted) ** 2).sum()) / float(((y - y.mean()) ** 2).sum())
    sigma = float(np.std(np.diff(mid)[ok], ddof=1))
    return Calibration(
        a=float(np.exp(intercept)), k=float(-slope), r2=r2, sigma=sigma, delta=delta, rate=rate
    )


class TradeLadder:
    """Taker volume in each bar, by price, for sizing fills.

    Built from signed trades and a bar grid. For bar ``i`` it answers how much buyer-initiated
    volume printed at or above a price, and how much seller-initiated volume printed at or below
    one. Trades outside the grid are dropped.
    """

    def __init__(
        self,
        time_ms: NDArray[np.int64],
        price: FloatArray,
        qty: FloatArray,
        buy: NDArray[np.bool_],
        start: int,
        bar: float,
        n: int,
    ) -> None:
        bar_ms = round(bar * 1000)
        index = np.asarray(time_ms, dtype=np.int64) // bar_ms - start
        keep = (index >= 0) & (index < n)
        self.n = n
        self._buy = self._side(index[keep & buy], price[keep & buy], qty[keep & buy], n)
        self._sell = self._side(index[keep & ~buy], price[keep & ~buy], qty[keep & ~buy], n)

    @staticmethod
    def _side(
        index: NDArray[np.int64], price: FloatArray, qty: FloatArray, n: int
    ) -> tuple[NDArray[np.int64], FloatArray, FloatArray]:
        order = np.lexsort((price, index))
        index, price, qty = index[order], price[order], qty[order]
        offsets = np.searchsorted(index, np.arange(n + 1)).astype(np.int64)
        cum = np.concatenate([[0.0], np.cumsum(qty)])
        return offsets, np.ascontiguousarray(price), cum

    def bought_at_or_above(self, i: int, price: float) -> float:
        """Buyer-initiated volume in bar ``i`` at prices >= ``price``."""
        offsets, prices, cum = self._buy
        lo, hi = int(offsets[i]), int(offsets[i + 1])
        j = lo + int(np.searchsorted(prices[lo:hi], price, side="left"))
        return float(cum[hi] - cum[j])

    def sold_at_or_below(self, i: int, price: float) -> float:
        """Seller-initiated volume in bar ``i`` at prices <= ``price``."""
        offsets, prices, cum = self._sell
        lo, hi = int(offsets[i]), int(offsets[i + 1])
        j = lo + int(np.searchsorted(prices[lo:hi], price, side="right"))
        return float(cum[j] - cum[lo])


@dataclass(frozen=True)
class TapeRun:
    """Result of replaying a quoter over bars.

    Money is per unit of quote size when fills are full size. With a :class:`TradeLadder` the
    quote is ``size`` units and fills can be partial. ``spread_earned + inventory_pnl`` equals
    the mark-to-mid profit before fees exactly. ``step_pnl[i]`` is the part of it earned
    between bar ``i`` and bar ``i + 1``.
    """

    spread_earned: float
    inventory_pnl: float
    fills: int
    filled: float
    traded_notional: float
    mean_quoted_spread: float
    q_final: float
    q_abs_max: float
    q_std: float
    seconds: int
    step_pnl: FloatArray

    @property
    def pnl(self) -> float:
        return self.spread_earned + self.inventory_pnl

    def pnl_after_fee(self, fee_rate: float) -> float:
        """Profit after a proportional fee charged on the notional of every fill."""
        return self.pnl - fee_rate * self.traded_notional


def simulate_tape(
    bid: FloatArray,
    ask: FloatArray,
    max_buy: FloatArray,
    min_sell: FloatArray,
    valid: NDArray[np.bool_],
    gamma: float,
    sigma: float,
    tau: float,
    k: float,
    tick: float,
    inventory: bool = True,
    kind: bool = True,
    ladder: TradeLadder | None = None,
    size: float = 1.0,
) -> TapeRun:
    """Replay the quoter over one-second bars.

    At the end of second ``i`` the quoter sees the best bid and ask and its own inventory
    ``q``. It sets one bid and one ask of unit size, good for second ``i + 1`` only:

    * centre: the reservation price ``mid - q gamma sigma^2 tau`` (or the mid when
      ``inventory`` is False);
    * width: eq. (30) with a constant time to horizon ``tau``;
    * the ask is rounded up and the bid down to the tick, and neither may cross the opposite
      best quote (post only).

    Fill assumptions, per side, at most one fill per second:

    * kind: the ask fills if any buyer-initiated trade in the next second printed at or above
      it. This is a quote at the front of its queue.
    * unkind: the ask fills only if such a trade printed strictly above it, so every order at
      that price was filled first. This is a quote at the back of its queue.

    Fill size. Without a ladder every fill is one whole unit, whatever the size of the trades
    that caused it. With a ladder the quote is ``size`` and a fill is capped by the taker
    volume that printed at prices the rule counts: at or through the quote under the kind
    rule, strictly through it under the unkind rule. The bid is treated the same way.

    Accounting: with ``m`` the mid, a fill at the ask earns ``ask - m_i`` of spread and a fill
    at the bid earns ``m_i - bid``. Inventory after the fills earns ``q_{i+1} (m_{i+1} - m_i)``.
    The two sum to the change in ``cash + q * m`` exactly. A fill and the adverse move that
    caused it land in the same second, so the cost of being picked off is in the inventory
    term. Seconds flagged invalid are not quoted.
    """
    n = len(bid)
    mid = (bid + ask) / 2.0
    skew = gamma * sigma**2 * tau if inventory else 0.0
    half = optimal_spread(gamma, sigma, tau, k) / 2.0
    eps = tick * 1e-6
    q = 0.0
    spread_earned = 0.0
    inventory_pnl = 0.0
    notional = 0.0
    fills = 0
    quoted = 0.0
    quoted_n = 0
    q_sum = 0.0
    q_sq = 0.0
    q_abs_max = 0.0
    filled = 0.0
    step_pnl = np.zeros(max(n - 1, 0))
    bid_l: list[float] = bid.tolist()
    ask_l: list[float] = ask.tolist()
    mid_l: list[float] = mid.tolist()
    max_buy_l: list[float] = max_buy.tolist()
    min_sell_l: list[float] = min_sell.tolist()
    valid_l: list[bool] = valid.tolist()
    for i in range(n - 1):
        m = mid_l[i]
        earned = 0.0
        if valid_l[i] and valid_l[i + 1]:
            centre = m - q * skew
            my_ask = math.ceil((centre + half) / tick - 1e-9) * tick
            my_bid = math.floor((centre - half) / tick + 1e-9) * tick
            my_ask = max(my_ask, bid_l[i] + tick)
            my_bid = min(my_bid, ask_l[i] - tick)
            quoted += my_ask - my_bid
            quoted_n += 1
            top = max_buy_l[i + 1]
            bottom = min_sell_l[i + 1]
            sold = top >= my_ask - eps if kind else top > my_ask + eps
            bought = bottom <= my_bid + eps if kind else bottom < my_bid - eps
            sell_size = buy_size = 1.0
            if ladder is not None:
                if sold:
                    edge = my_ask - eps if kind else my_ask + eps
                    sell_size = min(size, ladder.bought_at_or_above(i + 1, edge))
                    sold = sell_size > 0
                if bought:
                    edge = my_bid + eps if kind else my_bid - eps
                    buy_size = min(size, ladder.sold_at_or_below(i + 1, edge))
                    bought = buy_size > 0
            if sold:
                q -= sell_size
                earned += sell_size * (my_ask - m)
                notional += sell_size * my_ask
                filled += sell_size
                fills += 1
            if bought:
                q += buy_size
                earned += buy_size * (m - my_bid)
                notional += buy_size * my_bid
                filled += buy_size
                fills += 1
        spread_earned += earned
        held = q * (mid_l[i + 1] - m)
        inventory_pnl += held
        step_pnl[i] = earned + held
        q_sum += q
        q_sq += q * q
        q_abs_max = max(q_abs_max, abs(q))
    steps = max(n - 1, 1)
    variance = max(q_sq / steps - (q_sum / steps) ** 2, 0.0)
    return TapeRun(
        spread_earned=spread_earned,
        inventory_pnl=inventory_pnl,
        fills=fills,
        filled=filled,
        traded_notional=notional,
        mean_quoted_spread=quoted / max(quoted_n, 1),
        q_final=q,
        q_abs_max=q_abs_max,
        q_std=math.sqrt(variance),
        seconds=quoted_n,
        step_pnl=step_pnl,
    )
