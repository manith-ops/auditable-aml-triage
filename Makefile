# One-command rebuild. Run from the project root with the virtual environment active:   make all
# Needs the raw data in data/raw (python scripts/download_data.py). Each target below can also be run alone.
# The final test-set evaluation is NOT part of "all": it is scored once on purpose (see docs/evaluation_plan.md).

.PHONY: all pipeline patterns train alerts drift evaluate ci

all: pipeline patterns train alerts     # rebuild everything from the raw data to the analyst queue

pipeline:                               # bronze -> silver -> gold, then all 26 data tests and reconciliations
	cd dbt && dbt build

patterns:                               # link the laundering-pattern file to transaction rows
	python scripts/load_patterns.py

train:                                  # fit the model on the train days, evaluate on validation, log to MLflow
	python scripts/train_model.py

alerts:                                 # build the ranked alert queue and the 200-alert demo sample
	python scripts/build_alerts.py

drift:                                  # PSI drift tables
	python scripts/drift_psi.py

evaluate:                               # the one-time test-set evaluation; refuses a second run unless --rerun is added by hand
	python scripts/evaluate_test.py

ci:                                     # what GitHub Actions runs: synthetic sample data, dbt build on the ci target
	python scripts/make_sample_data.py
	cd dbt && dbt build --target ci --vars '{raw_trans_path: ../data/sample/sample_trans.csv}'
