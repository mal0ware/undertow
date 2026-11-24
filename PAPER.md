# Sources, formulas and comparison

Every formula in the code is listed here with where it comes from. Then each claim in the sources is set next to what this repository measured. All measured numbers are in `results/` and come from `scripts/reproduce.py`.

## Versions read

| Source | Version read for this build | Note |
|---|---|---|
| Cont, Kukanov and Stoikov, "The Price Impact of Order Book Events", J. Financial Econometrics 12(1), 2014 | arXiv:1011.6402v3, dated March 2011 | The journal version was not read. Equation numbers below are the arXiv ones. |
| Avellaneda and Stoikov, "High-frequency trading in a limit order book", Quantitative Finance 8(3), 2008 | The published article, and the October 2006 preprint | The published PDF's text layer drops Greek letters and minus signs, so symbols were checked against the preprint. Equation numbers are the published ones. |
| Roll, "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market", J. Finance 39(4), 1984 | Not read | The formula is taken from its restatement in Corwin and Schultz, eqs. (17) to (20). This is a secondary source. |
| Corwin and Schultz, "A Simple Way to Estimate Bid-Ask Spreads from Daily High and Low Prices", J. Finance 67(2), 2012 | NBER conference draft, 2009 | Equation numbers may differ in the journal version. |
| Abdi and Ranaldo, "A Simple Estimation of Bid-Ask Spreads from Daily Close, High, and Low Prices", Review of Financial Studies 30(12), 2017 | University of St. Gallen working paper 2016/04, version of April 2017 | Numbering not checked against the journal. |

## Formulas

### Order-flow imbalance (Cont, Kukanov, Stoikov)

Section 2.1, unnumbered. For the n-th change of the best quotes, with bid price and size `Pb, qb` and ask price and size `Pa, qa`:

```
e_n = 1{Pb_n >= Pb_{n-1}} qb_n - 1{Pb_n <= Pb_{n-1}} qb_{n-1}
    - 1{Pa_n <= Pa_{n-1}} qa_n + 1{Pa_n >= Pa_{n-1}} qa_{n-1}

OFI_k = sum of e_n over the updates in interval k
```

Code: `ofi.event_contributions`.

Price change, section 2.1, unnumbered: `dP_k = (P_k - P_{k-1}) / tick`, with `P_k` the mid at the end of interval k.

Eq. (4): `dP_k = alpha_i + beta_i OFI_k + eps_k`, by OLS in each subsample i, with White standard errors. The paper uses half-hour subsamples of 10-second intervals, so about 180 observations each. Code: `ofi.ols`, `ofi.window_fits`.

Trade imbalance, section 4.1: `TI_k` is buyer-initiated volume minus seller-initiated volume in interval k. Eq. (8b) regresses `dP_k` on `TI_k`, and (8c) on both.

Average depth, section 2.3: `AD_i` is the average over quote updates in subsample i of `(qb + qa) / 2`. Eq. (3): `beta_i = c / AD_i^lambda`. Eq. (5), the estimating form: `log beta_i = alpha - lambda log AD_i`. Code: `ofi.depth_relation`. Eq. (6), a second-stage fit of `c`, is not implemented; `c` here is `exp(alpha)` from eq. (5).

### The quoter (Avellaneda, Stoikov)

- Eq. (1): the mid follows `dS = sigma dW`.
- Eq. (29): reservation price `r = s - q gamma sigma^2 (T - t)`. Code: `quoter.reservation_price`.
- Eq. (12): fill intensity `lambda(delta) = A exp(-k delta)`. Code: `quoter.intensity`.
- Eq. (30): `delta_a + delta_b = gamma sigma^2 (T - t) + (2 / gamma) ln(1 + gamma / k)`. Code: `quoter.optimal_spread`.

Section 3.3, the simulation: `s = 100, T = 1, sigma = 2, dt = 0.005, q = 0, k = 1.5, A = 140`, 1000 paths, gamma of 0.1, 0.01 and 1. In each step a quote at distance delta fills with probability `lambda(delta) dt`, then the mid moves by plus or minus `sigma sqrt(dt)`. The symmetric benchmark quotes the inventory strategy's average spread around the mid. Code: `quoter.simulate_paper`.

### Spread estimators

