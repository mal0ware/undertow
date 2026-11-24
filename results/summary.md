# Results

Written by `scripts/reproduce.py` (full run). Derived from Binance Vision data (CC BY-NC-SA 4.0). See the README.

## Table 0. The sample

Binance BTCUSDT perpetual, 2024-03-25 to 2024-03-29. One-second bars. Changes are in ticks of 0.1 USDT. The spread share and the autocorrelation are measured at the end of each second.

| day | seconds | quote_updates | seconds_without_update | mid_first | mid_last | change_pct | abs_change_mean_ticks | abs_change_median_ticks | change_sd_ticks | spread_one_tick_share | change_autocorr_1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-03-25 | 86400 | 16516354 | 4 | 67,269 | 69,921 | 3.942 | 38.6 | 15 | 72.93 | 0.9915 | 0.07064 |
| 2024-03-26 | 86400 | 14331150 | 3 | 69,925 | 70,044 | 0.1703 | 33.07 | 6 | 63.81 | 0.9922 | 0.1015 |
| 2024-03-27 | 86400 | 15814430 | 1 | 70,049 | 69,533 | -0.7365 | 36.56 | 7 | 74.94 | 0.9873 | 0.08402 |
| 2024-03-28 | 86400 | 13562777 | 1 | 69,539 | 70,839 | 1.868 | 28.25 | 0 | 56.76 | 0.9952 | 0.1048 |
| 2024-03-29 | 86400 | 10315657 | 7 | 70,839 | 69,904 | -1.32 | 18.28 | 0 | 41.83 | 0.9964 | 0.1139 |
| all | 432000 | 70540368 | 16 | 67,269 | 69,904 | 3.917 | 30.95 | 1 | 63.21 | 0.9925 | 0.09001 |

## Table 1. Order-flow imbalance and price change, by interval length

Binance BTCUSDT perpetual, 2024-03-25 to 2024-03-29. Averages over windows of 180 intervals.

| interval_s | windows | r2_ofi | r2_ti | r2_both | t_ofi | ofi_significant | ti_significant_given_ofi | r2_next_in_sample | r2_next_out_of_sample | sign_hit_out_of_sample | sign_gain_ticks | sign_gain_bps | r2_next_oos_lagged_return | sign_hit_lagged_return |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2399 | 0.618 | 0.4061 | 0.7662 | 11.46 | 1 | 0.8608 | 0.04302 | 0.02217 | 0.6268 | 5.912 | 0.08468 | 0.003123 | 0.5785 |
| 5 | 479 | 0.6827 | 0.3674 | 0.8053 | 15.76 | 1 | 0.9478 | 0.01566 | -0.006046 | 0.5237 | 4.433 | 0.06349 | -0.0095 | 0.506 |
| 10 | 239 | 0.6821 | 0.3666 | 0.809 | 16.73 | 1 | 0.9665 | 0.008426 | -0.01269 | 0.4995 | 0.4308 | 0.006169 | -0.01341 | 0.4923 |
| 30 | 79 | 0.6289 | 0.4073 | 0.7921 | 15.67 | 1 | 0.9747 | 0.006489 | -0.01366 | 0.4946 | -1.314 | -0.01882 | -0.00983 | 0.5061 |
| 60 | 39 | 0.5671 | 0.4621 | 0.7822 | 13.68 | 1 | 1 | 0.005966 | -0.01061 | 0.5066 | -0.6135 | -0.008786 | -0.007469 | 0.509 |
| 300 | 7 | 0.3223 | 0.6196 | 0.7468 | 8.129 | 1 | 1 | 0.002974 | -0.009474 | 0.4981 | -38.84 | -0.5563 | -0.0168 | 0.4851 |

## Table 1c. Block-bootstrap intervals for table 1

95% percentile intervals from a circular block bootstrap over windows in time order. Block length is the cube root of the number of windows, rounded up.

| interval_s | statistic | estimate | ci95_low | ci95_high | windows | block_windows |
|---|---|---|---|---|---|---|
| 1 | r2_ofi | 0.618 | 0.6103 | 0.6256 | 2399 | 14 |
| 1 | r2_next_out_of_sample | 0.02217 | 0.01971 | 0.0247 | 2398 | 14 |
| 1 | sign_hit_out_of_sample | 0.6268 | 0.6202 | 0.6334 | 2398 | 14 |
| 1 | sign_gain_bps | 0.08468 | 0.07962 | 0.0898 | 2398 | 14 |
| 1 | sign_hit_lagged_return | 0.5785 | 0.5728 | 0.5842 | 2398 | 14 |
| 5 | r2_ofi | 0.6827 | 0.6701 | 0.6951 | 479 | 8 |
| 5 | r2_next_out_of_sample | -0.006046 | -0.008661 | -0.003227 | 478 | 8 |
| 5 | sign_hit_out_of_sample | 0.5237 | 0.5161 | 0.5313 | 478 | 8 |
| 5 | sign_gain_bps | 0.06349 | 0.04555 | 0.08097 | 478 | 8 |
| 5 | sign_hit_lagged_return | 0.506 | 0.4998 | 0.5124 | 478 | 8 |
| 10 | r2_ofi | 0.6821 | 0.6652 | 0.6988 | 239 | 7 |
| 10 | r2_next_out_of_sample | -0.01269 | -0.01638 | -0.009635 | 238 | 7 |
| 10 | sign_hit_out_of_sample | 0.4995 | 0.4949 | 0.504 | 238 | 7 |
| 10 | sign_gain_bps | 0.006169 | -0.02046 | 0.03225 | 238 | 7 |
| 10 | sign_hit_lagged_return | 0.4923 | 0.4884 | 0.4962 | 238 | 7 |
| 30 | r2_ofi | 0.6289 | 0.6029 | 0.6542 | 79 | 5 |
| 30 | r2_next_out_of_sample | -0.01366 | -0.01982 | -0.008257 | 78 | 5 |
| 30 | sign_hit_out_of_sample | 0.4946 | 0.4869 | 0.5024 | 78 | 5 |
| 30 | sign_gain_bps | -0.01882 | -0.08717 | 0.05352 | 78 | 5 |
| 30 | sign_hit_lagged_return | 0.5061 | 0.496 | 0.5158 | 78 | 5 |
| 60 | r2_ofi | 0.5671 | 0.5335 | 0.6002 | 39 | 4 |
| 60 | r2_next_out_of_sample | -0.01061 | -0.01553 | -0.005941 | 38 | 4 |
| 60 | sign_hit_out_of_sample | 0.5066 | 0.4982 | 0.5173 | 38 | 4 |
| 60 | sign_gain_bps | -0.008786 | -0.135 | 0.1201 | 38 | 4 |
| 60 | sign_hit_lagged_return | 0.509 | 0.4929 | 0.5224 | 38 | 4 |
| 300 | r2_ofi | 0.3223 | 0.2634 | 0.3951 | 7 | 2 |
| 300 | r2_next_out_of_sample | -0.009474 | -0.01553 | -0.004738 | 6 | 2 |
| 300 | sign_hit_out_of_sample | 0.4981 | 0.4898 | 0.5074 | 6 | 2 |
| 300 | sign_gain_bps | -0.5563 | -1.299 | 0.2466 | 6 | 2 |
| 300 | sign_hit_lagged_return | 0.4851 | 0.4553 | 0.5074 | 6 | 2 |

