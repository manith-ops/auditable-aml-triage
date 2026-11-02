# Validation report: alert-ranking model v1 (SR 11-7 style)

Format follows the main sections of the US supervisory guidance on model risk management (SR 11-7): purpose, conceptual soundness, data, outcomes analysis, ongoing monitoring, findings. It is a **self-validation by the model's author on public synthetic data**. SR 11-7 expects independent challenge, which this does not provide. Treat it as a structured self-review, not as a validation opinion.

## 1. Purpose and scope
Model v1 ranks transactions for analyst review. Scope: the XGBoost model, its nine features, its explanations and the surrounding controls. Out of scope: any real data or decisions, LLM summaries (not built), fairness (no demographic data). See [model card](model_card.md).

## 2. Conceptual soundness
- **Task fit:** ranking by risk for a limited review capacity is a reasonable framing. Evaluation uses PR-AUC and alert budgets because laundering is about 0.1-0.2% of rows.
- **Design:** gradient-boosted trees on nine transaction and account-history features, with explanations by SHAP. Simple and auditable.
- **Concern:** the features describe single accounts and amounts, and not sender-receiver relationships. Several laundering patterns in the data are defined by relationships (cycles, fan-in, fan-out). See finding F6.

## 3. Data and controls
| Check | Result |
|---|---|
| Data-quality tests (26) and layer reconciliation | Pass on the real data |
| Bad-batch test (4 injected faults) | All 4 caught (5 tests failed, one fault trips two) |
| Time-based split, defined once | Pass |
| Leakage test (features use earlier rows only) | Pass |
| Rebuild reproducibility (`make all`) | Pass: same validation metrics and a byte-identical demo sample |
| Label source | Simulator, not investigations (limitation) |

## 4. Outcomes analysis
- Test days scored once, after the evaluation plan was committed. Results: PR-AUC 0.1206 (random 0.0019); top 0.1% precision 24.5% and recall 13.2%; top 0.5% precision 12.6% and recall 33.9%; at the ACH rule's volume, recall 95.4% (model) vs 92.4% (rule).
- **Benchmarks:** an ACH rule and an amount rule (> 10,000). The model beats the amount rule by a wide margin (99.9% vs 53.1% recall at that rule's volume). Against the ACH rule the gain is about 3 points.
- **Error analysis:** 20 worst false positives (all ACH) and 20 worst misses (small ACH payments, and non-ACH laundering with no listed pattern). See [error analysis](error_analysis.md).
- **Uncertainty:** bootstrap 95% intervals on recall, with the alert set treated as fixed.

## 5. Ongoing monitoring
PSI on nine features and the score ([drift monitoring](drift_monitoring.md)). Feature-level PSI caught both simulated shifts; score-level PSI missed them. An append-only audit log records every analyst action with the model version.

## 6. Findings
| # | Finding | Severity | Recommended action |
|---|---|---|---|
| F1 | The model largely rediscovers the ACH rule (ACH dominates SHAP; gain over the rule about 3 points at equal volume). Its extra value may reflect a simulator artifact. | High | Test on a dataset from a different generator; report results with and without the payment-format feature. |
| F2 | **The test set is effectively two days.** Sep 9-10 hold 862,792 of 863,900 rows (99.9%); Sep 11-18 have 11-396 rows a day. Results are for a short window, not ten days. | High | Say so wherever results are quoted; evaluate on rolling windows if more data is available. |
| F3 | The training period contains a payment format ("Reinvestment", 14.8% of training rows) that never appears in validation or test. The effect on the model was not tested. | Medium | Retrain without those rows and compare. |
| F4 | Validation days were used for early stopping and design choices, so validation numbers are optimistic. Test days were untouched until the single run. | Low | Keep test days frozen. |
| F5 | No calibration check. Scores are rankings, not probabilities. | Medium | Add a calibration plot before any threshold is used. |
| F6 | No sender-receiver relationship features. The data's pattern types suggest they matter. Weak groups: laundering with no listed pattern, non-ACH, small ACH payments. | Medium | Add graph features (two-hop counterparties) and re-evaluate. |
| F7 | Pattern file lists only 3,209 of 5,177 laundering rows, so recall by pattern leaves 38% as one group. | Low | Report as its own group (done). |
| F8 | Single run and single split. Stability is unknown. | Medium | Repeat across time windows. |
| F9 | PSI thresholds are the common rule of thumb (0.10, 0.25). No owner, schedule or escalation exists. | Medium | Define ownership and a run schedule. |
| F10 | The analyst name in the audit log is self-declared (no login). The hosted demo's log is temporary. | Low | Add authentication before any real use. |
| F11 | No fairness assessment (no demographic attributes). | Not assessed | State as a gap. |
| F12 | Self-validation, not independent. | Structural | Have a second person challenge F1 and F2. |

## 7. Conclusion
The pipeline controls, the leakage protections, the audit log and the reproducibility pass. The model's incremental value over a simple ACH rule is small and may be a simulator artifact (F1), and the test window is short (F2). **Conclusion: fit as a portfolio demonstration of an auditable workflow; not fit for any real use.** No claim about real-world performance is made.