Roll, as restated in Corwin and Schultz eq. (20): `S = 2 sqrt(-Cov(dP_t, dP_{t-1}))`. A positive covariance is set to zero, the convention Corwin and Schultz use. Applied to log closes, so `S` is proportional. Code: `spread.roll`.

Corwin and Schultz, for consecutive days t and t+1:

```
beta  = ln(H_t / L_t)^2 + ln(H_{t+1} / L_{t+1})^2                     (6)
gamma = ln(H_{t,t+1} / L_{t,t+1})^2                                   (9)
alpha = (sqrt(2 beta) - sqrt(beta)) / (3 - 2 sqrt 2)
        - sqrt(gamma / (3 - 2 sqrt 2))                                (15)
S     = 2 (e^alpha - 1) / (1 + e^alpha)                               (16)
```

Overnight adjustment, their section 2.1: if day t+1 trades wholly above the close of day t, its high and low are lowered by the gap; wholly below, raised. Negative two-day estimates are set to zero before averaging. Code: `spread.corwin_schultz`.

Abdi and Ranaldo, with log close `c`, and `eta_t` the mean of the log high and log low:

```
two-day (11):      mean over t of sqrt(max(4 (c_t - eta_t)(c_t - eta_{t+1}), 0))
whole sample (10): sqrt(max(4 mean((c_t - eta_t)(c_t - eta_{t+1})), 0))
```

Code: `spread.abdi_ranaldo`. The paper applies (10) month by month. Here it is applied once to the whole sample.

### Uncertainty (added in a later revision, not from the papers)

Block bootstrap for table 1: the per-window values of each statistic are a series in time order. A circular block bootstrap resamples blocks of `ceil(n^(1/3))` consecutive windows, 2000 times with seed 0, and reports the 2.5% and 97.5% quantiles of the resampled means. Code: `stats.block_bootstrap`, `experiments.ofi_bootstrap`.

Quoter profit by day: the replay's profit is split by UTC day of the test period. The standard error is the standard deviation of the four daily totals over the square root of four. Code: `stats.day_summary`.

## Claim by claim

### Cont, Kukanov, Stoikov

Their data: 50 S&P 500 stocks, April 2010, consolidated quotes, 10-second intervals. This data: one instrument, the Binance BTCUSDT perpetual future, five days (2024-03-25 to 2024-03-29), 70.5 million quote updates (`results/table0_sample.csv`). A different asset class and one name, so agreement or disagreement says nothing about their result on equities.

| Claim | Paper | Here (10 s, 239 windows) | Verdict |
|---|---|---|---|
| OFI explains mid-price change, average R-squared | 65% | 68.2% (block-bootstrap 95% interval 66.5% to 69.9%) | Matches |
| Slope significant at 5% | 97% of subsamples | 100% | Matches |
| Average t-statistic of the slope | 11.47 | 16.7 | Higher here |
| Trade imbalance alone, average R-squared | 32% | 36.7% | Close |
| Both regressors, average R-squared | 67% | 80.9% | Does not match |
| Trade imbalance significant once OFI is included | 31% of subsamples | 96.7% | Does not match |
| lambda in beta = c / AD^lambda | 0.98 | 1.06 | Close |
| c | 0.45 | 4.30 | Does not match |
| R-squared of the log fit, eq. (5) | 74% | 62% | Lower here |
| "The fit of our model generally increases with dt" | stated, no table | R-squared peaks at 5 to 10 s (68%) and falls to 32% at 300 s | Does not match |

Likely reasons for the differences. These are my reading, not something tested here.

- Trade imbalance adds 13 points of R-squared here and 2 in the paper. In this market the mid moves a mean of 31 ticks from one second to the next (median 1, standard deviation 63), and the spread is one tick at the end of 99.3% of seconds (`results/table0_sample.csv`). A large trade walks through several price levels. Level-one OFI records only the sizes at the best quotes before and after, so the volume taken from deeper levels shows up in trade imbalance and not in OFI. In the paper's stocks the price rarely moved more than a tick in ten seconds.
- `c` is 9.5 times the paper's. In the stylised model `c = 1/2` means flow equal to twice the best-quote depth moves the price one tick, which assumes every level behind the best holds the same depth. Here flow equal to the best-quote depth moves the price about four ticks, so the levels behind the best are thinner than the best level, or get cancelled as it is consumed. No depth beyond level one was available to check this.
- OFI's R-squared falls with interval length and trade imbalance's rises (62% at 300 s). Over 300 seconds the price crosses hundreds of ticks and level-one OFI adds up thousands of whole-queue terms from price changes. The paper's statement was about intervals up to 10 minutes on stocks whose price moves a few ticks in that time.

