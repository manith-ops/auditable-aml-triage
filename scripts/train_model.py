"""Train the first XGBoost model: fit on the train days, evaluate on the VALIDATION days.

Run from the project root:  python scripts/train_model.py
The test days (Sep 9-18) are never loaded into a metric here; they are kept for one final evaluation.
"""
from pathlib import Path

import numpy as np                               # fast number arrays
import xgboost as xgb                            # the gradient-boosted tree model
from sklearn.metrics import average_precision_score   # PR-AUC (area under the precision-recall curve)

from common import FEATURES, LABEL, load_frame   # shared feature list and loader (scripts/common.py)

# ---- 1. Load: features + split + rule flag, one row per transaction ----
df = load_frame()

# ---- 2. Split by time (the split column was defined once, in dbt) ----
train = df[df["split"] == "train"]               # a boolean filter: keep only the rows where split == 'train'
valid = df[df["split"] == "validation"]
print(f"train rows {len(train):,} (laundering {int(train[LABEL].sum()):,})   "
      f"validation rows {len(valid):,} (laundering {int(valid[LABEL].sum()):,})")

# ---- 3. Train ----
n_pos = int(train[LABEL].sum())
n_neg = len(train) - n_pos
model = xgb.XGBClassifier(
    n_estimators=500,                            # at most 500 trees ...
    early_stopping_rounds=30,                    # ... but stop when validation PR-AUC has not improved for 30 trees
    eval_metric="aucpr",                         # the metric used to decide when to stop
    learning_rate=0.1,                           # how much each new tree is allowed to correct
    max_depth=6,                                 # how deep each tree can grow
    tree_method="hist",                          # fast histogram-based training
    enable_categorical=True,                     # allow the payment_format category column
    scale_pos_weight=n_neg / n_pos,              # laundering is rare, so each laundering row counts as much as the rare-class ratio
    n_jobs=-1,                                   # use all CPU cores
    random_state=42,                             # fixed seed: same result every run
)
model.fit(
    train[FEATURES], train[LABEL],               # X = inputs, y = answers
    eval_set=[(valid[FEATURES], valid[LABEL])],  # watched during training for early stopping
    verbose=50,                                  # print progress every 50 trees
)

# ---- 4. Evaluate on VALIDATION ----
scores = model.predict_proba(valid[FEATURES])[:, 1]      # one probability-like score per row: how likely laundering
y = valid[LABEL].to_numpy()
base_rate = y.mean()                             # share of laundering rows if you picked at random

order = np.argsort(-scores)                      # row positions sorted from highest score to lowest


def at_top(k: int) -> tuple[float, float]:
    """Alert budget = review the top k rows. Return (precision, recall) for that budget."""
    caught = y[order[:k]].sum()                  # laundering rows among the k highest-scored
    return caught / k, caught / y.sum()


print(f"\nbase rate (random): {base_rate:.5f}")
print(f"PR-AUC: {average_precision_score(y, scores):.4f}   (random would be about {base_rate:.4f})")
for k in (1_000, 5_000, 10_000):
    p, r = at_top(k)
    print(f"top {k:>6,} alerts: precision {p:.4f}  recall {r:.4f}")

# Same alert volume as the ACH rule, so the comparison is fair
k_rule = int(valid["rule_ach"].sum())
rule_hits = int(valid.loc[valid["rule_ach"], LABEL].sum())
p, r = at_top(k_rule)
print(f"\nACH rule flags {k_rule:,} rows: precision {rule_hits / k_rule:.4f}  recall {rule_hits / y.sum():.4f}")
print(f"model, same {k_rule:,} alerts:     precision {p:.4f}  recall {r:.4f}")

# ---- 5. Save the model (the folder is git-ignored) ----
Path("artifacts").mkdir(exist_ok=True)
model.save_model("artifacts/xgb_v1.json")
print("\nsaved artifacts/xgb_v1.json")
