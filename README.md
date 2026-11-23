# Undertow

**Record a live order book, then test whether the flow under the surface tells you where the price goes next.**

> **Status: planned.** This repository holds the design. No results exist yet, and nothing below is a finding. Each box in the roadmap gets ticked when the code and its tests are in.

## The question

Does the imbalance between buy and sell pressure in the order book predict the next price move? And if you quoted both sides, would you keep the spread or lose it to inventory?

## What this will contain

- A recorder for a public crypto order-book feed, with gap detection
- Book reconstruction, checked against exchange snapshots
- Order-flow imbalance as Cont, Kukanov and Stoikov define it, regressed against price change at several horizons
- An Avellaneda-Stoikov quoter simulated on the recorded tape, with fees and stated queue assumptions
- Three estimators of the spread from daily prices, as a side module

## The result it is built to show

The R-squared of imbalance against price change at each horizon, and the quoter's profit split into spread earned and inventory lost.

Whatever the answer turns out to be goes at the top of this file, with one chart, before any installation step.

## Sources

- Cont, Kukanov and Stoikov, "The Price Impact of Order Book Events", Journal of Financial Econometrics 12(1), 2014
- Avellaneda and Stoikov, "High-frequency trading in a limit order book", Quantitative Finance 8(3), 2008
- Roll (1984), Corwin and Schultz (2012), Abdi and Ranaldo (2017) for the spread estimators

Every number that differs from a source will be listed in `PAPER.md` with the likely reason.

## Data

Recorded live from a public websocket feed that needs no key. Full-depth history cannot be downloaded anywhere for free, so the recorder has to run for weeks before the analysis means anything.

## How it is tested

The maths is tested before any result is trusted.

- The rebuilt book matches exchange snapshots
- The quoter's reservation price and spread match the paper's formulas
- A dropped message is detected and the affected window is excluded

## Layout

```
src/undertow/      the code
tests/             maths tests first
scripts/reproduce.py   one command rebuilds every figure and table
scripts/fetch_data.py  downloads public data into data/ (never committed)
results/           committed figures and small tables
PAPER.md           citations, claims tested, comparison with the sources
```

## Roadmap

- [ ] Project skeleton, CI, and the reproduce command
- [ ] A recorder for a public crypto order-book feed, with gap detection
- [ ] Book reconstruction, checked against exchange snapshots
- [ ] Order-flow imbalance as Cont, Kukanov and Stoikov define it, regressed against price change at several horizons
- [ ] An Avellaneda-Stoikov quoter simulated on the recorded tape, with fees and stated queue assumptions
- [ ] Three estimators of the spread from daily prices, as a side module
- [ ] `PAPER.md` comparison with the sources
- [ ] Results and limits written up at the top of this file

## Limits

- Fill simulation is the weak point of every project like this. The assumptions are written out, and the results are shown under a kind and an unkind version of them.
- Crypto books are not equity or futures books. Nothing here transfers without a new test.
- A simulated quoter does not move the market. A real one does.
- This is research code. It is not investment advice and it does not trade.

## The name

An undertow is the current under the surface that pulls the other way. Order flow is the same thing under a quoted price.

## Licence

MIT. See `LICENSE`.
