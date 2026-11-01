"""Build the alert list the analyst app shows: top-scored transactions with plain-language reasons.

Run from the project root:  python scripts/build_alerts.py
Reads the model saved by train_model.py and writes artifacts/alerts.csv (git-ignored).
By default it uses the VALIDATION days. The test days are only used in the final evaluation.
The app never shows the true label to the analyst; it is kept in the file for evaluation only.
"""
from pathlib import Path

import numpy as np
import pandas as pd                              # tables in Python; used here to build and save the result
import xgboost as xgb

from common import FEATURES, LABEL, load_frame

SPLIT = "validation"                             # which days to score
N_ALERTS = 1_000                                 # alert budget: how many alerts go to the analyst queue
N_REASONS = 3                                    # reasons shown per alert
MODEL_VERSION = "v1"

FEATURE_NAMES = {                                # plain-language names for the reasons
    "amount_paid": "Amount paid",
    "hour_of_day": "Hour of day",
    "payment_format": "Payment format",
    "sender_sent_before": "Sender's earlier transactions",
    "sender_sent_amount_before": "Sender's earlier total sent",
    "sender_fan_out_before": "Different accounts the sender paid before",
    "receiver_received_before": "Receiver's earlier transactions",
    "receiver_received_amount_before": "Receiver's earlier total received",
    "receiver_fan_in_before": "Different accounts that paid the receiver before",
}


def describe(feature: str, value) -> str:
    """Format a feature value for people: money with commas, counts as whole numbers."""
    if feature == "payment_format":
        return str(value)
    if feature == "hour_of_day":
        return f"{int(value):02d}:00"
    if "amount" in feature:
        return f"{value:,.2f}"
    return f"{int(value):,}"


df = load_frame()
part = df[df["split"] == SPLIT].reset_index(drop=True)

model = xgb.XGBClassifier()
model.load_model("artifacts/xgb_v1.json")
part["score"] = model.predict_proba(part[FEATURES])[:, 1]       # risk score between 0 and 1

top = part.sort_values("score", ascending=False).head(N_ALERTS).reset_index(drop=True)   # the alert queue, best first
top.insert(0, "alert_id", range(1, len(top) + 1))               # rank 1 = highest risk

# Reasons: TreeSHAP contributions for the alert rows only
contrib = model.get_booster().predict(xgb.DMatrix(top[FEATURES], enable_categorical=True), pred_contribs=True)
reasons = []
for i in range(len(top)):
    c = contrib[i, :-1]                          # drop the last column (the base value)
    strongest = np.argsort(-np.abs(c))[:N_REASONS]
    parts = []
    for j in strongest:
        arrow = "raises risk" if c[j] > 0 else "lowers risk"
        parts.append(f"{FEATURE_NAMES[FEATURES[j]]}: {describe(FEATURES[j], top.loc[i, FEATURES[j]])} ({arrow}, {c[j]:+.2f})")
    reasons.append(" | ".join(parts))
top["reasons"] = reasons
top["model_version"] = MODEL_VERSION

cols = ["alert_id", "raw_row_id", "transaction_ts", "from_account_key", "to_account_key",
        "amount_paid", "payment_format", "rules_fired" if "rules_fired" in top else "rule_ach",
        "score", "reasons", "model_version", LABEL]
Path("artifacts").mkdir(exist_ok=True)
top[cols].to_csv("artifacts/alerts.csv", index=False)

# A small public-demo sample: the top 200 alerts, WITHOUT the true label.
# It contains rows derived from the IBM AMLworld data, so it ships with demo/DATA_NOTICE.md (CDLA-Sharing 1.0).
Path("demo").mkdir(exist_ok=True)
top.head(200)[[c for c in cols if c != LABEL]].to_csv("demo/alerts_demo.csv", index=False)
print("saved demo/alerts_demo.csv: top 200 alerts, no labels")
print(f"saved artifacts/alerts.csv: {len(top)} alerts from the {SPLIT} days")
print(f"laundering among them (evaluation only): {int(top[LABEL].sum())}")
print("\nfirst alert:")
print(top.loc[0, ["alert_id", "from_account_key", "to_account_key", "amount_paid", "score", "reasons"]].to_string())