## Table 1b. The 10-second regression, day by day

| day | interval_s | windows | r2_ofi | r2_ti | r2_both | t_ofi | ofi_significant | ti_significant_given_ofi | r2_next_in_sample | r2_next_out_of_sample | sign_hit_out_of_sample | sign_gain_ticks | sign_gain_bps | r2_next_oos_lagged_return | sign_hit_lagged_return |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-03-25 | 10 | 47 | 0.6461 | 0.4004 | 0.7952 | 16.23 | 1 | 0.9574 | 0.00781 | -0.01212 | 0.5022 | 1.275 | 0.01864 | -0.01538 | 0.4925 |
| 2024-03-26 | 10 | 47 | 0.6884 | 0.3654 | 0.8038 | 16.7 | 1 | 0.9149 | 0.005252 | -0.00922 | 0.4964 | -2.313 | -0.03286 | -0.01302 | 0.487 |
| 2024-03-27 | 10 | 47 | 0.6691 | 0.349 | 0.8064 | 16.87 | 1 | 0.9787 | 0.008165 | -0.009325 | 0.5075 | 1.907 | 0.02731 | -0.009387 | 0.5001 |
| 2024-03-28 | 10 | 47 | 0.7177 | 0.3645 | 0.8307 | 18.09 | 1 | 1 | 0.01113 | -0.02012 | 0.4961 | -0.175 | -0.002484 | -0.01528 | 0.4936 |
| 2024-03-29 | 10 | 47 | 0.6934 | 0.3548 | 0.8117 | 15.82 | 1 | 0.9787 | 0.009738 | -0.01471 | 0.4935 | 0.9826 | 0.01402 | -0.01355 | 0.4874 |

## Table 2. Impact slope against depth

Fit of log(beta) = log(c) - lambda log(AD) across 10-second windows.

| interval_s | windows_used | c | lambda | r2 |
|---|---|---|---|---|
| 10 | 239 | 4.296 | 1.059 | 0.6221 |

## Table 3. The paper's simulation, rerun

Avellaneda-Stoikov section 3.3. Columns prefixed paper_ are the published values.

| gamma | strategy | spread | paper_spread | profit | paper_profit | profit_std | paper_profit_std | final_q | paper_final_q | final_q_std | paper_final_q_std |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.1 | inventory | 1.491 | 1.49 | 65.14 | 65 | 6.633 | 6.6 | 0.016 | 0.08 | 3.041 | 2.9 |
| 0.1 | symmetric | 1.491 | 1.49 | 68.22 | 68.4 | 12.82 | 12.7 | -0.001 | 0.26 | 8.453 | 8.4 |
| 0.01 | inventory | 1.349 | 1.35 | 68.7 | 68.6 | 8.739 | 8.7 | -0.032 | 0.12 | 5.406 | 5.1 |
| 0.01 | symmetric | 1.349 | 1.35 | 68.82 | 68.8 | 12.9 | 12.8 | 0.111 | 0.09 | 8.824 | 8.7 |
| 1 | inventory | 3.022 | 3.02 | 31.45 | 31.4 | 4.783 | 5 | 0.009 | 0.02 | 1.684 | 1.7 |
| 1 | symmetric | 3.022 | 3.02 | 43.78 | 44 | 10.49 | 11 | 0.305 | 0 | 5.139 | 5.1 |

## Table 4. Calibration of the quoter

Fill rate lambda(delta) = A exp(-k delta) and volatility from the calibration period, for each requote interval.

| requote_s | A_per_s | k_per_usdt | fit_r2 | sigma_usdt_per_sqrt_s | tau_s | calibration_hours | test_hours |
|---|---|---|---|---|---|---|---|
| 1 | 0.4691 | 0.202 | 0.6611 | 7.293 | 4.147 | 24 | 96 |
| 0.1 | 0.8807 | 0.3428 | 0.819 | 6.418 | 1.86 | 24 | 96 |

## Table 5. The quoter replayed on the tape

Calibrated on the calibration period, run on the rest. The quote is 1 BTC a side. Size rule full: every fill is 1 BTC. Size rule traded: a fill is capped by the taker volume at the prices the fill rule counts. Money is USDT, before fees. Day columns treat each UTC day of the test period as one independent draw.