One addition that is not in the paper: the predictive regression of the next interval's price change on this interval's OFI, in sample and out of sample (slope fitted in the previous window). Results are in the README, `results/table1_ofi_by_horizon.csv` and, with block-bootstrap intervals, `results/table1c_ofi_bootstrap.csv`. Out of sample the sign is right 62.7% of the time at 1 s (62.0% to 63.3%) and 52.4% at 5 s (51.6% to 53.1%). From 10 s the interval includes 50%. Only level-one data is available, so this cannot say whether the one-second forecast is more than the best queue running out.

### Avellaneda, Stoikov

The paper's own simulation, rerun with 1000 paths and seed 0 (`results/table3_paper_simulation.csv`):

| gamma | Strategy | Spread: paper / here | Profit: paper / here | Std(profit): paper / here | Std(final q): paper / here |
|---|---|---|---|---|---|
| 0.1 | Inventory | 1.49 / 1.49 | 65.0 / 65.1 | 6.6 / 6.6 | 2.9 / 3.0 |
| 0.1 | Symmetric | 1.49 / 1.49 | 68.4 / 68.2 | 12.7 / 12.8 | 8.4 / 8.5 |
| 0.01 | Inventory | 1.35 / 1.35 | 68.6 / 68.7 | 8.7 / 8.7 | 5.1 / 5.4 |
| 0.01 | Symmetric | 1.35 / 1.35 | 68.8 / 68.8 | 12.8 / 12.9 | 8.7 / 8.8 |
| 1 | Inventory | 3.02 / 3.02 | 31.4 / 31.5 | 5.0 / 4.8 | 1.7 / 1.7 |
| 1 | Symmetric | 3.02 / 3.02 | 44.0 / 43.8 | 11.0 / 10.5 | 5.1 / 5.1 |

The simulation replicates. The differences are the size expected from 1000 random paths. Two details were inferred, because the paper does not state them: the published "spread" column equals eq. (30) averaged over the session (`T - t` replaced by `T / 2`), and the symmetric strategy quotes that constant. Both reproduce the published spread column to the second decimal.

On the real tape the paper's main claim is that the inventory strategy gives up a little profit for a much lower variance of profit and of final inventory.

