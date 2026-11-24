"""Bar building, joining, and reading archive files (built in a temp folder, no download)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pytest

from undertow.data import (
    AGG_TRADE_COLUMNS,
    BOOK_TICKER_COLUMNS,
    Bars,
    Trades,
    archive_files,
    build_bars,
    concat_bars,
    load_binance_day,
    load_binance_trades,
    load_klines,
    slice_bars,
)
from undertow.synthetic import synthetic_bars, synthetic_streams

A = np.asarray
T0 = 1_700_000_000.0


def small() -> Bars:
    # quotes at 0.2, 0.7, 2.1 and 2.9 seconds; nothing in second 1
    return build_bars(
        quote_time=T0 + A([0.2, 0.7, 2.1, 2.9]),
        bid=A([100.0, 100.0, 100.1, 100.1]),
        bid_qty=A([5.0, 8.0, 2.0, 2.0]),
        ask=A([100.1, 100.1, 100.2, 100.2]),
        ask_qty=A([7.0, 7.0, 6.0, 9.0]),
        trade_time=T0 + A([0.5, 0.6, 2.5, 2.6, 99.0]),
        trade_price=A([100.1, 100.3, 100.1, 100.0, 1.0]),
        trade_qty=A([1.0, 2.0, 0.5, 0.25, 1.0]),
        trade_buy=A([True, True, False, False, True]),
    )


def test_build_bars_by_hand() -> None:
    bars = small()
    assert len(bars) == 3
    assert bars.start == int(T0)
    assert bars.bar == 1.0
    # second 0: bid size 5 -> 8 gives +3. second 2: both sides step up (2 + 7 = 9), then ask
    # size 6 -> 9 gives -3
    assert bars.ofi.tolist() == [3.0, 0.0, 6.0]
    assert bars.updates.tolist() == [2.0, 0.0, 2.0]
    assert bars.bid.tolist() == [100.0, 100.0, 100.1]  # carried through the empty second
    assert bars.ask.tolist() == [100.1, 100.1, 100.2]
    assert bars.mid[2] == pytest.approx(100.15)
    assert bars.depth.tolist() == pytest.approx([(6.0 + 7.5) / 2, 7.5, (4.0 + 5.5) / 2])
    assert bars.buy_volume.tolist() == [3.0, 0.0, 0.0]
    assert bars.sell_volume.tolist() == [0.0, 0.0, 0.75]
    assert bars.max_buy.tolist() == [100.3, -np.inf, -np.inf]
    assert bars.min_sell.tolist() == [np.inf, np.inf, 100.0]
    assert bars.valid.all()  # the trade at 99 s is outside the quotes and is dropped


def test_build_bars_at_100_ms() -> None:
    bars = build_bars(
        quote_time=T0 + A([0.05, 0.149, 0.150, 0.31]),
        bid=A([100.0] * 4),
        bid_qty=A([1.0, 2.0, 4.0, 8.0]),
        ask=A([100.1] * 4),
        ask_qty=A([1.0] * 4),
        trade_time=T0 + A([0.30]),
        trade_price=A([100.1]),
        trade_qty=A([1.0]),
        trade_buy=A([True]),
        bar=0.1,
    )
    assert len(bars) == 4
    assert bars.bar == 0.1
    assert bars.start == int(T0) * 10
    assert bars.ofi.tolist() == [0.0, 3.0, 0.0, 4.0]
    assert bars.max_buy.tolist() == [-np.inf, -np.inf, -np.inf, 100.1]
    # the total does not depend on the bar length
    assert bars.ofi.sum() == pytest.approx(7.0)


def test_bar_length_does_not_change_totals() -> None:
    s = synthetic_streams(seconds=300, seed=2)
    one = synthetic_bars(seconds=300, seed=2, bar=1.0)
    tenth = synthetic_bars(seconds=300, seed=2, bar=0.1)
    assert tenth.ofi.sum() == pytest.approx(one.ofi.sum())
    assert tenth.buy_volume.sum() == pytest.approx(one.buy_volume.sum())
    assert tenth.updates.sum() == one.updates.sum() == len(s["quote_time"])
    assert tenth.bid[-1] == one.bid[-1]


def test_build_bars_rejects_bad_input() -> None:
    empty = A([], dtype=np.float64)
    none = A([], dtype=np.bool_)
    with pytest.raises(ValueError):
        build_bars(empty, empty, empty, empty, empty, empty, empty, empty, none)
    two = A([1.0, 1.0])
    with pytest.raises(ValueError):
        build_bars(A([5.0, 4.0]), two, two, two, two, empty, empty, empty, none)


def test_concat_and_slice() -> None:
    a = synthetic_bars(seconds=60, seed=0, start_time=T0)
    b = synthetic_bars(seconds=60, seed=1, start_time=T0 + 100)
    joined = concat_bars([a, b])
    assert len(joined) == b.start + len(b) - a.start
    hole = slice(len(a), b.start - a.start)
    assert not joined.valid[hole].any()
    assert np.all(joined.bid[hole] == a.bid[-1])
    assert np.all(joined.ofi[hole] == 0)
    assert np.array_equal(joined.ofi[: len(a)], a.ofi)
    assert np.array_equal(joined.ofi[b.start - a.start :], b.ofi)
    part = slice_bars(joined, 10, 20)
    assert len(part) == 10 and part.start == joined.start + 10
    assert np.array_equal(part.bid, joined.bid[10:20])
    with pytest.raises(ValueError):
        concat_bars([b, a])
    with pytest.raises(ValueError):
        concat_bars([])


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    bars = synthetic_bars(seconds=120, seed=4, bar=0.1)
    bars.save(tmp_path / "derived" / "bars.npz")
    back = Bars.load(tmp_path / "derived" / "bars.npz")
    assert back.start == bars.start and back.bar == 0.1
    for name in ("ofi", "bid", "ask", "max_buy", "min_sell", "valid"):
        assert np.array_equal(getattr(back, name), getattr(bars, name))


def test_archive_file_keys() -> None:
    keys = archive_files("BTCUSDT", ["2024-03-25"], ["2024-03"])
    assert keys == [
        "data/futures/um/daily/bookTicker/BTCUSDT/BTCUSDT-bookTicker-2024-03-25.zip",
        "data/futures/um/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2024-03-25.zip",
        "data/futures/um/monthly/klines/BTCUSDT/1d/BTCUSDT-1d-2024-03.zip",
    ]


def _zip(path: Path, text: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(path.stem + ".csv", text)


@pytest.mark.parametrize("header", [True, False])
def test_load_binance_day_from_archive_layout(tmp_path: Path, header: bool) -> None:
    ms = int(T0 * 1000)
    quotes = [
        f"1,100.0,5.0,100.1,7.0,{ms + 200},{ms + 205}",
        f"3,100.1,2.0,100.2,6.0,{ms + 2100},{ms + 2105}",
        f"2,100.0,8.0,100.1,7.0,{ms + 700},{ms + 705}",  # out of order in the file
    ]
    trades = [
        f"10,100.1,1.0,1,1,{ms + 500},false",  # buyer was the taker
        f"11,100.0,0.25,2,3,{ms + 2600},true",  # buyer was the maker: a sell
    ]
    head_q = ",".join(BOOK_TICKER_COLUMNS) + "\n" if header else ""
    head_t = ",".join(AGG_TRADE_COLUMNS) + "\n" if header else ""
    _zip(tmp_path / "XYZ-bookTicker-2024-01-01.zip", head_q + "\n".join(quotes) + "\n")
    _zip(tmp_path / "XYZ-aggTrades-2024-01-01.zip", head_t + "\n".join(trades) + "\n")
    one, tenth = load_binance_day(tmp_path, "XYZ", "2024-01-01", bars=(1.0, 0.1))
    assert one.ofi.tolist() == [3.0, 0.0, 9.0]
    assert one.buy_volume.tolist() == [1.0, 0.0, 0.0]
    assert one.sell_volume.tolist() == [0.0, 0.0, 0.25]
    assert one.min_sell[2] == 100.0
    assert len(tenth) == 20 and tenth.ofi.sum() == 12.0
    (limited,) = load_binance_day(tmp_path, "XYZ", "2024-01-01", nrows=1)
    assert len(limited) == 1
    trades = load_binance_trades(tmp_path, "XYZ", "2024-01-01")
    assert trades.time_ms.tolist() == [ms + 500, ms + 2600]
    assert trades.buy.tolist() == [True, False]
    assert trades.qty.tolist() == [1.0, 0.25]


def test_trades_save_load_and_concat(tmp_path: Path) -> None:
    a = Trades(A([1, 2], dtype=np.int64), A([10.0, 11.0]), A([0.5, 1.0]), A([True, False]))
    b = Trades(A([3], dtype=np.int64), A([12.0]), A([2.0]), A([True]))
    a.save(tmp_path / "t.npz")
    back = Trades.load(tmp_path / "t.npz")
    assert back.time_ms.tolist() == [1, 2] and back.buy.tolist() == [True, False]
    joined = Trades.concat([a, b])
    assert len(joined) == 3 and joined.price.tolist() == [10.0, 11.0, 12.0]


def test_load_klines(tmp_path: Path) -> None:
    row = "{t},10.0,11.0,9.0,10.5,1,{t2},1,1,1,1,0"
    feb = row.format(t=1706745600000, t2=1706831999999)
    jan = row.format(t=1704067200000, t2=1704153599999)
    _zip(tmp_path / "XYZ-1d-2024-02.zip", feb + "\n")
    _zip(tmp_path / "XYZ-1d-2024-01.zip", "open_time,open,high,low,close,v,ct,q,n,a,b,i\n" + jan)
    table = load_klines(tmp_path, "XYZ", ["2024-02", "2024-01"])
    assert table["date"].tolist() == ["2024-01-01", "2024-02-01"]
    assert table["high"].tolist() == [11.0, 11.0]
    assert list(table.columns) == ["date", "open", "high", "low", "close"]