| requote_s | paper_gamma | strategy | fills_rule | size_rule | gamma | quoted_spread | fills | filled_btc | spread_earned | inventory_pnl | pnl | spread_per_btc | inventory_per_btc | pnl_per_btc | breakeven_fee_bps | days | day_pnl_mean | day_pnl_se | day_pnl_t | days_positive | q_std | q_abs_max | q_final |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.01 | inventory | kind | full | 0.001347 | 10.3 | 81481 | 81,481 | 408,194 | -820,147 | -411,953 | 5.01 | -10.07 | -5.056 | -0.7206 | 4 | -102,988 | 17,722 | -5.811 | 0 | 2.953 | 18 | 1 |
| 1 | 0.01 | inventory | kind | traded | 0.001347 | 10.27 | 82364 | 52,930 | 265,214 | -591,075 | -325,861 | 5.011 | -11.17 | -6.156 | -0.8774 | 4 | -81,465 | 15,463 | -5.268 | 0 | 3.214 | 18.34 | -2.222 |
| 1 | 0.01 | inventory | unkind | full | 0.001347 | 10.3 | 79992 | 79,992 | 400,726 | -811,465 | -410,739 | 5.01 | -10.14 | -5.135 | -0.7318 | 4 | -102,685 | 17,826 | -5.76 | 0 | 2.939 | 18 | 0 |
| 1 | 0.01 | inventory | unkind | traded | 0.001347 | 10.27 | 80856 | 52,118 | 261,140 | -585,254 | -324,114 | 5.011 | -11.23 | -6.219 | -0.8863 | 4 | -81,029 | 15,363 | -5.274 | 0 | 3.214 | 18.33 | -2.314 |
| 1 | 0.01 | symmetric | kind | full | 0.001347 | 10.3 | 80916 | 80,916 | 416,654 | -656,868 | -240,214 | 5.149 | -8.118 | -2.969 | -0.4231 | 4 | -60,054 | 116,811 | -0.5141 | 1 | 102.3 | 363 | 152 |
| 1 | 0.01 | symmetric | kind | traded | 0.001347 | 10.3 | 80916 | 52,475 | 270,191 | -511,203 | -241,011 | 5.149 | -9.742 | -4.593 | -0.6545 | 4 | -60,253 | 110,086 | -0.5473 | 1 | 128.9 | 411.8 | 366 |
| 1 | 0.01 | symmetric | unkind | full | 0.001347 | 10.3 | 79336 | 79,336 | 408,517 | -612,034 | -203,517 | 5.149 | -7.714 | -2.565 | -0.3656 | 4 | -50,879 | 110,122 | -0.462 | 1 | 101.2 | 365 | 150 |
| 1 | 0.01 | symmetric | unkind | traded | 0.001347 | 10.3 | 79336 | 51,642 | 265,903 | -491,873 | -225,971 | 5.149 | -9.525 | -4.376 | -0.6236 | 4 | -56,493 | 103,689 | -0.5448 | 1 | 127.9 | 400.8 | 360.9 |
| 1 | 0.1 | inventory | kind | full | 0.01347 | 12.67 | 69622 | 69,622 | 349,768 | -731,901 | -382,133 | 5.024 | -10.51 | -5.489 | -0.7822 | 4 | -95,533 | 16,414 | -5.82 | 0 | 0.9732 | 5 | 0 |
| 1 | 0.1 | inventory | kind | traded | 0.01347 | 12.68 | 73173 | 45,968 | 239,922 | -534,853 | -294,931 | 5.219 | -11.64 | -6.416 | -0.9144 | 4 | -73,733 | 14,716 | -5.01 | 0 | 0.9155 | 5.82 | -0.433 |
| 1 | 0.1 | inventory | unkind | full | 0.01347 | 12.7 | 67584 | 67,584 | 340,446 | -726,056 | -385,610 | 5.037 | -10.74 | -5.706 | -0.8132 | 4 | -96,403 | 16,915 | -5.699 | 0 | 1.008 | 7 | 0 |
| 1 | 0.1 | inventory | unkind | traded | 0.01347 | 12.71 | 69518 | 44,384 | 232,852 | -529,098 | -296,245 | 5.246 | -11.92 | -6.675 | -0.9513 | 4 | -74,061 | 14,887 | -4.975 | 0 | 0.9723 | 6.193 | -0.51 |
| 1 | 0.1 | symmetric | kind | full | 0.01347 | 12.7 | 64280 | 64,280 | 408,120 | -401,729 | 6,390 | 6.349 | -6.25 | 0.09941 | 0.01417 | 4 | 1,598 | 37,216 | 0.04293 | 2 | 73.47 | 213 | 124 |
| 1 | 0.1 | symmetric | kind | traded | 0.01347 | 12.7 | 64280 | 43,146 | 273,928 | -380,830 | -106,902 | 6.349 | -8.827 | -2.478 | -0.3531 | 4 | -26,725 | 62,492 | -0.4277 | 2 | 114.7 | 383.2 | 349.9 |
| 1 | 0.1 | symmetric | unkind | full | 0.01347 | 12.7 | 63078 | 63,078 | 400,487 | -397,261 | 3,227 | 6.349 | -6.298 | 0.05116 | 0.007291 | 4 | 806.7 | 42,008 | 0.0192 | 2 | 74.48 | 242 | 116 |
| 1 | 0.1 | symmetric | unkind | traded | 0.01347 | 12.7 | 63078 | 42,477 | 269,682 | -367,099 | -97,418 | 6.349 | -8.642 | -2.293 | -0.3268 | 4 | -24,354 | 70,936 | -0.3433 | 2 | 115.1 | 393.1 | 361.7 |
| 1 | 1 | inventory | kind | full | 0.1347 | 37.59 | 15154 | 15,154 | 145,393 | -185,370 | -39,977 | 9.594 | -12.23 | -2.638 | -0.3761 | 4 | -9,994 | 3,218 | -3.106 | 0 | 0.1629 | 2 | 0 |
| 1 | 1 | inventory | kind | traded | 0.1347 | 37.61 | 22251 | 14,968 | 121,560 | -203,663 | -82,103 | 8.121 | -13.61 | -5.485 | -0.7818 | 4 | -20,526 | 5,382 | -3.814 | 0 | 0.2633 | 2.366 | -0.178 |
| 1 | 1 | inventory | unkind | full | 0.1347 | 37.94 | 14044 | 14,044 | 135,594 | -211,500 | -75,906 | 9.655 | -15.06 | -5.405 | -0.7705 | 4 | -18,977 | 5,059 | -3.751 | 0 | 0.2401 | 2 | 0 |
| 1 | 1 | inventory | unkind | traded | 0.1347 | 37.81 | 19420 | 14,051 | 114,877 | -209,668 | -94,792 | 8.176 | -14.92 | -6.746 | -0.9616 | 4 | -23,698 | 6,156 | -3.85 | 0 | 0.2961 | 2.338 | -0.132 |
| 1 | 1 | symmetric | kind | full | 0.1347 | 37.3 | 9267 | 9,267 | 172,852 | 147,431 | 320,283 | 18.65 | 15.91 | 34.56 | 4.928 | 4 | 80,071 | 59,942 | 1.336 | 3 | 65.44 | 207 | 99 |
| 1 | 1 | symmetric | kind | traded | 0.1347 | 37.3 | 9267 | 7,670 | 143,070 | 133,936 | 277,006 | 18.65 | 17.46 | 36.11 | 5.15 | 4 | 69,251 | 36,905 | 1.876 | 3 | 61.5 | 149.7 | 147.8 |
| 1 | 1 | symmetric | unkind | full | 0.1347 | 37.3 | 9139 | 9,139 | 170,465 | 143,241 | 313,706 | 18.65 | 15.67 | 34.33 | 4.894 | 4 | 78,427 | 52,826 | 1.485 | 3 | 68.25 | 184 | 131 |
| 1 | 1 | symmetric | unkind | traded | 0.1347 | 37.3 | 9139 | 7,576 | 141,305 | 134,729 | 276,034 | 18.65 | 17.78 | 36.44 | 5.196 | 4 | 69,008 | 33,693 | 2.048 | 3 | 63.3 | 164.9 | 163.1 |
| 0.1 | 0.01 | inventory | kind | full | 0.002285 | 6.076 | 151120 | 151,120 | 446,223 | -1,249,702 | -803,479 | 2.953 | -8.27 | -5.317 | -0.7579 | 4 | -200,870 | 41,484 | -4.842 | 0 | 3.213 | 18 | 2 |
| 0.1 | 0.01 | inventory | kind | traded | 0.002285 | 6.09 | 154702 | 73,989 | 220,075 | -654,188 | -434,113 | 2.974 | -8.842 | -5.867 | -0.8364 | 4 | -108,528 | 25,444 | -4.265 | 0 | 3.764 | 19.27 | -1.801 |
| 0.1 | 0.01 | inventory | unkind | full | 0.002285 | 6.075 | 146310 | 146,310 | 432,019 | -1,218,845 | -786,826 | 2.953 | -8.331 | -5.378 | -0.7666 | 4 | -196,706 | 40,752 | -4.827 | 0 | 3.163 | 17 | 2 |
| 0.1 | 0.01 | inventory | unkind | traded | 0.002285 | 6.09 | 149776 | 72,320 | 215,098 | -643,008 | -427,910 | 2.974 | -8.891 | -5.917 | -0.8435 | 4 | -106,977 | 25,283 | -4.231 | 0 | 3.742 | 18.81 | -1.479 |
| 0.1 | 0.01 | symmetric | kind | full | 0.002285 | 6.1 | 151180 | 151,180 | 460,757 | -1,624,860 | -1,164,103 | 3.048 | -10.75 | -7.7 | -1.098 | 4 | -291,026 | 100,518 | -2.895 | 0 | 165.9 | 349 | 150 |
| 0.1 | 0.01 | symmetric | kind | traded | 0.002285 | 6.1 | 151180 | 74,171 | 225,997 | -825,193 | -599,196 | 3.047 | -11.13 | -8.079 | -1.152 | 4 | -149,799 | 185,986 | -0.8054 | 2 | 288.2 | 835.6 | 801.3 |
| 0.1 | 0.01 | symmetric | unkind | full | 0.002285 | 6.1 | 145787 | 145,787 | 444,315 | -1,459,350 | -1,015,034 | 3.048 | -10.01 | -6.962 | -0.9925 | 4 | -253,759 | 95,768 | -2.65 | 1 | 157.9 | 303 | 103 |
| 0.1 | 0.01 | symmetric | unkind | traded | 0.002285 | 6.1 | 145787 | 72,282 | 220,240 | -807,940 | -587,700 | 3.047 | -11.18 | -8.131 | -1.159 | 4 | -146,925 | 184,107 | -0.798 | 2 | 277.7 | 832.6 | 799.5 |
| 0.1 | 0.1 | inventory | kind | full | 0.02285 | 7.458 | 123825 | 123,825 | 364,113 | -1,025,778 | -661,665 | 2.941 | -8.284 | -5.344 | -0.7617 | 4 | -165,416 | 30,687 | -5.391 | 0 | 1.048 | 6 | -1 |
| 0.1 | 0.1 | inventory | kind | traded | 0.02285 | 7.51 | 147982 | 66,181 | 205,873 | -601,587 | -395,713 | 3.111 | -9.09 | -5.979 | -0.8524 | 4 | -98,928 | 23,116 | -4.28 | 0 | 0.9803 | 6.255 | -0.039 |
| 0.1 | 0.1 | inventory | unkind | full | 0.02285 | 7.497 | 118371 | 118,371 | 349,040 | -1,012,015 | -662,975 | 2.949 | -8.55 | -5.601 | -0.7984 | 4 | -165,744 | 30,980 | -5.35 | 0 | 1.109 | 7 | -1 |
| 0.1 | 0.1 | inventory | unkind | traded | 0.02285 | 7.557 | 131386 | 62,501 | 196,354 | -587,823 | -391,469 | 3.142 | -9.405 | -6.263 | -0.8929 | 4 | -97,867 | 23,252 | -4.209 | 0 | 1.111 | 7.715 | -0.302 |
| 0.1 | 0.1 | symmetric | kind | full | 0.02285 | 7.5 | 118882 | 118,882 | 445,514 | -988,760 | -543,246 | 3.748 | -8.317 | -4.57 | -0.6514 | 4 | -135,811 | 172,724 | -0.7863 | 2 | 155.7 | 474 | 98 |
| 0.1 | 0.1 | symmetric | kind | traded | 0.02285 | 7.5 | 118882 | 62,185 | 232,995 | -608,643 | -375,648 | 3.747 | -9.788 | -6.041 | -0.8612 | 4 | -93,912 | 134,864 | -0.6963 | 2 | 239.1 | 751.9 | 717.9 |
| 0.1 | 0.1 | symmetric | unkind | full | 0.02285 | 7.5 | 115191 | 115,191 | 431,679 | -953,843 | -522,164 | 3.748 | -8.281 | -4.533 | -0.6462 | 4 | -130,541 | 194,327 | -0.6718 | 2 | 157.4 | 529 | 45 |
| 0.1 | 0.1 | symmetric | unkind | traded | 0.02285 | 7.5 | 115191 | 60,813 | 227,853 | -593,433 | -365,580 | 3.747 | -9.758 | -6.012 | -0.857 | 4 | -91,395 | 121,746 | -0.7507 | 2 | 230.5 | 727 | 692.3 |
| 0.1 | 1 | inventory | kind | full | 0.2285 | 22.16 | 30552 | 30,552 | 170,032 | -237,376 | -67,344 | 5.565 | -7.77 | -2.204 | -0.3144 | 4 | -16,836 | 4,686 | -3.593 | 0 | 0.09683 | 2 | 0 |
| 0.1 | 1 | inventory | kind | traded | 0.2285 | 22.17 | 59467 | 26,881 | 136,400 | -268,532 | -132,132 | 5.074 | -9.99 | -4.915 | -0.7008 | 4 | -33,033 | 9,004 | -3.669 | 0 | 0.2917 | 2.843 | -0.136 |
| 0.1 | 1 | inventory | unkind | full | 0.2285 | 22.54 | 27594 | 27,594 | 155,013 | -280,170 | -125,156 | 5.618 | -10.15 | -4.536 | -0.6469 | 4 | -31,289 | 7,799 | -4.012 | 0 | 0.2607 | 3 | 0 |
| 0.1 | 1 | inventory | unkind | traded | 0.2285 | 22.46 | 44698 | 24,541 | 126,463 | -270,755 | -144,292 | 5.153 | -11.03 | -5.88 | -0.8384 | 4 | -36,073 | 9,539 | -3.782 | 0 | 0.356 | 3.462 | -0.367 |
| 0.1 | 1 | symmetric | kind | full | 0.2285 | 22.1 | 17351 | 17,351 | 191,649 | 238,592 | 430,241 | 11.05 | 13.75 | 24.8 | 3.538 | 4 | 107,560 | 131,524 | 0.8178 | 3 | 101.1 | 371 | 29 |
| 0.1 | 1 | symmetric | kind | traded | 0.2285 | 22.1 | 17351 | 14,415 | 159,226 | 212,036 | 371,263 | 11.05 | 14.71 | 25.75 | 3.674 | 4 | 92,816 | 81,078 | 1.145 | 3 | 85.23 | 248 | 117.7 |
| 0.1 | 1 | symmetric | unkind | full | 0.2285 | 22.1 | 17014 | 17,014 | 187,926 | 233,074 | 421,000 | 11.05 | 13.7 | 24.74 | 3.53 | 4 | 105,250 | 128,962 | 0.8161 | 3 | 100.4 | 369 | 28 |
| 0.1 | 1 | symmetric | unkind | traded | 0.2285 | 22.1 | 17014 | 14,189 | 156,723 | 209,790 | 366,513 | 11.05 | 14.79 | 25.83 | 3.685 | 4 | 91,628 | 82,954 | 1.105 | 3 | 86.19 | 255.7 | 115.9 |

