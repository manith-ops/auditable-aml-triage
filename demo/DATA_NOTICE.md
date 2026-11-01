# Data notice for `alerts_demo.csv`

`alerts_demo.csv` is derived from the **IBM AMLworld synthetic transactions** dataset
(Kaggle: `ealtman2019/ibm-transactions-for-anti-money-laundering-aml`, HI-Small set).
It is synthetic data. It does not describe real people, accounts or transactions.

- **License:** Community Data License Agreement - Sharing, Version 1.0 (CDLA-Sharing-1.0): https://cdla.dev/sharing-1-0/
  This file is published under the same license.
- **Source credit:** the dataset and its creators (see the Kaggle page above).
- **Changes made:** the file contains only the 200 highest-scored transactions from the validation days, with model scores
  and model-generated reasons added. The true laundering label is removed.
- **Not included:** the rest of the dataset. It must be downloaded from Kaggle (see `scripts/download_data.py`).
