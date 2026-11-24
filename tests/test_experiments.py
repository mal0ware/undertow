"""The experiment tables on a synthetic tape, and the reproduce script end to end."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from undertow import experiments as ex
from undertow.data import TICK, concat_bars
from undertow.synthetic import synthetic_bars, synthetic_tape

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bars() -> object:
    return synthetic_bars(seconds=5400, seed=11)


def test_ofi_table_on_the_toy_tape(bars: object) -> None:
    table = ex.ofi_by_horizon(bars, TICK, [1, 5, 10])  # type: ignore[arg-type]
    assert table["interval_s"].tolist() == [1, 5, 10]
    assert table["windows"].tolist() == [29, 5, 2]
    # in the toy model price moves only when a queue empties, so flow explains most of it
    assert (table["r2_ofi"] > 0.5).all()
    assert (table["r2_both"] >= table["r2_ofi"]).all()
    assert (table["ofi_significant"] == 1.0).all()
    # and trades alone explain much less
    assert (table["r2_ti"] < table["r2_ofi"]).all()


def test_horizons_without_enough_data_are_left_out(bars: object) -> None:
    table = ex.ofi_by_horizon(bars, TICK, [10, 300])  # type: ignore[arg-type]
    assert table["interval_s"].tolist() == [10]


def test_depth_table_columns(bars: object) -> None:
    table = ex.depth_table(bars, TICK, step=1)  # type: ignore[arg-type]
    assert list(table.columns) == ["interval_s", "windows_used", "c", "lambda", "r2"]
    assert table["windows_used"].iloc[0] > 10
    assert table["c"].iloc[0] > 0


def test_paper_simulation_table() -> None:
    table = ex.paper_simulation(paths=300, seed=0)
    assert len(table) == 6
    assert np.allclose(table["spread"], table["paper_spread"], atol=0.006)
    assert np.allclose(table["profit"], table["paper_profit"], atol=3.0)
    inv = table[table["strategy"] == "inventory"]["final_q_std"].to_numpy()
    sym = table[table["strategy"] == "symmetric"]["final_q_std"].to_numpy()
    assert (inv < sym).all()


def test_quoter_table_and_dimensionless_settings() -> None:
    days = [synthetic_bars(seconds=1800, seed=i, start_time=1.7e9 + 1800 * i) for i in range(2)]
    cal = ex.calibrate_bars(days[0], TICK)
    tau = ex.paper_tau(cal)
    assert cal.sigma**2 * tau * cal.k**2 == pytest.approx(9.0)
    table = ex.quoter_table(days[1], cal, TICK)
    assert len(table) == 12
    assert np.allclose(table["gamma"] / cal.k, np.repeat(ex.PAPER_GAMMA_OVER_K, 4))
    assert np.allclose(table["pnl"], table["spread_earned"] + table["inventory_pnl"])
    kind = table[table["fills_rule"] == "kind"]["fills"].to_numpy()
    unkind = table[table["fills_rule"] == "unkind"]["fills"].to_numpy()
    assert (unkind <= kind).all()
    row = ex.calibration_row(cal, days[0], days[1])
    assert row["requote_s"] == 1.0
    assert row["tau_s"] == pytest.approx(tau)
    assert row["calibration_hours"] == pytest.approx(0.5, abs=0.01)


def test_calibration_units_do_not_depend_on_bar_length() -> None:
    one = synthetic_bars(seconds=3600, seed=5, bar=1.0)
    half = synthetic_bars(seconds=3600, seed=5, bar=0.5)
    row_one = ex.calibration_row(ex.calibrate_bars(one, TICK), one, one)
    row_half = ex.calibration_row(ex.calibrate_bars(half, TICK), half, half)
    # the toy price is a random walk, so volatility per root second is the same either way
    assert row_half["sigma_usdt_per_sqrt_s"] == pytest.approx(
        row_one["sigma_usdt_per_sqrt_s"], rel=0.1
    )
    assert row_half["calibration_hours"] == pytest.approx(row_one["calibration_hours"], abs=0.01)


def test_spread_simulation_table() -> None:
    table = ex.spread_simulation(spreads=[0.02, 0.0001], sigma=0.01, days=200, runs=10)
    assert table["true_spread_bps"].tolist() == [200.0, 1.0]
    wide, tiny = table.iloc[0], table.iloc[1]
    assert wide["ar_mean_bps"] == pytest.approx(200.0, rel=0.15)
    assert tiny["cs_mean_bps"] > 10.0  # nowhere near one basis point


def test_spread_real_table() -> None:
    rng = np.random.default_rng(0)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 120)))
    klines = pd.DataFrame({"high": close * 1.01, "low": close * 0.99, "close": close})
    bars = synthetic_bars(seconds=600, seed=1)
    table = ex.spread_real(klines, bars)
    assert table["estimator"].tolist()[-1] == "Quoted spread, measured"
    assert table["spread_bps"].iloc[-1] == pytest.approx(1.0, rel=0.05)  # one tick on 1000
    assert table["days"].tolist() == [120, 120, 120, 120, 0]  # ten minutes of bars
    assert len(ex.spread_real(klines, None)) == 4


def test_tables_are_deterministic() -> None:
    def build() -> list[pd.DataFrame]:
        days = [synthetic_bars(seconds=1200, seed=i, start_time=1.7e9 + 1200 * i) for i in (0, 1)]
        cal = ex.calibrate_bars(days[0], TICK)
        trades = synthetic_tape(seconds=1200, seed=1, start_time=1.7e9 + 1200)[1]
        return [
            ex.sample_table(days, ["0", "1"], TICK),
            ex.ofi_by_horizon(concat_bars(days), TICK, [1, 5]),
            ex.ofi_bootstrap(concat_bars(days), TICK, [1], resamples=50),
            *ex.quoter_runs(days[1], cal, TICK, trades),
            ex.paper_simulation(paths=50),
            ex.spread_simulation(runs=3),
        ]

    for first, second in zip(build(), build(), strict=True):
        pd.testing.assert_frame_equal(first, second)


def _reproduce(out: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = importlib.util.spec_from_file_location("reproduce", ROOT / "scripts" / "reproduce.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys, "argv", ["reproduce.py", "--fast", "--synthetic", "--out", str(out)])
    assert module.main() == 0


def test_reproduce_twice_gives_identical_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _reproduce(tmp_path / "a", monkeypatch)
    _reproduce(tmp_path / "b", monkeypatch)
    names = sorted(p.name for p in (tmp_path / "a").iterdir())
    assert names == sorted(p.name for p in (tmp_path / "b").iterdir())
    tables = [n for n in names if n.endswith((".csv", ".md", ".txt"))]
    assert len(tables) >= 9
    assert not [n for n in names if n.startswith(("table8", "table9"))]
    for name in tables:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
    figures = [n for n in names if n.endswith(".png")]
    assert len(figures) == 5
    for name in figures:
        assert (tmp_path / "a" / name).stat().st_size > 5000


def test_sample_table_by_day_and_overall() -> None:
    days = [synthetic_bars(seconds=600, seed=i, start_time=1.7e9 + 600 * i) for i in (0, 1)]
    table = ex.sample_table(days, ["a", "b"], TICK)
    assert table["day"].tolist() == ["a", "b", "all"]
    assert table["seconds"].tolist() == [600, 600, 1200]
    assert table["quote_updates"].iloc[2] == table["quote_updates"].iloc[:2].sum()
    # the toy book always has a one-tick spread
    assert (table["spread_one_tick_share"] == 1.0).all()
    first = days[0]
    assert table["change_pct"].iloc[0] == pytest.approx(100 * (first.mid[-1] / first.mid[0] - 1))
    change = np.diff(first.mid) / TICK
    assert table["abs_change_mean_ticks"].iloc[0] == pytest.approx(np.mean(np.abs(change)))
    assert table["change_autocorr_1"].iloc[0] == pytest.approx(
        np.corrcoef(change[:-1], change[1:])[0, 1]
    )


def test_ofi_bootstrap_brackets_the_estimates(bars: object) -> None:
    table = ex.ofi_bootstrap(bars, TICK, [1, 5], resamples=300)  # type: ignore[arg-type]
    assert table["statistic"].tolist() == ex.BOOTSTRAP_STATISTICS * 2
    assert (table["ci95_low"] <= table["estimate"] + 1e-12).all()
    assert (table["estimate"] <= table["ci95_high"] + 1e-12).all()
    base = ex.ofi_by_horizon(bars, TICK, [1, 5])  # type: ignore[arg-type]
    r2 = table[table["statistic"] == "r2_ofi"]["estimate"].to_numpy()
    assert np.allclose(r2, base["r2_ofi"].to_numpy())
    assert table[table["interval_s"] == 1]["block_windows"].iloc[0] == 4  # 29 windows


def test_quoter_runs_with_traded_size_and_days() -> None:
    tapes = [synthetic_tape(seconds=1800, seed=i, start_time=1.7e9 + 1800 * i) for i in (0, 1)]
    cal = ex.calibrate_bars(tapes[0][0][0], TICK)
    test, trades = tapes[1][0][0], tapes[1][1]
    table, per_day = ex.quoter_runs(test, cal, TICK, trades)
    assert len(table) == 24
    assert set(table["size_rule"]) == {"full", "traded"}
    full = table[table["size_rule"] == "full"].reset_index(drop=True)
    traded = table[table["size_rule"] == "traded"].reset_index(drop=True)
    assert (full["filled_btc"] == full["fills"]).all()
    assert (traded["filled_btc"] <= traded["fills"]).all()
    assert np.allclose(table["pnl_per_btc"] * table["filled_btc"], table["pnl"])
    # the half hour of the test tape falls in one UTC day, so the day total is the whole profit
    sums = per_day.groupby(
        ["requote_s", "paper_gamma", "strategy", "fills_rule", "size_rule"], sort=False
    )["pnl"].sum()
    assert np.allclose(sums.to_numpy(), table["pnl"].to_numpy())
    assert (table["days"] == 1).all()
    # without trades only the full-size rule runs, as before
    assert ex.quoter_table(test, cal, TICK)["size_rule"].tolist() == ["full"] * 12


def test_day_labels_split_at_midnight_utc() -> None:
    midnight = 1_700_006_400.0  # 2023-11-15 00:00:00 UTC
    bars = synthetic_bars(seconds=120, seed=3, start_time=midnight - 60)
    days = ex._day_labels(bars)
    assert days[0] + 1 == days[-1]
    assert int((days == days[0]).sum()) == 60


def test_reproduce_opens_no_network_connection() -> None:
    source = (ROOT / "scripts" / "reproduce.py").read_text(encoding="utf-8")
    for word in ("urllib", "socket", "http", "requests"):
        assert word not in source, word