## Table 5b. The quoter's profit by day

USDT, before fees, per UTC day of the test period.

| requote_s | paper_gamma | strategy | fills_rule | size_rule | day | pnl |
|---|---|---|---|---|---|---|
| 1 | 0.01 | inventory | kind | full | 2024-03-26 | -128,471 |
| 1 | 0.01 | inventory | kind | full | 2024-03-27 | -126,325 |
| 1 | 0.01 | inventory | kind | full | 2024-03-28 | -104,876 |
| 1 | 0.01 | inventory | kind | full | 2024-03-29 | -52,282 |
| 1 | 0.01 | inventory | kind | traded | 2024-03-26 | -103,900 |
| 1 | 0.01 | inventory | kind | traded | 2024-03-27 | -103,806 |
| 1 | 0.01 | inventory | kind | traded | 2024-03-28 | -79,867 |
| 1 | 0.01 | inventory | kind | traded | 2024-03-29 | -38,288 |
| 1 | 0.01 | inventory | unkind | full | 2024-03-26 | -128,398 |
| 1 | 0.01 | inventory | unkind | full | 2024-03-27 | -127,089 |
| 1 | 0.01 | inventory | unkind | full | 2024-03-28 | -103,129 |
| 1 | 0.01 | inventory | unkind | full | 2024-03-29 | -52,123 |
| 1 | 0.01 | inventory | unkind | traded | 2024-03-26 | -102,798 |
| 1 | 0.01 | inventory | unkind | traded | 2024-03-27 | -104,050 |
| 1 | 0.01 | inventory | unkind | traded | 2024-03-28 | -78,947 |
| 1 | 0.01 | inventory | unkind | traded | 2024-03-29 | -38,319 |
| 1 | 0.01 | symmetric | kind | full | 2024-03-26 | -124,359 |
| 1 | 0.01 | symmetric | kind | full | 2024-03-27 | -222,183 |
| 1 | 0.01 | symmetric | kind | full | 2024-03-28 | 285,197 |
| 1 | 0.01 | symmetric | kind | full | 2024-03-29 | -178,869 |
| 1 | 0.01 | symmetric | kind | traded | 2024-03-26 | -42,448 |
| 1 | 0.01 | symmetric | kind | traded | 2024-03-27 | -179,180 |
| 1 | 0.01 | symmetric | kind | traded | 2024-03-28 | 241,161 |
| 1 | 0.01 | symmetric | kind | traded | 2024-03-29 | -260,544 |
| 1 | 0.01 | symmetric | unkind | full | 2024-03-26 | -121,714 |
| 1 | 0.01 | symmetric | unkind | full | 2024-03-27 | -202,401 |
| 1 | 0.01 | symmetric | unkind | full | 2024-03-28 | 275,736 |
| 1 | 0.01 | symmetric | unkind | full | 2024-03-29 | -155,138 |
| 1 | 0.01 | symmetric | unkind | traded | 2024-03-26 | -33,094 |
| 1 | 0.01 | symmetric | unkind | traded | 2024-03-27 | -166,070 |
| 1 | 0.01 | symmetric | unkind | traded | 2024-03-28 | 224,030 |
| 1 | 0.01 | symmetric | unkind | traded | 2024-03-29 | -250,837 |
| 1 | 0.1 | inventory | kind | full | 2024-03-26 | -116,435 |
| 1 | 0.1 | inventory | kind | full | 2024-03-27 | -122,876 |
| 1 | 0.1 | inventory | kind | full | 2024-03-28 | -92,444 |
| 1 | 0.1 | inventory | kind | full | 2024-03-29 | -50,378 |
| 1 | 0.1 | inventory | kind | traded | 2024-03-26 | -91,999 |
| 1 | 0.1 | inventory | kind | traded | 2024-03-27 | -101,481 |
| 1 | 0.1 | inventory | kind | traded | 2024-03-28 | -65,499 |
| 1 | 0.1 | inventory | kind | traded | 2024-03-29 | -35,952 |
| 1 | 0.1 | inventory | unkind | full | 2024-03-26 | -117,929 |
| 1 | 0.1 | inventory | unkind | full | 2024-03-27 | -124,614 |
| 1 | 0.1 | inventory | unkind | full | 2024-03-28 | -93,182 |
| 1 | 0.1 | inventory | unkind | full | 2024-03-29 | -49,885 |
| 1 | 0.1 | inventory | unkind | traded | 2024-03-26 | -92,827 |
| 1 | 0.1 | inventory | unkind | traded | 2024-03-27 | -101,919 |
| 1 | 0.1 | inventory | unkind | traded | 2024-03-28 | -65,658 |
| 1 | 0.1 | inventory | unkind | traded | 2024-03-29 | -35,841 |
| 1 | 0.1 | symmetric | kind | full | 2024-03-26 | -394.5 |
| 1 | 0.1 | symmetric | kind | full | 2024-03-27 | -87,923 |
| 1 | 0.1 | symmetric | kind | full | 2024-03-28 | 94,340 |
| 1 | 0.1 | symmetric | kind | full | 2024-03-29 | 367.9 |
| 1 | 0.1 | symmetric | kind | traded | 2024-03-26 | 8,879 |
| 1 | 0.1 | symmetric | kind | traded | 2024-03-27 | -92,873 |
| 1 | 0.1 | symmetric | kind | traded | 2024-03-28 | 131,294 |
| 1 | 0.1 | symmetric | kind | traded | 2024-03-29 | -154,202 |
| 1 | 0.1 | symmetric | unkind | full | 2024-03-26 | 14,999 |
| 1 | 0.1 | symmetric | unkind | full | 2024-03-27 | -107,267 |
| 1 | 0.1 | symmetric | unkind | full | 2024-03-28 | 97,185 |
| 1 | 0.1 | symmetric | unkind | full | 2024-03-29 | -1,690 |
| 1 | 0.1 | symmetric | unkind | traded | 2024-03-26 | 13,827 |
| 1 | 0.1 | symmetric | unkind | traded | 2024-03-27 | -106,019 |
| 1 | 0.1 | symmetric | unkind | traded | 2024-03-28 | 157,561 |
| 1 | 0.1 | symmetric | unkind | traded | 2024-03-29 | -162,786 |
| 1 | 1 | inventory | kind | full | 2024-03-26 | -12,433 |
| 1 | 1 | inventory | kind | full | 2024-03-27 | -17,265 |
| 1 | 1 | inventory | kind | full | 2024-03-28 | -8,165 |
| 1 | 1 | inventory | kind | full | 2024-03-29 | -2,115 |
| 1 | 1 | inventory | kind | traded | 2024-03-26 | -24,875 |
| 1 | 1 | inventory | kind | traded | 2024-03-27 | -32,758 |
| 1 | 1 | inventory | kind | traded | 2024-03-28 | -16,795 |
| 1 | 1 | inventory | kind | traded | 2024-03-29 | -7,675 |
| 1 | 1 | inventory | unkind | full | 2024-03-26 | -23,206 |
| 1 | 1 | inventory | unkind | full | 2024-03-27 | -29,903 |
| 1 | 1 | inventory | unkind | full | 2024-03-28 | -16,644 |
| 1 | 1 | inventory | unkind | full | 2024-03-29 | -6,153 |
| 1 | 1 | inventory | unkind | traded | 2024-03-26 | -28,691 |
| 1 | 1 | inventory | unkind | traded | 2024-03-27 | -37,585 |
| 1 | 1 | inventory | unkind | traded | 2024-03-28 | -19,676 |
| 1 | 1 | inventory | unkind | traded | 2024-03-29 | -8,840 |
| 1 | 1 | symmetric | kind | full | 2024-03-26 | 145,979 |
| 1 | 1 | symmetric | kind | full | 2024-03-27 | 124,849 |
| 1 | 1 | symmetric | kind | full | 2024-03-28 | -99,049 |
| 1 | 1 | symmetric | kind | full | 2024-03-29 | 148,504 |
| 1 | 1 | symmetric | kind | traded | 2024-03-26 | 112,905 |
| 1 | 1 | symmetric | kind | traded | 2024-03-27 | 117,851 |
| 1 | 1 | symmetric | kind | traded | 2024-03-28 | -39,410 |
| 1 | 1 | symmetric | kind | traded | 2024-03-29 | 85,659 |
| 1 | 1 | symmetric | unkind | full | 2024-03-26 | 143,700 |
| 1 | 1 | symmetric | unkind | full | 2024-03-27 | 127,915 |
| 1 | 1 | symmetric | unkind | full | 2024-03-28 | -79,433 |
| 1 | 1 | symmetric | unkind | full | 2024-03-29 | 121,525 |
| 1 | 1 | symmetric | unkind | traded | 2024-03-26 | 110,440 |
| 1 | 1 | symmetric | unkind | traded | 2024-03-27 | 119,504 |
| 1 | 1 | symmetric | unkind | traded | 2024-03-28 | -27,606 |
| 1 | 1 | symmetric | unkind | traded | 2024-03-29 | 73,696 |
| 0.1 | 0.01 | inventory | kind | full | 2024-03-26 | -245,873 |
| 0.1 | 0.01 | inventory | kind | full | 2024-03-27 | -285,054 |
| 0.1 | 0.01 | inventory | kind | full | 2024-03-28 | -176,241 |
| 0.1 | 0.01 | inventory | kind | full | 2024-03-29 | -96,311 |
| 0.1 | 0.01 | inventory | kind | traded | 2024-03-26 | -134,858 |
| 0.1 | 0.01 | inventory | kind | traded | 2024-03-27 | -163,296 |
| 0.1 | 0.01 | inventory | kind | traded | 2024-03-28 | -87,824 |
| 0.1 | 0.01 | inventory | kind | traded | 2024-03-29 | -48,135 |
| 0.1 | 0.01 | inventory | unkind | full | 2024-03-26 | -242,309 |
| 0.1 | 0.01 | inventory | unkind | full | 2024-03-27 | -278,819 |
| 0.1 | 0.01 | inventory | unkind | full | 2024-03-28 | -171,266 |
| 0.1 | 0.01 | inventory | unkind | full | 2024-03-29 | -94,433 |
| 0.1 | 0.01 | inventory | unkind | traded | 2024-03-26 | -132,701 |
| 0.1 | 0.01 | inventory | unkind | traded | 2024-03-27 | -161,958 |
| 0.1 | 0.01 | inventory | unkind | traded | 2024-03-28 | -85,729 |
| 0.1 | 0.01 | inventory | unkind | traded | 2024-03-29 | -47,522 |
| 0.1 | 0.01 | symmetric | kind | full | 2024-03-26 | -7,840 |
| 0.1 | 0.01 | symmetric | kind | full | 2024-03-27 | -482,886 |
| 0.1 | 0.01 | symmetric | kind | full | 2024-03-28 | -342,728 |
| 0.1 | 0.01 | symmetric | kind | full | 2024-03-29 | -330,649 |
| 0.1 | 0.01 | symmetric | kind | traded | 2024-03-26 | 14,221 |
| 0.1 | 0.01 | symmetric | kind | traded | 2024-03-27 | -240,920 |
| 0.1 | 0.01 | symmetric | kind | traded | 2024-03-28 | 248,048 |
| 0.1 | 0.01 | symmetric | kind | traded | 2024-03-29 | -620,546 |
| 0.1 | 0.01 | symmetric | unkind | full | 2024-03-26 | 26,058 |
| 0.1 | 0.01 | symmetric | unkind | full | 2024-03-27 | -389,322 |
| 0.1 | 0.01 | symmetric | unkind | full | 2024-03-28 | -364,475 |
| 0.1 | 0.01 | symmetric | unkind | full | 2024-03-29 | -287,295 |
| 0.1 | 0.01 | symmetric | unkind | traded | 2024-03-26 | 6,320 |
| 0.1 | 0.01 | symmetric | unkind | traded | 2024-03-27 | -237,370 |
| 0.1 | 0.01 | symmetric | unkind | traded | 2024-03-28 | 253,595 |
| 0.1 | 0.01 | symmetric | unkind | traded | 2024-03-29 | -610,245 |
| 0.1 | 0.1 | inventory | kind | full | 2024-03-26 | -194,459 |
| 0.1 | 0.1 | inventory | kind | full | 2024-03-27 | -229,035 |
| 0.1 | 0.1 | inventory | kind | full | 2024-03-28 | -151,613 |
| 0.1 | 0.1 | inventory | kind | full | 2024-03-29 | -86,558 |
| 0.1 | 0.1 | inventory | kind | traded | 2024-03-26 | -116,678 |
| 0.1 | 0.1 | inventory | kind | traded | 2024-03-27 | -153,717 |
| 0.1 | 0.1 | inventory | kind | traded | 2024-03-28 | -77,899 |
| 0.1 | 0.1 | inventory | kind | traded | 2024-03-29 | -47,420 |
| 0.1 | 0.1 | inventory | unkind | full | 2024-03-26 | -195,678 |
| 0.1 | 0.1 | inventory | unkind | full | 2024-03-27 | -229,755 |
| 0.1 | 0.1 | inventory | unkind | full | 2024-03-28 | -151,257 |
| 0.1 | 0.1 | inventory | unkind | full | 2024-03-29 | -86,284 |
| 0.1 | 0.1 | inventory | unkind | traded | 2024-03-26 | -116,692 |
| 0.1 | 0.1 | inventory | unkind | traded | 2024-03-27 | -152,711 |
| 0.1 | 0.1 | inventory | unkind | traded | 2024-03-28 | -75,388 |
| 0.1 | 0.1 | inventory | unkind | traded | 2024-03-29 | -46,679 |
| 0.1 | 0.1 | symmetric | kind | full | 2024-03-26 | 190,355 |
| 0.1 | 0.1 | symmetric | kind | full | 2024-03-27 | -211,239 |
| 0.1 | 0.1 | symmetric | kind | full | 2024-03-28 | -588,668 |
| 0.1 | 0.1 | symmetric | kind | full | 2024-03-29 | 66,306 |
| 0.1 | 0.1 | symmetric | kind | traded | 2024-03-26 | 75,740 |
| 0.1 | 0.1 | symmetric | kind | traded | 2024-03-27 | -191,938 |
| 0.1 | 0.1 | symmetric | kind | traded | 2024-03-28 | 168,019 |
| 0.1 | 0.1 | symmetric | kind | traded | 2024-03-29 | -427,469 |
| 0.1 | 0.1 | symmetric | unkind | full | 2024-03-26 | 204,779 |
| 0.1 | 0.1 | symmetric | unkind | full | 2024-03-27 | -162,876 |
| 0.1 | 0.1 | symmetric | unkind | full | 2024-03-28 | -665,291 |
| 0.1 | 0.1 | symmetric | unkind | full | 2024-03-29 | 101,224 |
| 0.1 | 0.1 | symmetric | unkind | traded | 2024-03-26 | 76,728 |
| 0.1 | 0.1 | symmetric | unkind | traded | 2024-03-27 | -174,920 |
| 0.1 | 0.1 | symmetric | unkind | traded | 2024-03-28 | 129,978 |
| 0.1 | 0.1 | symmetric | unkind | traded | 2024-03-29 | -397,366 |
| 0.1 | 1 | inventory | kind | full | 2024-03-26 | -20,649 |
| 0.1 | 1 | inventory | kind | full | 2024-03-27 | -28,026 |
| 0.1 | 1 | inventory | kind | full | 2024-03-28 | -11,698 |
| 0.1 | 1 | inventory | kind | full | 2024-03-29 | -6,971 |
| 0.1 | 1 | inventory | kind | traded | 2024-03-26 | -38,938 |
| 0.1 | 1 | inventory | kind | traded | 2024-03-27 | -55,307 |
| 0.1 | 1 | inventory | kind | traded | 2024-03-28 | -23,679 |
| 0.1 | 1 | inventory | kind | traded | 2024-03-29 | -14,208 |
| 0.1 | 1 | inventory | unkind | full | 2024-03-26 | -38,591 |
| 0.1 | 1 | inventory | unkind | full | 2024-03-27 | -49,004 |
| 0.1 | 1 | inventory | unkind | full | 2024-03-28 | -23,768 |
| 0.1 | 1 | inventory | unkind | full | 2024-03-29 | -13,793 |
| 0.1 | 1 | inventory | unkind | traded | 2024-03-26 | -43,428 |
| 0.1 | 1 | inventory | unkind | traded | 2024-03-27 | -59,017 |
| 0.1 | 1 | inventory | unkind | traded | 2024-03-28 | -26,039 |
| 0.1 | 1 | inventory | unkind | traded | 2024-03-29 | -15,808 |
| 0.1 | 1 | symmetric | kind | full | 2024-03-26 | 205,385 |
| 0.1 | 1 | symmetric | kind | full | 2024-03-27 | 206,570 |
| 0.1 | 1 | symmetric | kind | full | 2024-03-28 | -281,405 |
| 0.1 | 1 | symmetric | kind | full | 2024-03-29 | 299,692 |
| 0.1 | 1 | symmetric | kind | traded | 2024-03-26 | 160,215 |
| 0.1 | 1 | symmetric | kind | traded | 2024-03-27 | 165,125 |
| 0.1 | 1 | symmetric | kind | traded | 2024-03-28 | -149,307 |
| 0.1 | 1 | symmetric | kind | traded | 2024-03-29 | 195,230 |
| 0.1 | 1 | symmetric | unkind | full | 2024-03-26 | 202,760 |
| 0.1 | 1 | symmetric | unkind | full | 2024-03-27 | 204,804 |
| 0.1 | 1 | symmetric | unkind | full | 2024-03-28 | -276,776 |
| 0.1 | 1 | symmetric | unkind | full | 2024-03-29 | 290,212 |
| 0.1 | 1 | symmetric | unkind | traded | 2024-03-26 | 162,210 |
| 0.1 | 1 | symmetric | unkind | traded | 2024-03-27 | 162,591 |
| 0.1 | 1 | symmetric | unkind | traded | 2024-03-28 | -155,981 |
| 0.1 | 1 | symmetric | unkind | traded | 2024-03-29 | 197,692 |

