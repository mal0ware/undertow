"""A small synthetic tape for tests and for running the pipeline without any download.

It is a toy queue model, not a model of a real market. The best bid and ask sit one tick
apart. Limit orders add to a queue, cancels and market orders take from it, and when a queue
empties the price moves one tick in that direction. Price changes therefore come from order
flow by construction, which is what the order-flow regression should find.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from undertow.data import Bars, Trades, build_bars

FloatArray = NDArray[np.float64]


def synthetic_streams(
    seconds: int = 7200,
    events_per_second: float = 20.0,
    tick: float = 0.1,
    start_price: float = 1000.0,
    seed: int = 0,
    start_time: float = 1_700_000_000.0,
) -> dict[str, NDArray[np.float64] | NDArray[np.bool_]]:
    """Quote updates and trades from the toy queue model, as arrays."""
    rng = np.random.default_rng(seed)
    n = int(seconds * events_per_second)
    times = np.sort(rng.uniform(0.0, float(seconds), size=n)) + start_time
    kinds = rng.integers(0, 6, size=n)
    sizes = np.round(rng.exponential(1.0, size=n) + 0.01, 3)
    refills = np.round(rng.exponential(5.0, size=2 * n) + 1.0, 3)
    bid_ticks = round(start_price / tick)
    bid_qty, ask_qty = 5.0, 5.0
    refill = 0
    q_time: list[float] = []
    q_bid: list[float] = []
    q_bid_qty: list[float] = []
    q_ask: list[float] = []
    q_ask_qty: list[float] = []
    t_time: list[float] = []
    t_price: list[float] = []
    t_qty: list[float] = []
    t_buy: list[bool] = []
    for i in range(n):
        kind, size = int(kinds[i]), float(sizes[i])
        if kind == 0:
            bid_qty += size
        elif kind == 1:
            ask_qty += size
        elif kind == 2:
            bid_qty -= size
        elif kind == 3:
            ask_qty -= size
        elif kind == 4:  # market buy takes from the ask
            t_time.append(float(times[i]))
            t_price.append((bid_ticks + 1) * tick)
            t_qty.append(min(size, ask_qty))
            t_buy.append(True)
            ask_qty -= size
        else:  # market sell takes from the bid
            t_time.append(float(times[i]))
            t_price.append(bid_ticks * tick)
            t_qty.append(min(size, bid_qty))
            t_buy.append(False)
            bid_qty -= size
        if ask_qty <= 0:
            bid_ticks += 1
            ask_qty, bid_qty = float(refills[refill]), float(refills[refill + 1])
            refill += 2
        elif bid_qty <= 0:
            bid_ticks -= 1
            ask_qty, bid_qty = float(refills[refill]), float(refills[refill + 1])
            refill += 2
        q_time.append(float(times[i]))
        q_bid.append(bid_ticks * tick)
        q_bid_qty.append(bid_qty)
        q_ask.append((bid_ticks + 1) * tick)
        q_ask_qty.append(ask_qty)
    return {
        "quote_time": np.asarray(q_time),
        "bid": np.asarray(q_bid),
        "bid_qty": np.asarray(q_bid_qty),
        "ask": np.asarray(q_ask),
        "ask_qty": np.asarray(q_ask_qty),
        "trade_time": np.asarray(t_time),
        "trade_price": np.asarray(t_price),
        "trade_qty": np.asarray(t_qty),
        "trade_buy": np.asarray(t_buy, dtype=np.bool_),
    }


def synthetic_bars(
    seconds: int = 7200,
    seed: int = 0,
    tick: float = 0.1,
    start_time: float = 1_700_000_000.0,
    bar: float = 1.0,
) -> Bars:
    """Bars built from :func:`synthetic_streams`."""
    s = synthetic_streams(seconds=seconds, seed=seed, tick=tick, start_time=start_time)
    return build_bars(
        np.asarray(s["quote_time"], dtype=np.float64),
        np.asarray(s["bid"], dtype=np.float64),
        np.asarray(s["bid_qty"], dtype=np.float64),
        np.asarray(s["ask"], dtype=np.float64),
        np.asarray(s["ask_qty"], dtype=np.float64),
        np.asarray(s["trade_time"], dtype=np.float64),
        np.asarray(s["trade_price"], dtype=np.float64),
        np.asarray(s["trade_qty"], dtype=np.float64),
        np.asarray(s["trade_buy"], dtype=np.bool_),
        bar=bar,
    )


def synthetic_tape(
    seconds: int = 7200,
    seed: int = 0,
    tick: float = 0.1,
    start_time: float = 1_700_000_000.0,
    bars: tuple[float, ...] = (1.0,),
) -> tuple[list[Bars], Trades]:
    """Bars at each length in ``bars`` and the trades behind them, from one toy stream."""
    s = synthetic_streams(seconds=seconds, seed=seed, tick=tick, start_time=start_time)
    trade_time = np.asarray(s["trade_time"], dtype=np.float64)
    built = [
        build_bars(
            np.asarray(s["quote_time"], dtype=np.float64),
            np.asarray(s["bid"], dtype=np.float64),
            np.asarray(s["bid_qty"], dtype=np.float64),
            np.asarray(s["ask"], dtype=np.float64),
            np.asarray(s["ask_qty"], dtype=np.float64),
            trade_time,
            np.asarray(s["trade_price"], dtype=np.float64),
            np.asarray(s["trade_qty"], dtype=np.float64),
            np.asarray(s["trade_buy"], dtype=np.bool_),
            bar=bar,
        )
        for bar in bars
    ]
    trades = Trades(
        time_ms=np.round(trade_time * 1000.0).astype(np.int64),
        price=np.asarray(s["trade_price"], dtype=np.float64),
        qty=np.asarray(s["trade_qty"], dtype=np.float64),
        buy=np.asarray(s["trade_buy"], dtype=np.bool_),
    )
    return built, trades
