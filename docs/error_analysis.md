# Error analysis (test days, model v1)

The 20 highest-scored false positives and the 20 lowest-scored laundering transactions. These are the **extremes**, not a typical sample, so they show failure modes and do not measure how often each one happens. A "false positive" is an alert on a transaction whose simulator label is not laundering.

## Worst false positives (ranks 9 to 45 of 863,900)
- All 20 are **ACH** payments, with scores of 0.976 to 0.979.
- Per-alert reasons show the ACH flag adding about +3.1 to the score in every case, then a large sender history (a high earlier total sent) adding about +0.5 each.
- Amounts range from about 1,000 to 20,000, so the amount rule would flag only some of them.
- **Reading:** at the top of the queue the model is mostly saying "ACH plus an active sender". Real and false alerts there look alike on the model's features, which matches the SHAP finding that ACH dominates.

## Worst misses (ranks 169,000 to 249,000 of 863,900)
- 11 of 20 are **not ACH**: 6 Cheque, 3 Bitcoin, 2 Credit Card. All 11 are laundering with no listed pattern. Four have tiny amounts (0.05 to 7.80); the others range from 45 to 448,921. The ACH rule cannot catch them either.
- 9 of 20 are **ACH**, mostly with small amounts (10 to 770, one 51,610). Seven belong to listed patterns (fan-in, bipartite, scatter-gather twice, gather-scatter, fan-out twice); two have no listed pattern. The rule flags them, but the model scores them low (under 0.1) because the small amount pulls the score down more than ACH pushes it up.
- Even the lowest-scored laundering transaction sits at rank 249,135, in the top 29% of rows. That is why the model reaches near-complete recall only at large alert volumes.

## What this suggests (not tested)
- Features that describe the **relationship** between sender and receiver, or repeated small payments over time, are not in the model. That may be why small ACH pattern payments score low. I have not tested this.
- Non-ACH laundering (no listed pattern) is the group both the rule and the model handle worst.
- A combined "rules first" ranking could keep the small ACH misses in the queue, but it did not help at small budgets in the evaluation.

## Limits
- Forty cases from one run of one model on simulated data. No claim about frequency or about real transactions.
- Reasons are SHAP contributions of the model, not causes in the laundering process.