## Table 6. Spread estimators on simulated prices

Daily volatility 3%, 300 days per run. Basis points.

| true_spread_bps | roll_mean_bps | roll_sd_bps | cs_mean_bps | cs_sd_bps | ar2_mean_bps | ar2_sd_bps | ar_mean_bps | ar_sd_bps |
|---|---|---|---|---|---|---|---|---|
| 200 | 189.8 | 75.41 | 243 | 10.92 | 173 | 11.41 | 198.2 | 21.25 |
| 50 | 73.84 | 75.89 | 142.9 | 8.202 | 121 | 9.598 | 44.42 | 41.87 |
| 10 | 66.7 | 74.49 | 121.9 | 7.465 | 117.4 | 9.433 | 29.76 | 39.02 |
| 1 | 66.73 | 74.47 | 120.2 | 7.392 | 117.3 | 9.41 | 29.24 | 38.9 |
| 0 | 66.77 | 74.47 | 120.2 | 7.395 | 117.3 | 9.409 | 29.22 | 38.92 |

## Table 7. Spread estimators on real daily prices

BTCUSDT perpetual daily bars, 2023-06-01 to 2024-03-31. The quoted spread is the mean over the one-second bars.

| estimator | spread_bps | days |
|---|---|---|
| Roll | 164 | 305 |
| Corwin-Schultz | 99.78 | 305 |
| Abdi-Ranaldo, two-day | 84.13 | 305 |
| Abdi-Ranaldo, whole sample | 92.07 | 305 |
| Quoted spread, measured | 0.01581 | 5 |
