# Model card: alert-ranking model v1

A prototype built on public synthetic data as a personal project. It has never seen, and must not be used on, real transactions or real customers.

## What it is
- **Task:** score each transaction by how likely the simulator labelled it laundering, so analysts can review the highest-scored ones first. The model ranks. A human decides.
- **Model:** XGBoost gradient-boosted trees (`artifacts/xgb_v1.json`, version `v1`). Up to 500 trees, learning rate 0.1, depth 6, stopped early when validation PR-AUC had not improved for 30 rounds. Laundering is rare, so positive rows are up-weighted by the negative-to-positive ratio in the training days. Fixed seed 42.
- **Inputs (9):** amount paid, hour of day, payment format, and for sender and receiver the number of earlier transactions, earlier total amount, and the number of distinct counterparties seen before (fan-out and fan-in). Counts use only rows before the current one; a dbt test checks that.
- **Outputs:** a score from 0 to 1 and the three strongest SHAP contributions per alert, shown in plain language to the analyst.

## Data
- IBM AMLworld synthetic transactions, HI-Small set (5,078,345 rows), CDLA-Sharing 1.0. Labels come from a simulator, not from real investigations.
- Split by time. Train Sep 1-6: 3,248,921 rows, 2,530 laundering. Validation Sep 7-8: 965,524 rows, 1,036 laundering. Test Sep 9-18: 863,900 rows, 1,611 laundering.
- Validation days were used for early stopping and design choices, so validation numbers are slightly optimistic. The test days were scored once, after [the evaluation plan](evaluation_plan.md) was committed.

## Performance (test days, one run)
| Measure | Result |
|---|---|
| PR-AUC | 0.1206 (random: 0.0019) |
| Top 0.1% of rows (864 alerts) | precision 24.5%, recall 13.2% |
| Top 0.5% of rows (4,320 alerts) | precision 12.6%, recall 33.9% |
| Recall at the ACH rule's alert volume (120,303) | model 95.4%, rule 92.4% |

Recall by laundering pattern, the 95% intervals and the full tables are in the README and `scripts/evaluate_test.py`. The model's score is a ranking and not a calibrated probability: nothing here tests calibration.

## Intended and out-of-scope use
- **Intended:** demonstrating an auditable alert-triage workflow (data tests, time-split evaluation, explanations, audit log, drift checks).
- **Out of scope:** any real monitoring, reporting or customer decision. No claim is made about real-world detection performance.

## Known limitations
- The simulator's labels may carry generator artifacts. SHAP shows the ACH flag dominating the top alerts, so the model largely rediscovers the ACH rule. Its gain over the rule at equal volume is about 3 points on one run.
- At small alert budgets it finds a minority of laundering (13% and 34%). It ranks almost everything inside the top third of rows.
- Weak groups: laundering with no listed pattern, non-ACH laundering, and small ACH payments (see [error analysis](error_analysis.md)).
- Features describe single accounts' history. They do not describe relationships between sender and receiver.
- One run, one split. Stability on other time windows is unknown. The test period (Sep 9-18) is effectively two days: Sep 9-10 hold 99.9% of its rows.
- SHAP reasons are model explanations, not legal adverse-action codes.
- **Fairness:** the data has no demographic attributes, so no fairness audit was done. This is a gap, not a clean result.

## Monitoring and change control
- PSI on all nine features and the score ([drift monitoring](drift_monitoring.md)). Feature-level PSI caught both simulated shifts. Score-level PSI missed them.
- A payment format present in training ("Reinvestment") never appears later, which a fixed-window PSI flags heavily.
- Every analyst action is stored in an append-only audit log with the model version. Any retrained model gets a new version number and MLflow run (with the git commit) before it is used.
- Retraining is run with `make train`. There is no scheduled retraining.
