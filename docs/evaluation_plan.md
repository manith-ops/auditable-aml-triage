# Final evaluation plan (written before the test days were scored)

Committed before any test-day result was computed, so the choices below cannot be adjusted after seeing results.

## Rules of the evaluation
- **Test days: Sep 9-18.** They are scored **once**, with the frozen model `v1` (`artifacts/xgb_v1.json`).
- No retraining, no tuning, no feature changes, no threshold changes after looking at test results.
- If something is wrong (a bug), it is fixed and the run is repeated, and the README says it was repeated.
- Prototype on public synthetic data. Results will not transfer to a real bank.

## Metrics (headline is not ROC-AUC)
1. **PR-AUC**, next to the base rate (a random ranker scores about the base rate).
2. **Alert budgets**, defined as a share of the test rows so they do not depend on how many days the test covers: top 0.1% and top 0.5% of rows. For each: precision@k, recall@k, and **false positives per true positive** (alerts that are not laundering, divided by alerts that are).
3. **Rule-matched volume:** for each rule, the model is also scored at the same number of alerts as that rule, so the comparison is fair.

"False positive" here means: an alert on a transaction whose simulator label is `is_laundering = 0`.

## Compared
| Method | Definition |
|---|---|
| ACH rule | alert when payment format is ACH |
| Amount rule | alert when amount > 10,000 |
| Either rule | ACH or amount rule fires |
| Model | top-k by model score |
| Combined | rule-flagged rows first (ranked by model score), then the rest by model score, same total k |

## Breakdowns
- **Recall by laundering pattern**, using the pattern file that ships with the IBM data. It lists 3,209 of the 5,177 laundering transactions (370 attempts, 8 types). The other 1,968 have no listed pattern; they are reported as their own group, "no pattern listed", with no assumption about why.
- **Error analysis:** the 20 highest-scored false positives and the 20 laundering transactions with the lowest scores. For each, say what the model saw and why it may have been wrong.

## Uncertainty
- Report the number of laundering rows in the test days, so the sample size is visible.
- Bootstrap 95% interval (resampling rows, fixed seed) for recall at each budget.

## What this evaluation cannot show
- Real-world performance (simulated labels).
- That the model beats the rules for reasons other than learning generator artifacts (SHAP already shows ACH dominating).
