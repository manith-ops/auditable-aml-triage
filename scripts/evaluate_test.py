"""Final evaluation of the frozen model v1, as set out in docs/evaluation_plan.md.

Run from the project root:
    python scripts/evaluate_test.py                      # scores the TEST days (Sep 9-18), once
    python scripts/evaluate_test.py --split validation   # dry run on validation days, to check the script itself
A second test run is refused unless you pass --rerun, so looking at the test days twice is a deliberate, visible choice.
Needs artifacts/xgb_v1.json (train_model.py) and artifacts/laundering_patterns.csv (load_patterns.py).
Writes artifacts/<split>_results.json and artifacts/<split>_error_analysis.csv, and logs a run to MLflow.
"""
import json
import subprocess
import sys
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score

from common import FEATURES, LABEL, load_frame

SPLIT = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else "test"
RERUN = "--rerun" in sys.argv
RESULTS_PATH = Path(f"artifacts/{SPLIT}_results.json")
FRACTIONS = (0.001, 0.005)                       # alert budgets: top 0.1% and top 0.5% of rows (fixed in the plan)
AMOUNT_RULE = 10_000                             # amount rule threshold (fixed in the plan)
N_BOOT, SEED = 2_000, 42                         # bootstrap repeats and fixed seed
N_ERRORS = 20                                    # worst false positives and worst misses to list

if SPLIT == "test" and RESULTS_PATH.exists() and not RERUN:
    sys.exit(f"{RESULTS_PATH} already exists: the test days were already scored. Use --rerun only if you must, and say so in the README.")

# ---- 1. Load the frame, keep one split, attach pattern types ----
df = load_frame()
part = df[df["split"] == SPLIT].reset_index(drop=True)
patterns = pd.read_csv("artifacts/laundering_patterns.csv")
part = part.merge(patterns[["raw_row_id", "pattern_type"]], on="raw_row_id", how="left")    # left merge keeps the row order
part["pattern_type"] = part["pattern_type"].fillna("")
part.loc[(part[LABEL] == 1) & (part["pattern_type"] == ""), "pattern_type"] = "NO PATTERN LISTED"

y = part[LABEL].to_numpy()
n = len(part)
print(f"split: {SPLIT}   rows: {n:,}   laundering: {int(y.sum()):,}   base rate: {y.mean():.5f}")

# ---- 2. Score with the frozen model ----
model = xgb.XGBClassifier()
model.load_model("artifacts/xgb_v1.json")
scores = model.predict_proba(part[FEATURES])[:, 1]
order = np.argsort(-scores, kind="stable")       # row positions, highest score first
score_rank = np.empty(n, dtype=int)
score_rank[order] = np.arange(1, n + 1)          # rank 1 = highest score

ach = part["rule_ach"].to_numpy(dtype=bool)
amount = (part["amount_paid"].to_numpy() > AMOUNT_RULE)
either = ach | amount


def mask_top(ranking: np.ndarray, k: int) -> np.ndarray:
    """Boolean mask that is True for the first k rows of a ranking."""
    m = np.zeros(n, dtype=bool)
    m[ranking[:k]] = True
    return m


def stats(mask: np.ndarray) -> dict:
    """Alerts = rows in the mask. Caught = laundering among them. FP per TP = non-laundering alerts per laundering alert."""
    alerts, caught = int(mask.sum()), int(y[mask].sum())
    return {"alerts": alerts, "caught": caught, "precision": caught / alerts, "recall": caught / y.sum(),
            "fp_per_tp": (alerts - caught) / caught if caught else None}


def recall_interval(mask: np.ndarray) -> tuple[float, float]:
    """95% bootstrap interval for recall. Only laundering rows matter for recall, so each gets a Poisson(1) weight
    (the usual way to resample rows), and recall = weighted caught / weighted total. The alert set is treated as fixed."""
    hit = mask[y == 1].astype(float)
    w = np.random.default_rng(SEED).poisson(1.0, size=(N_BOOT, len(hit)))
    r = (w * hit).sum(axis=1) / w.sum(axis=1)
    lo, hi = np.percentile(r, [2.5, 97.5])
    return float(lo), float(hi)


# Combined: rows flagged by either rule first (best model score first), then everything else by model score
combined_order = np.lexsort((-scores, ~either))

results = {"split": SPLIT, "rows": n, "laundering": int(y.sum()), "base_rate": float(y.mean()),
           "pr_auc": float(average_precision_score(y, scores))}
print(f"PR-AUC: {results['pr_auc']:.4f}   (random ranker ~ {results['base_rate']:.4f})")

