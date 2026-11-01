"""Train an XGBoost model: fit on the train days, evaluate on the VALIDATION days, log the run to MLflow.

Run from the project root:  python scripts/train_model.py
The test days (Sep 9-18) are never loaded into a metric here; they are kept for one final evaluation.
Every run is recorded in MLflow (settings, metrics, model file, git commit). View them with:
    mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db
"""
import subprocess                                # run shell commands (here: ask git for the current commit)
from pathlib import Path

import mlflow                                    # experiment tracking
import numpy as np                               # fast number arrays
import xgboost as xgb                            # the gradient-boosted tree model
from sklearn.metrics import average_precision_score   # PR-AUC (area under the precision-recall curve)

from common import FEATURES, LABEL, load_frame   # shared feature list and loader (scripts/common.py)

MODEL_VERSION = "v1"                             # change this when the features or settings change
MODEL_PATH = Path("artifacts/xgb_v1.json")

PARAMS = {                                       # all training settings in one place, so they can be logged
    "n_estimators": 500,                         # at most 500 trees ...
    "early_stopping_rounds": 30,                 # ... but stop when validation PR-AUC has not improved for 30 trees
    "eval_metric": "aucpr",                      # the metric used to decide when to stop
    "learning_rate": 0.1,                        # how much each new tree is allowed to correct
    "max_depth": 6,                              # how deep each tree can grow
    "tree_method": "hist",                       # fast histogram-based training
    "enable_categorical": True,                  # allow the payment_format category column
    "n_jobs": -1,                                # use all CPU cores
    "random_state": 42,                          # fixed seed: same result every run
}


def git_info() -> tuple[str, bool]:
    """Return (short commit hash, whether there are uncommitted changes)."""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
    return commit, dirty


# ---- 1. Load: features + split + rule flag, one row per transaction ----
df = load_frame()

# ---- 2. Split by time (the split column was defined once, in dbt) ----
train = df[df["split"] == "train"]               # a boolean filter: keep only the rows where split == 'train'
valid = df[df["split"] == "validation"]
print(f"train rows {len(train):,} (laundering {int(train[LABEL].sum()):,})   "
      f"validation rows {len(valid):,} (laundering {int(valid[LABEL].sum()):,})")

# ---- 3. MLflow setup: a small database file inside the git-ignored artifacts/ folder ----
Path("artifacts").mkdir(exist_ok=True)
mlflow.set_tracking_uri("sqlite:///artifacts/mlflow.db")
mlflow.set_experiment("aml-triage")

with mlflow.start_run(run_name=f"xgb-{MODEL_VERSION}"):      # everything logged below belongs to this one run
    commit, dirty = git_info()
    mlflow.set_tags({
        "model_version": MODEL_VERSION,
        "git_commit": commit,
        "git_uncommitted_changes": str(dirty),   # True means the code differed from the commit
        "split": "train Sep 1-6 | validation Sep 7-8 | test Sep 9-18 (test not used here)",
    })

    # ---- 4. Train ----
    n_pos = int(train[LABEL].sum())
    n_neg = len(train) - n_pos
    spw = n_neg / n_pos                          # laundering is rare, so up-weight it by the rare-class ratio
    mlflow.log_params({**PARAMS, "scale_pos_weight": round(spw, 1), "n_features": len(FEATURES)})  # ** merges two dicts
    model = xgb.XGBClassifier(**PARAMS, scale_pos_weight=spw)   # ** unpacks the dict into keyword arguments
    model.fit(
        train[FEATURES], train[LABEL],           # X = inputs, y = answers
        eval_set=[(valid[FEATURES], valid[LABEL])],   # watched during training for early stopping
        verbose=50,                              # print progress every 50 trees
    )

    # ---- 5. Evaluate on VALIDATION ----
    scores = model.predict_proba(valid[FEATURES])[:, 1]   # one score per row: how likely laundering
    y = valid[LABEL].to_numpy()
    base_rate = y.mean()                         # share of laundering rows if you picked at random
    order = np.argsort(-scores)                  # row positions sorted from highest score to lowest

    def at_top(k: int) -> tuple[float, float]:
        """Alert budget = review the top k rows. Return (precision, recall) for that budget."""
        caught = y[order[:k]].sum()              # laundering rows among the k highest-scored
        return caught / k, caught / y.sum()

    metrics = {"base_rate": base_rate, "pr_auc": average_precision_score(y, scores)}
    for k in (1_000, 5_000, 10_000):
        p, r = at_top(k)
        metrics[f"precision_at_{k}"] = p
        metrics[f"recall_at_{k}"] = r

    # Same alert volume as the ACH rule, so the comparison is fair
    k_rule = int(valid["rule_ach"].sum())
    rule_hits = int(valid.loc[valid["rule_ach"], LABEL].sum())
    p, r = at_top(k_rule)
    metrics.update({
        "ach_rule_precision": rule_hits / k_rule, "ach_rule_recall": rule_hits / y.sum(),
        "model_precision_at_ach_volume": p, "model_recall_at_ach_volume": r,
    })

    mlflow.log_metrics({name: float(value) for name, value in metrics.items()})   # record every number in the run
    for name, value in metrics.items():
        print(f"{name:<32}{value:.4f}")

    # ---- 6. Save the model and attach the file to the run ----
    model.save_model(str(MODEL_PATH))
    mlflow.log_artifact(str(MODEL_PATH))
    print(f"\nsaved {MODEL_PATH}   (git commit {commit}, uncommitted changes: {dirty})")
