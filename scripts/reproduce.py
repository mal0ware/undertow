"""Rebuild every figure and table.

    uv run python scripts/fetch_data.py
    uv run python scripts/reproduce.py              # full run, writes results/
    uv run python scripts/reproduce.py --fast       # one partial day, writes results_fast/
    uv run python scripts/reproduce.py --fast --synthetic   # no data needed

The first full run reads about 8 GB of CSV out of the archive files and caches one-second bars
in data/derived/. Later runs take under a minute. The fast run reads part of the first day and
its numbers are not the ones quoted in the README. The synthetic run swaps the market data for
a toy tape, to check that the pipeline runs end to end.

Every input is a Binance archive file or generated here. The script opens no network
connection.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from undertow import experiments as ex
from undertow import quoter
from undertow.data import (
    DAYS,
    KLINE_MONTHS,
    SYMBOL,
    TICK,
    Bars,
    Trades,
    concat_bars,
    load_binance_day,
    load_binance_trades,
    load_klines,
    slice_bars,
)
from undertow.synthetic import synthetic_tape

ROOT = Path(__file__).resolve().parents[1]
FAST_ROWS = 3_000_000
BAR_LENGTHS = (1.0, 0.1)

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
        "font.family": "DejaVu Sans",
        "savefig.dpi": 150,
    }
)


# ------------------------------------------------------------------------------ output


def save_table(table: pd.DataFrame, out: Path, name: str) -> None:
    table.to_csv(out / f"{name}.csv", index=False, float_format="%.6g", lineterminator="\n")


def save_figure(fig: Any, out: Path, name: str) -> None:
    fig.savefig(out / f"{name}.png", metadata={"Software": None})
    plt.close(fig)


def markdown(table: pd.DataFrame) -> str:
    def cell(value: Any) -> str:
        if isinstance(value, float | np.floating):
            if np.isfinite(value) and abs(value) >= 1000:
                return f"{value:,.0f}"
            return f"{value:.4g}"
        return str(value)

    head = "| " + " | ".join(table.columns) + " |"
    rule = "|" + "|".join(["---"] * len(table.columns)) + "|"
    rows = table.astype(object).to_numpy()
    body = ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


# ------------------------------------------------------------------------------ data


def binance_trades(fast: bool) -> list[Trades]:
    """Signed trades per day, read from the archive on first use and cached."""
    raw = ROOT / "data" / "binance"
    derived = ROOT / "data" / "derived"
    out: list[Trades] = []
    for day in DAYS[:1] if fast else DAYS:
        cache = derived / f"trades_{SYMBOL}_{day}.npz"
        if cache.exists():
            out.append(Trades.load(cache))
            continue
        if not (raw / f"{SYMBOL}-aggTrades-{day}.zip").exists():
            flag = " --fast" if fast else ""
            raise SystemExit(f"missing data for {day}: run scripts/fetch_data.py{flag} first")
        trades = load_binance_trades(raw, SYMBOL, day)
        trades.save(cache)
        out.append(trades)
    return out


def binance_days(fast: bool) -> dict[float, list[Bars]]:
    """Bars per day for each bar length, built from the archive on first use and cached."""
    raw = ROOT / "data" / "binance"
    derived = ROOT / "data" / "derived"
    out: dict[float, list[Bars]] = {bar: [] for bar in BAR_LENGTHS}
    for day in DAYS[:1] if fast else DAYS:
        suffix = "_fast" if fast else ""
        caches = {
            bar: derived / f"bars_{SYMBOL}_{day}_{round(bar * 1000)}ms{suffix}.npz"
            for bar in BAR_LENGTHS
        }
        if all(cache.exists() for cache in caches.values()):
            for bar, cache in caches.items():
                out[bar].append(Bars.load(cache))
            continue
        if not (raw / f"{SYMBOL}-bookTicker-{day}.zip").exists():
            flag = " --fast" if fast else ""
            raise SystemExit(f"missing data for {day}: run scripts/fetch_data.py{flag} first")
        start = time.time()
        built = load_binance_day(
            raw, SYMBOL, day, nrows=FAST_ROWS if fast else None, bars=BAR_LENGTHS
        )
        for bar, bars in zip(BAR_LENGTHS, built, strict=True):
            bars.save(caches[bar])
            out[bar].append(bars)
        print(f"  built bars for {day} in {time.time() - start:.0f}s")
    return out


# ------------------------------------------------------------------------------ figures


def fig_r2(table: pd.DataFrame, out: Path, where: str) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    x = table["interval_s"].to_numpy()
    lines = [
        ("r2_both", "same interval: both", SERIES[2], "^"),
        ("r2_ofi", "same interval: order-flow imbalance", SERIES[0], "o"),
        ("r2_ti", "same interval: trade imbalance", SERIES[1], "s"),
        ("r2_next_out_of_sample", "next interval, out of sample", INK, "D"),
    ]
    for column, label, colour, marker in lines:
        ax.plot(x, 100 * table[column], marker=marker, color=colour, label=label)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([str(v) for v in x])
    ax.minorticks_off()
    ax.set_xlabel("interval length (seconds)")
    ax.set_ylabel("R² of mid-price change (%)")
    ax.set_title(f"Mid-price change explained by imbalance ({where})")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2)
    fig.tight_layout()
    save_figure(fig, out, "fig1_r2_by_horizon")


def fig_quoter(table: pd.DataFrame, out: Path) -> None:
    table = table[(table["paper_gamma"] == 0.1) & (table["fills_rule"] == "kind")]
    requotes = sorted(table["requote_s"].unique(), reverse=True)
    fig, axes = plt.subplots(1, len(requotes), figsize=(7.2, 4.2), sharey=True, squeeze=False)
    for ax, requote in zip(axes[0], requotes, strict=True):
        part = table[table["requote_s"] == requote]
        labels = [
            f"{s}\n{r} size" for s, r in zip(part["strategy"], part["size_rule"], strict=True)
        ]
        x = np.arange(len(part))
        ax.bar(x - 0.27, part["spread_per_btc"], 0.26, color=SERIES[2], label="spread")
        ax.bar(x, part["inventory_per_btc"], 0.26, color=SERIES[1], label="inventory")
        ax.bar(x + 0.27, part["pnl_per_btc"], 0.26, color=INK, label="net, before fees")
        ax.axhline(0, color=MUTED, linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(f"requote every {requote:g} s, kind fills")
    axes[0][0].set_ylabel("USDT per BTC filled")
    axes[0][0].legend(loc="best")
    fig.tight_layout()
    save_figure(fig, out, "fig2_quoter_split")


def fig_calibration(cals: dict[float, quoter.Calibration], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for (bar, cal), colour in zip(cals.items(), SERIES, strict=False):
        ax.plot(cal.delta, cal.rate / bar, "o", color=colour, markersize=3.5)
        fitted = quoter.intensity(cal.delta, cal.a, cal.k) / bar
        label = f"requote {bar:g} s: k = {cal.k:.3g} per USDT, fit R² = {cal.r2:.2f}"
        ax.plot(cal.delta, fitted, color=colour, label=label)
    ax.set_yscale("log")
    ax.set_xlabel("distance of the quote from the mid, δ (USDT)")
    ax.set_ylabel("fills per second")
    ax.set_title("Measured fill rate (dots) and the fitted A exp(-k δ) (lines)")
    ax.legend(loc="best")
    fig.tight_layout()
    save_figure(fig, out, "fig3_fill_rate")


def fig_depth(bars: Bars, tick: float, out: Path) -> None:
    w = ex.fits_at(bars, 10, tick)
    keep = w.beta_ofi > 0
    c, lam, r2, _ = ex.depth_relation(w.beta_ofi, w.depth)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(w.depth[keep], w.beta_ofi[keep], "o", color=SERIES[0], markersize=3, alpha=0.6)
    grid = np.linspace(w.depth[keep].min(), w.depth[keep].max(), 50)
    ax.plot(grid, c / grid**lam, color=SERIES[1], label=f"c / AD^λ, λ = {lam:.2f}")
    ax.plot(grid, 0.5 / grid, color=MUTED, linestyle="--", label="1 / (2 AD), the stylised model")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("average depth at the best quotes, AD (BTC)")
    ax.set_ylabel("impact slope β (ticks per BTC)")
    ax.set_title(f"Impact slope against depth, 30-minute windows (R² = {r2:.2f})")
    ax.legend(loc="best")
    fig.tight_layout()
    save_figure(fig, out, "fig4_slope_vs_depth")


def fig_spread(table: pd.DataFrame, out: Path) -> None:
    table = table[table["true_spread_bps"] > 0]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = table["true_spread_bps"].to_numpy()
    names = [
        ("roll", "Roll", "o"),
        ("cs", "Corwin-Schultz", "s"),
        ("ar2", "Abdi-Ranaldo, two-day", "^"),
        ("ar", "Abdi-Ranaldo, whole sample", "D"),
    ]
    for (key, label, marker), colour in zip(names, SERIES, strict=False):
        ax.plot(x, table[f"{key}_mean_bps"], marker=marker, color=colour, label=label)
    ax.plot(x, x, color=MUTED, linestyle="--", label="true spread")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("true spread (basis points)")
    ax.set_ylabel("mean estimate (basis points)")
    ax.set_title("Spread estimators on simulated prices, daily volatility 3%")
    ax.legend(loc="best")
    fig.tight_layout()
    save_figure(fig, out, "fig5_spread_estimators")


# ------------------------------------------------------------------------------ main


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fast", action="store_true", help="smoke run on part of one day")
    parser.add_argument("--synthetic", action="store_true", help="use a toy tape, no data")
    parser.add_argument("--out", type=Path, default=None, help="output directory")
    args = parser.parse_args()

    default = "results_synthetic" if args.synthetic else "results_fast" if args.fast else "results"
    out = args.out or ROOT / default
    out.mkdir(parents=True, exist_ok=True)
    start = time.time()
    sections: list[str] = []
    vintage: list[str] = []

    def emit(title: str, name: str, table: pd.DataFrame, note: str = "") -> None:
        save_table(table, out, name)
        text = f"## {title}\n\n"
        if note:
            text += note + "\n\n"
        sections.append(text + markdown(table) + "\n")
        print(f"  {name}")

    # ---- market data
    if args.synthetic:
        seconds = 3600 if args.fast else 14400
        tapes = [
            synthetic_tape(
                seconds=seconds, seed=i, start_time=1.7e9 + i * seconds, bars=BAR_LENGTHS
            )
            for i in range(2)
        ]
        by_bar = {bar: [t[0][j] for t in tapes] for j, bar in enumerate(BAR_LENGTHS)}
        day_trades = [t[1] for t in tapes]
        labels = ["seed 0", "seed 1"]
        where = "synthetic tape"
        vintage.append("synthetic tape, seeds 0 and 1")
    else:
        by_bar = binance_days(args.fast)
        day_trades = binance_trades(args.fast)
        labels = DAYS[: len(by_bar[1.0])]
        where = f"Binance {SYMBOL} perpetual, {DAYS[0]} to {DAYS[-1]}"
        raw = ROOT / "data" / "binance"
        for path in sorted(raw.glob("*.CHECKSUM")):
            vintage.append(path.read_text().strip().replace("*", ""))
    days = by_bar[1.0]
    bars = concat_bars(days)
    print(f"bars: {len(bars)} seconds, {int(bars.updates.sum())} quote updates")

    def split(parts: list[Bars]) -> tuple[Bars, Bars, Trades]:
        """Calibration period, test period and the test period's trades: first day and the
        rest, or halves of one day."""
        if len(parts) > 1:
            return parts[0], concat_bars(parts[1:]), Trades.concat(day_trades[1:])
        half = len(parts[0]) // 2
        first, second = slice_bars(parts[0], 0, half), slice_bars(parts[0], half, len(parts[0]))
        return first, second, day_trades[0]

    emit(
        "Table 0. The sample",
        "table0_sample",
        ex.sample_table(days, labels, TICK),
        f"{where}. One-second bars. Changes are in ticks of {TICK:g} USDT. The spread share "
        "and the autocorrelation are measured at the end of each second.",
    )

    # ---- order-flow imbalance
    table1 = ex.ofi_by_horizon(bars, TICK)
    emit(
        "Table 1. Order-flow imbalance and price change, by interval length",
        "table1_ofi_by_horizon",
        table1,
        f"{where}. Averages over windows of {ex.WINDOW} intervals.",
    )
    fig_r2(table1, out, "synthetic tape" if args.synthetic else f"{SYMBOL} perpetual")
    emit(
        "Table 1c. Block-bootstrap intervals for table 1",
        "table1c_ofi_bootstrap",
        ex.ofi_bootstrap(bars, TICK, resamples=200 if args.fast else 2000),
        "95% percentile intervals from a circular block bootstrap over windows in time order. "
        "Block length is the cube root of the number of windows, rounded up.",
    )

    if not args.synthetic and not args.fast:
        by_day = []
        for day, day_bars in zip(DAYS, days, strict=True):
            row = ex.ofi_by_horizon(day_bars, TICK, [10])
            row.insert(0, "day", day)
            by_day.append(row)
        emit(
            "Table 1b. The 10-second regression, day by day",
            "table1b_ofi_by_day",
            pd.concat(by_day, ignore_index=True),
        )

    emit(
        "Table 2. Impact slope against depth",
        "table2_depth",
        ex.depth_table(bars, TICK),
        "Fit of log(beta) = log(c) - lambda log(AD) across 10-second windows.",
    )
    fig_depth(bars, TICK, out)

    # ---- Avellaneda-Stoikov
    emit(
        "Table 3. The paper's simulation, rerun",
        "table3_paper_simulation",
        ex.paper_simulation(paths=200 if args.fast else 1000),
        "Avellaneda-Stoikov section 3.3. Columns prefixed paper_ are the published values.",
    )

    cals: dict[float, quoter.Calibration] = {}
    calibration_rows = []
    curves = []
    quoter_runs = []
    quoter_days = []
    for bar in BAR_LENGTHS:
        calibration_bars, test_bars, test_trades = split(by_bar[bar])
        cal = ex.calibrate_bars(calibration_bars, TICK)
        cals[bar] = cal
        calibration_rows.append(ex.calibration_row(cal, calibration_bars, test_bars))
        curves.append(ex.calibration_table(cal, bar))
        summary, per_day = ex.quoter_runs(test_bars, cal, TICK, test_trades)
        quoter_runs.append(summary)
        quoter_days.append(per_day)
        print(f"  quoter replayed on {bar:g} s bars")
    emit(
        "Table 4. Calibration of the quoter",
        "table4_calibration",
        pd.DataFrame(calibration_rows),
        "Fill rate lambda(delta) = A exp(-k delta) and volatility from the calibration period, "
        "for each requote interval.",
    )
    save_table(pd.concat(curves, ignore_index=True), out, "table4b_fill_rate_curve")
    fig_calibration(cals, out)

    table5 = pd.concat(quoter_runs, ignore_index=True)
    emit(
        "Table 5. The quoter replayed on the tape",
        "table5_quoter",
        table5,
        "Calibrated on the calibration period, run on the rest. The quote is 1 BTC a side. "
        "Size rule full: every fill is 1 BTC. Size rule traded: a fill is capped by the taker "
        "volume at the prices the fill rule counts. Money is USDT, before fees. Day columns "
        "treat each UTC day of the test period as one independent draw.",
    )
    emit(
        "Table 5b. The quoter's profit by day",
        "table5b_quoter_by_day",
        pd.concat(quoter_days, ignore_index=True),
        "USDT, before fees, per UTC day of the test period.",
    )
    fig_quoter(table5, out)

    # ---- spread estimators
    table6 = ex.spread_simulation(runs=20 if args.fast else 200)
    emit(
        "Table 6. Spread estimators on simulated prices",
        "table6_spread_simulated",
        table6,
        "Daily volatility 3%, 300 days per run. Basis points.",
    )
    fig_spread(table6, out)
    if not args.synthetic and not args.fast:
        klines = load_klines(ROOT / "data" / "binance", SYMBOL, KLINE_MONTHS)
        emit(
            "Table 7. Spread estimators on real daily prices",
            "table7_spread_real",
            ex.spread_real(klines, bars),
            f"{SYMBOL} perpetual daily bars, {klines['date'].iloc[0]} to "
            f"{klines['date'].iloc[-1]}. The quoted spread is the mean over the one-second bars.",
        )

    mode = "synthetic" if args.synthetic else "fast" if args.fast else "full"
    source = (
        "A toy tape, no market data."
        if args.synthetic
        else "Derived from Binance Vision data (CC BY-NC-SA 4.0). See the README."
    )
    header = f"# Results\n\nWritten by `scripts/reproduce.py` ({mode} run). {source}\n\n"
    (out / "summary.md").write_text(header + "\n".join(sections), encoding="utf-8", newline="\n")
    (out / "data_vintage.txt").write_text("\n".join(vintage) + "\n", encoding="utf-8", newline="\n")
    print(f"done in {time.time() - start:.0f}s -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