# ---- 3. Table 1: fixed alert budgets (share of rows) ----
rows = []
for frac in FRACTIONS:
    k = int(np.ceil(frac * n))
    for name, ranking in (("model", order), ("combined", combined_order)):
        m = mask_top(ranking, k)
        s = stats(m)
        s.update({"budget": f"top {frac:.1%}", "method": name, "recall_ci": recall_interval(m)})
        rows.append(s)
budget_table = pd.DataFrame(rows)
results["budgets"] = rows
print("\n== Alert budgets (share of rows) ==")
print(budget_table[["budget", "method", "alerts", "caught", "precision", "recall", "recall_ci", "fp_per_tp"]].to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# ---- 4. Table 2: each rule at its own volume, against model and combined at the same volume ----
rows = []
for rule_name, rule_mask in (("ACH rule", ach), ("amount rule", amount), ("either rule", either)):
    k = int(rule_mask.sum())
    for name, m in ((rule_name, rule_mask), ("model, same volume", mask_top(order, k)), ("combined, same volume", mask_top(combined_order, k))):
        s = stats(m)
        s.update({"matched_to": rule_name, "method": name, "recall_ci": recall_interval(m)})
        rows.append(s)
volume_table = pd.DataFrame(rows)
results["rule_matched"] = rows
print("\n== Rules vs model at the same alert volume ==")
print(volume_table[["matched_to", "method", "alerts", "caught", "precision", "recall", "recall_ci", "fp_per_tp"]].to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# ---- 5. Recall by laundering pattern ----
masks = {"ACH rule": ach, "amount rule": amount}
for frac in FRACTIONS:
    masks[f"model top {frac:.1%}"] = mask_top(order, int(np.ceil(frac * n)))
masks["model @ACH volume"] = mask_top(order, int(ach.sum()))
rows = []
for pattern, grp in part[part[LABEL] == 1].groupby("pattern_type"):
    idx = grp.index.to_numpy()
    row = {"pattern": pattern, "laundering_rows": len(idx)}
    for name, m in masks.items():
        row[name] = float(m[idx].mean())         # share of this pattern's rows that the method alerts on
    rows.append(row)
pattern_table = pd.DataFrame(rows).sort_values("laundering_rows", ascending=False)
results["by_pattern"] = rows
print("\n== Recall by laundering pattern ==")
print(pattern_table.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

# ---- 6. Error analysis: worst false positives and worst misses, with SHAP reasons ----
fp_idx = np.where(y == 0)[0][np.argsort(-scores[y == 0], kind="stable")[:N_ERRORS]]      # highest-scored non-laundering rows
miss_idx = np.where(y == 1)[0][np.argsort(scores[y == 1], kind="stable")[:N_ERRORS]]     # lowest-scored laundering rows
pick = np.concatenate([fp_idx, miss_idx])
contrib = model.get_booster().predict(xgb.DMatrix(part.loc[pick, FEATURES], enable_categorical=True), pred_contribs=True)
reasons = []
for i in range(len(pick)):
    c = contrib[i, :-1]                          # drop the base-value column
    strongest = np.argsort(-np.abs(c))[:3]
    reasons.append(" | ".join(f"{FEATURES[j]}={part.loc[pick[i], FEATURES[j]]} ({c[j]:+.2f})" for j in strongest))
err = part.loc[pick, ["raw_row_id", "transaction_ts", "amount_paid", "payment_format", "rule_ach", "pattern_type"]].copy()
err.insert(0, "kind", ["false positive"] * len(fp_idx) + ["missed laundering"] * len(miss_idx))
err["score"] = scores[pick]
err["score_rank"] = score_rank[pick]
err["reasons"] = reasons
Path("artifacts").mkdir(exist_ok=True)
err.to_csv(f"artifacts/{SPLIT}_error_analysis.csv", index=False)
print(f"\nsaved artifacts/{SPLIT}_error_analysis.csv ({len(err)} rows: {N_ERRORS} worst false positives, {N_ERRORS} worst misses)")

# ---- 7. Save the numbers and log the run ----
RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
mlflow.set_tracking_uri("sqlite:///artifacts/mlflow.db")
mlflow.set_experiment("aml-triage")
with mlflow.start_run(run_name=f"eval-{SPLIT}-v1"):
    mlflow.set_tags({"model_version": "v1", "split": SPLIT, "git_commit": commit, "git_uncommitted_changes": str(dirty)})
    mlflow.log_metrics({"pr_auc": results["pr_auc"], "base_rate": results["base_rate"]})
    mlflow.log_artifact(str(RESULTS_PATH))
print(f"saved {RESULTS_PATH}   (git commit {commit}, uncommitted changes: {dirty})")
