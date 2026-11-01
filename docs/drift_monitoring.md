# Drift monitoring (PSI)

`scripts/drift_psi.py` compares feature and model-score distributions against a reference window. It uses no laundering labels, so it could run in production. PSI rule of thumb: below 0.10 stable, 0.10 to 0.25 moderate, above 0.25 large.

## Table A: later days vs the training days (Sep 1-6)
- **Stable:** `amount_paid` (0.025 to 0.062) and `hour_of_day` (0.014 to 0.062).
- **Large drift on every day from Sep 7 to Sep 10:** `payment_format` (1.79), the six history features (0.35 to 3.9) and the model score (0.36 to 0.61).
- Sep 11 to Sep 18 have only 11 to 396 rows a day, so they are skipped (PSI on a few hundred rows is noise).

Two causes, both read from the data and not tested further:
1. **A payment format disappears.** "Reinvestment" is 14.8% of training rows and 0% of validation and test rows. A bucket that goes empty gives a very large PSI.
2. **History features grow with time by construction.** "Sender's earlier transactions" counts everything before the current row, so later days have larger values than the training average.

So these alarms are real changes in the data, but they are not evidence that laundering behaviour changed. Against a fixed reference window, the history features will always alarm in this setup. A production version would use a rolling reference or compare rates, not cumulative counts.

## Table B: clean demo (reference Sep 5, window Sep 6, then simulated shifts)
| Window | amount_paid | payment_format | model score |
|---|---|---|---|
| Sep 6, no shift | 0.000 | 0.000 | 0.005 |
| Simulated: amounts x3 | 0.144 (moderate) | 0.000 | 0.027 |
| Simulated: 20% of rows relabelled ACH | 0.000 | 0.196 (moderate) | 0.081 |

- Each simulated shift is flagged on the feature that was changed, and on no other feature except those that already moved on the baseline day (`receiver_received_before`, 0.286, from history growth).
- **The model-score PSI stayed below 0.10 for both shifts.** Monitoring only the score would have missed both. Feature-level PSI caught them. That is why the script monitors all nine features and the score.

## Limits
- The shifts are simulated, with sizes I chose (x3, 20%). They show the monitor works, not how sensitive it is to real drift.
- Ten equal-sized buckets from the reference window; a different bucket count changes the values.
- PSI says the data moved. It does not say the model got worse.
