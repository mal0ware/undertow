"""Loading the public files and reducing them to one-second bars.

The published results use one source: Binance USD-M futures archive files (``bookTicker``
for the best bid and ask on every change, ``aggTrades`` for signed trades, daily ``klines``
for the spread estimators).

A bar holds everything the analysis needs for one second: the order-flow imbalance summed
over the quote updates in that second, the last best bid and ask, signed trade volume, and
the highest buyer-initiated and lowest seller-initiated trade price.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from undertow.ofi import event_contributions

SYMBOL = "BTCUSDT"
DAYS = ["2024-03-25", "2024-03-26", "2024-03-27", "2024-03-28", "2024-03-29"]
KLINE_MONTHS = [
    "2023-06",
    "2023-07",
    "2023-08",
    "2023-09",
    "2023-10",
    "2023-11",
    "2023-12",
    "2024-01",
    "2024-02",
    "2024-03",
]
TICK = 0.1

FloatArray = NDArray[np.float64]


def archive_files(symbol: str, days: list[str], months: list[str]) -> list[str]:
    """Keys under data.binance.vision for the given days and kline months."""
    keys: list[str] = []
    root = "data/futures/um"
    for day in days:
        keys.append(f"{root}/daily/bookTicker/{symbol}/{symbol}-bookTicker-{day}.zip")
        keys.append(f"{root}/daily/aggTrades/{symbol}/{symbol}-aggTrades-{day}.zip")
    for month in months:
        keys.append(f"{root}/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip")
    return keys


@dataclass(frozen=True)
class Bars:
    """Bars of ``bar`` seconds each. All arrays have one entry per bar.

    ``start`` is the index of the first bar counted in bars since the Unix epoch. ``valid`` is
    False for bars that touch a known gap in the feed. ``max_buy`` is ``-inf`` and ``min_sell``
    is ``+inf`` in bars with no such trade. The order-flow analysis uses one-second bars; the
    quoter is also replayed on 100-millisecond bars.
    """

    start: int
    bar: float
    ofi: FloatArray
    bid: FloatArray
    ask: FloatArray
    depth: FloatArray
    updates: FloatArray
    buy_volume: FloatArray
    sell_volume: FloatArray
    max_buy: FloatArray
    min_sell: FloatArray
    valid: NDArray[np.bool_]

    @property
    def mid(self) -> FloatArray:
        return (self.bid + self.ask) / 2.0

    def __len__(self) -> int:
        return len(self.ofi)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **{k: getattr(self, k) for k in self.__dataclass_fields__})

    @staticmethod
    def load(path: Path) -> Bars:
        with np.load(path) as stored:
            fields: dict[str, Any] = {k: stored[k] for k in stored.files}
        fields["start"] = int(fields["start"])
        fields["bar"] = float(fields["bar"])
        return Bars(**fields)


def _last_fill(seconds: NDArray[np.int64], values: FloatArray, n: int) -> FloatArray:
    """Last value seen in each second, carried forward through empty seconds."""
    out = np.full(n, np.nan)
    out[seconds] = values  # later rows overwrite earlier ones within a second
    idx = np.where(~np.isnan(out), np.arange(n), 0)
    np.maximum.accumulate(idx, out=idx)
    return out[idx]


def build_bars(
    quote_time: FloatArray,
    bid: FloatArray,
    bid_qty: FloatArray,
    ask: FloatArray,
    ask_qty: FloatArray,
    trade_time: FloatArray,
    trade_price: FloatArray,
    trade_qty: FloatArray,
    trade_buy: NDArray[np.bool_],
    bar: float = 1.0,
) -> Bars:
    """Reduce a quote stream and a trade stream to bars of ``bar`` seconds.

    Times are Unix seconds and are rounded to the millisecond. ``bar`` must be a whole number
    of milliseconds. Quotes must be in time order. Every bar is flagged valid; bars that
    fill a hole between two joined stretches are flagged invalid by :func:`concat_bars`.
    """
    bar_ms = round(bar * 1000)

    def index(times: FloatArray) -> NDArray[np.int64]:
        return np.round(times * 1000.0).astype(np.int64) // bar_ms

    if len(quote_time) == 0:
        raise ValueError("no quotes")
    if np.any(np.diff(quote_time) < 0):
        raise ValueError("quotes are not in time order")
    sec = index(quote_time)
    start = int(sec[0])
    n = int(sec[-1]) - start + 1
    sec = sec - start

    e = event_contributions(bid, bid_qty, ask, ask_qty)
    ofi = np.bincount(sec, weights=e, minlength=n)
    updates = np.bincount(sec, minlength=n).astype(np.float64)
    depth_sum = np.bincount(sec, weights=(bid_qty + ask_qty) / 2.0, minlength=n)
    last_bid = _last_fill(sec, bid, n)
    last_ask = _last_fill(sec, ask, n)
    last_depth = _last_fill(sec, (bid_qty + ask_qty) / 2.0, n)
    depth = np.where(updates > 0, depth_sum / np.maximum(updates, 1.0), last_depth)

    buy_volume = np.zeros(n)
    sell_volume = np.zeros(n)
    max_buy = np.full(n, -np.inf)
    min_sell = np.full(n, np.inf)
    tsec = index(trade_time) - start
    keep = (tsec >= 0) & (tsec < n)
    tsec, price, qty, buy = tsec[keep], trade_price[keep], trade_qty[keep], trade_buy[keep]
    buy_volume += np.bincount(tsec[buy], weights=qty[buy], minlength=n)
    sell_volume += np.bincount(tsec[~buy], weights=qty[~buy], minlength=n)
    np.maximum.at(max_buy, tsec[buy], price[buy])
    np.minimum.at(min_sell, tsec[~buy], price[~buy])

    valid = np.ones(n, dtype=np.bool_)
    return Bars(
        start=start,
        bar=bar,
        ofi=ofi,
        bid=last_bid,
        ask=last_ask,
        depth=depth,
        updates=updates,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        max_buy=max_buy,
        min_sell=min_sell,
        valid=valid,
    )


def _read_zip_csv(path: Path, columns: list[str], nrows: int | None) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive, archive.open(archive.namelist()[0]) as handle:
        head = handle.readline().decode("ascii", "replace")
    has_header = not head.split(",")[0].strip().lstrip("-").replace(".", "").isdigit()
    with zipfile.ZipFile(path) as archive, archive.open(archive.namelist()[0]) as handle:
        return pd.read_csv(
            handle,
            header=0 if has_header else None,
            names=columns,
            nrows=nrows,
        )


BOOK_TICKER_COLUMNS = [
    "update_id",
    "best_bid_price",
    "best_bid_qty",
    "best_ask_price",
    "best_ask_qty",
    "transaction_time",
    "event_time",
]
AGG_TRADE_COLUMNS = [
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
]
KLINE_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "count",
    "taker_buy_volume",
    "taker_buy_quote_volume",
    "ignore",
]


@dataclass(frozen=True)
class Trades:
    """Signed trades, one entry per archive ``aggTrades`` row, in time order.

    ``time_ms`` is the exchange's transaction time in Unix milliseconds. ``buy`` is True for a
    buyer-initiated trade. The quoter replay uses these to size fills by traded quantity.
    """

    time_ms: NDArray[np.int64]
    price: FloatArray
    qty: FloatArray
    buy: NDArray[np.bool_]

    def __len__(self) -> int:
        return len(self.price)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **{k: getattr(self, k) for k in self.__dataclass_fields__})

    @staticmethod
    def load(path: Path) -> Trades:
        with np.load(path) as stored:
            return Trades(**{k: stored[k] for k in stored.files})

    @staticmethod
    def concat(parts: list[Trades]) -> Trades:
        return Trades(
            time_ms=np.concatenate([p.time_ms for p in parts]),
            price=np.concatenate([p.price for p in parts]),
            qty=np.concatenate([p.qty for p in parts]),
            buy=np.concatenate([p.buy for p in parts]),
        )


def load_binance_trades(raw: Path, symbol: str, day: str) -> Trades:
    """Signed trades for one archive day. A buyer-initiated trade is one where the buyer was
    not the maker."""
    trades = _read_zip_csv(raw / f"{symbol}-aggTrades-{day}.zip", AGG_TRADE_COLUMNS, None)
    trades = trades.sort_values(["transact_time", "agg_trade_id"], kind="stable")
    maker = trades["is_buyer_maker"]
    buyer_is_maker = (
        maker.to_numpy(dtype=np.bool_)
        if maker.dtype == bool
        else maker.astype(str).str.lower().eq("true").to_numpy(dtype=np.bool_)
    )
    return Trades(
        time_ms=trades["transact_time"].to_numpy(dtype=np.int64),
        price=trades["price"].to_numpy(dtype=np.float64),
        qty=trades["quantity"].to_numpy(dtype=np.float64),
        buy=~buyer_is_maker,
    )


def load_binance_day(
    raw: Path, symbol: str, day: str, nrows: int | None = None, bars: tuple[float, ...] = (1.0,)
) -> list[Bars]:
    """Bars for one archive day, one set per bar length in ``bars``.

    ``nrows`` limits the quote rows read (fast mode). Times are the exchange's transaction
    times in milliseconds.
    """
    quotes = _read_zip_csv(raw / f"{symbol}-bookTicker-{day}.zip", BOOK_TICKER_COLUMNS, nrows)
    quotes = quotes.sort_values(["transaction_time", "update_id"], kind="stable")
    trades = load_binance_trades(raw, symbol, day)
    quote_time = quotes["transaction_time"].to_numpy(dtype=np.float64) / 1000.0
    trade_time = trades.time_ms.astype(np.float64) / 1000.0
    return [
        build_bars(
            quote_time,
            quotes["best_bid_price"].to_numpy(dtype=np.float64),
            quotes["best_bid_qty"].to_numpy(dtype=np.float64),
            quotes["best_ask_price"].to_numpy(dtype=np.float64),
            quotes["best_ask_qty"].to_numpy(dtype=np.float64),
            trade_time,
            trades.price,
            trades.qty,
            trades.buy,
            bar=bar,
        )
        for bar in bars
    ]


def load_klines(raw: Path, symbol: str, months: list[str]) -> pd.DataFrame:
    """Daily open, high, low, close for the given months, in date order."""
    frames = [_read_zip_csv(raw / f"{symbol}-1d-{m}.zip", KLINE_COLUMNS, None) for m in months]
    table = pd.concat(frames, ignore_index=True).sort_values("open_time")
    table["date"] = pd.to_datetime(table["open_time"], unit="ms").dt.strftime("%Y-%m-%d")
    return table[["date", "open", "high", "low", "close"]].reset_index(drop=True)


def concat_bars(parts: list[Bars]) -> Bars:
    """Join bars from consecutive stretches into one series on a common grid.

    Bars between the end of one part and the start of the next are filled with the last
    quote and flagged invalid.
    """
    if not parts:
        raise ValueError("nothing to join")
    start = parts[0].start
    n = parts[-1].start + len(parts[-1]) - start
    arrays: dict[str, Any] = {
        "ofi": np.zeros(n),
        "bid": np.full(n, np.nan),
        "ask": np.full(n, np.nan),
        "depth": np.full(n, np.nan),
        "updates": np.zeros(n),
        "buy_volume": np.zeros(n),
        "sell_volume": np.zeros(n),
        "max_buy": np.full(n, -np.inf),
        "min_sell": np.full(n, np.inf),
        "valid": np.zeros(n, dtype=np.bool_),
    }
    end = start
    for part in parts:
        offset = part.start - start
        if offset < end - start:
            raise ValueError("parts overlap or are out of order")
        for name, target in arrays.items():
            target[offset : offset + len(part)] = getattr(part, name)
        end = part.start + len(part)
    for name in ("bid", "ask", "depth"):
        values = arrays[name]
        idx = np.where(~np.isnan(values), np.arange(n), 0)
        np.maximum.accumulate(idx, out=idx)
        arrays[name] = values[idx]
    return Bars(start=start, bar=parts[0].bar, **arrays)


def slice_bars(bars: Bars, lo: int, hi: int) -> Bars:
    """Bars ``lo`` to ``hi`` (exclusive), counted from the first bar."""
    fields: dict[str, Any] = {
        name: getattr(bars, name)[lo:hi]
        for name in bars.__dataclass_fields__
        if name not in ("start", "bar")
    }
    return Bars(start=bars.start + lo, bar=bars.bar, **fields)
