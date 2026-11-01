# Auditable AML Alert Triage: Requirements

Title: Auditable AML Alert Triage: Explainable Scoring and Human-Reviewed Case Summaries
Status: planning only. No project code until Manith says "go".

## Problem
AML monitoring produces mostly false-positive alerts (commonly cited 90-95%, from PwC analysis around 2017-18; definitions vary). Analysts need ranked, explained, auditable alerts.

## Users
- AML analyst: reviews alerts.
- Model/data owner: watches data quality and drift.

## Why this project
Employers ask for data-quality tests, reconciliation, lineage, audit evidence, model cards, explainability, monitoring. The IBM dataset is crowded with model-centric projects, so do NOT chase AUC. The edge is a finished, tested, documented pipeline with honest evaluation. LLM SAR drafting is only credible as human-in-the-loop with deterministic checks.

## Core features
1. **Pipeline**: raw transactions -> bronze/silver/gold in DuckDB + dbt; data-quality tests (include dbt-expectations); row/amount reconciliation between layers; lineage via dbt docs.
2. **Detection**: a few rule flags + gradient-boosted model (time-based split); simple graph features in SQL (fan-in/fan-out counts, 2-hop counterparties); MLflow tracking; SHAP reason codes per alert.
3. **Analyst queue (Streamlit)**: Claude API drafts a case summary from structured transaction facts ONLY; analyst approves/edits/rejects/escalates; every action goes to an append-only SQLite audit log (who, when, model version, prompt version, decision). Nothing is ever auto-filed. The LLM never decides if a case is suspicious.

## Data
- IBM AMLworld synthetic data. Kaggle: `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`.
- Six sets (HI/LI x Small/Medium/Large). Start with HI-Small (about 5.08M transactions, about 1 laundering per 981). Includes labeled laundering-pattern files.
- Community Data License Agreement (verify exact terms on Kaggle).
- Do not commit raw data; use a download script. Needs a Kaggle account.

## Stack
Python, DuckDB, dbt-core, XGBoost/LightGBM, SHAP, MLflow, Streamlit, SQLite, Claude API, GitHub Actions, Docker Compose. Free-tier demo hosting (Streamlit Community Cloud or Hugging Face Spaces) on precomputed sample alerts. Budget: free tiers + a few dollars of API use. Stretch only: Kafka (Redpanda) + PySpark streaming replay; Airflow.

## Plan (about 10 hrs/week, 3-5 weeks)
- Week 1: repo, download script, dbt layers, tests, lineage docs, CI.
- Week 2: rules, features, time-split model, SHAP, MLflow, Streamlit alert queue, DEPLOY a live demo, README v1.
- Week 3: full evaluation, failure analysis, drift (PSI), bad-batch demo.
- Week 4: human review, audit log, LLM summaries, summary evaluation.
- Week 5: buffer, README, model card, SR 11-7-style validation report, demo GIF.
- Cut order if short on time: streaming, then LLM summaries, then drift dashboards. Never cut evaluation.
- 3-week version: weeks 1-3, no LLM.

## Evaluation
- **Detection**: split by time; report PR-AUC, recall at a fixed alert budget, precision@k, false positives per true positive (define "false positive" precisely); compare rules vs ML vs combined; recall by laundering pattern; review worst misses and false positives. Do not headline ROC-AUC.
- **Data quality**: inject a bad batch; show tests catch it.
- **Drift**: PSI on key features across time windows; simulate a shift.
- **LLM summaries**: hand-label 30-40 cases per claim (supported/unsupported/contradicted); automatic exact-match checks that every amount, date, count, and account in the draft appears in the source data; compare prompt v1 vs v2; state small-sample caveat.
- Skip a fairness audit (no demographic attributes in the data) and say so in the README.

## README outline
Problem + live demo + GIF; architecture + lineage screenshot; data/license/synthetic caveat; one-command quickstart; design decisions and tradeoffs; results table; controls (data quality, audit log, human review, drift); LLM evaluation; WHERE THIS BREAKS (simulator labels, metrics will not transfer to a real bank, model may learn generator artifacts, SHAP reasons are not legal adverse-action codes, laptop-scale only, no fairness audit); next steps.

## Done means
- One command rebuilds the pipeline and CI tests pass.
- Live demo works.
- README has results table.
- Audit log works end to end.
- "Where this breaks" written.

## Working rules for this project
- Public or synthetic data only. No employer data, schemas, thresholds, code, architecture or internal numbers. Do not name any employer in the repo or public posts.
- Personal time and equipment. Check the employer's outside-work/IP policy before publishing.
- Never state numbers that were not measured.
- Be honest the data is synthetic. Public wording: "prototype on public synthetic data" and "personal project". Never "real-time" or "solved a real problem".
- No backdated commits, no inflated claims.
- Never put secrets in chat; never print `.env`; keep keys in `.env` and gitignored.
- Raw data is never committed.

## Resources
- Dataset: https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- Tools: dbt-core, dbt-expectations, DuckDB, MLflow, SHAP, Streamlit, Claude API.

## Learning gaps to cover (about 5 hours coaching)
AML basics, class imbalance, PR-AUC, SHAP.