| Claim | Paper (gamma = 0.1) | Here (paper's gamma = 0.1, requote 1 s, kind fills) | Verdict |
|---|---|---|---|
| Inventory strategy holds less inventory | std of final q 2.9 against 8.4 | std of q over time 0.97 against 73.5 BTC | Matches, more strongly |
| Inventory strategy earns slightly less | 65.0 against 68.4 | -382,133 against +6,390 USDT with full-size fills; -294,931 against -106,902 with fills capped by traded volume | Does not match: the inventory strategy loses on each of the four days (t = -5.8 and -5.0 on day totals); the symmetric one cannot be told from zero (t = 0.04 and -0.43) |
| Both strategies are profitable | yes | neither earns a spread after inventory | Does not match |

The reason is a model assumption that the tape breaks. In the paper a fill at distance delta arrives with probability `lambda(delta) dt`, independent of the next move of the mid. On the tape a quote away from the touch fills only when the price moves through it, and one-second mid changes are positively autocorrelated (0.090 over the five days, 0.071 to 0.114 day by day, `results/table0_sample.csv`), so the price tends to keep going. The symmetric quoter's result of about zero is what a martingale price gives a passive quote. The inventory quoter then pays to shed each position right after it was picked off.

The exponential fill curve also fits poorly: R-squared 0.66 at a one-second requote and 0.82 at 100 ms (`results/fig3_fill_rate.png`). The measured rate drops sharply between the touch and the next tick, then decays slowly.

Differences from the paper in the tape replay, all deliberate:

1. The time to horizon `T - t` is held constant at `tau`. The paper has a session that ends. A perpetual future trades around the clock and has no close.
2. `gamma` and `tau` are set by matching the paper's simulation in dimensionless form: `gamma / k` takes the paper's three values (0.01/1.5, 0.1/1.5, 1/1.5) and `tau` solves `sigma^2 tau k^2 = 9`, the paper's `2^2 * 1 * 1.5^2`. `sigma` and `k` are measured on the first day and the replay runs on the other four.
3. Quotes are rounded outward to the tick and may not cross the opposite best quote.
4. Fills come from archive trades under two fill rules and two size rules (see the README), with at most one fill per side per requote interval. Under the full size rule every fill is the whole 1 BTC. Under the traded size rule a fill is capped by the taker volume that printed at the prices the fill rule counts. At the paper's gamma of 0.1 the traded rule fills about half to two thirds as many BTC. It does worse per BTC filled in every configuration except the symmetric quoter at gamma 1, which earns slightly more.

### Spread estimators

No paper table is replicated. The estimators are checked against simulated prices with a known spread and then applied to 305 daily bars of the BTCUSDT perpetual (2023-06-01 to 2024-03-31).

| Estimator | Estimate on real daily bars | Mean estimate on simulated prices with zero spread, 3% daily volatility |
|---|---|---|
| Roll | 164 bps | 67 bps |
| Corwin-Schultz | 100 bps | 120 bps |
| Abdi-Ranaldo, two-day | 84 bps | 117 bps |
| Abdi-Ranaldo, whole sample | 92 bps | 29 bps |
| Quoted spread measured from the book | 0.016 bps | |

All three return a spread thousands of times the real one. The simulation shows why: with 3% daily volatility they report 30 to 120 bps when the true spread is zero, because negative estimates are floored at zero and what is left is noise. They recover a 200 bps spread to within a quarter (190, 243, 173 and 198 bps). They were built for daily equity data with spreads of a percent or more. Corwin and Schultz report the same floor effect in their own data: flooring raised their mean estimate from 1.85% to 2.65%.

The real-data comparison is loose in one way. The quoted spread is measured on five days in March 2024 and the estimators use ten months.

## Variants tried

Everything that was run on the Binance archive is reported. One run on other data was withdrawn, item 6.

1. An exploratory run of the order-flow tables and the calibration on the first day alone, before the five-day run. Same code, same settings.
2. The rule for `gamma` and `tau` (item 2 above) was chosen after seeing the first day's `sigma` and `k`. The rule, the replay code and the replay call arrive together in commit 5ca8329, so git cannot show whether the rule came before the first replay.
3. The quoter was first replayed with a one-second requote interval only. After seeing that it lost and that the two fill rules barely differed, a 100 ms requote interval was added to check whether the one-second staleness was the cause. Both are in table 5. The conclusion did not change.
4. The out-of-sample forecast from the lagged price change (the last two columns of table 1) was added after seeing the one-second predictive result, to check whether OFI says more than the last move does.
5. Interval lengths (1, 5, 10, 30, 60, 300 s), the window of 180 intervals, the 51-point grid for the fill curve, the five days, and the simulation settings for the spread estimators were each chosen once and not varied.
6. One short recording of a second exchange's public feed was run through the order-flow regression. Its tables were withdrawn because that venue's terms on publishing derived market data are unclear, and the recording code has since been removed. No number from it is in this repository and no result here depends on it.
7. Post hoc, after an outside review of the first results: the block-bootstrap intervals on table 1 (table 1c), the profit by day with day-level standard errors (table 5b and the day columns of table 5), the traded size rule, and the sample facts in table 0. Each was run once with the settings stated above. The block length rule and 2000 resamples were set before the intervals were computed and were not varied. Adding the traded size rule made the quoter's loss larger, and the bootstrap put the 5 s sign hit rate of 52.4%, which the first write-up did not discuss, above 50%.

## Not verified

- The journal versions of all five papers. Working-paper and preprint versions were read, as listed at the top.
- Roll's formula against Roll's paper.
- The final-inventory signs in the published Avellaneda-Stoikov tables. The PDF text layer drops minus signs. The values are means near zero, so this does not affect any comparison.
- Whether the archive's `bookTicker` files are complete. Their update ids are not consecutive by design, so a missing update cannot be detected. Sixteen of 432,000 seconds have no quote update (`results/table0_sample.csv`).
- Exchange fee schedules. No fee is assumed anywhere. Table 5 reports the fee or rebate each result would need to break even.
