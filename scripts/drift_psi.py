"""Drift monitoring with PSI (Population Stability Index): has the data changed compared with a reference window?

Run from the project root:  python scripts/drift_psi.py
PSI = sum over buckets of (share_now - share_ref) * ln(share_now / share_ref).  Rule of thumb: <0.10 stable, 0.10-0.25 moderate, >0.25 large.
An empty bucket is floored at a tiny share, so a category that vanishes (or appears) gives a very large PSI.
No laundering label is used: monitoring must work without labels.

Table A: every day after training vs the TRAINING days. Days with fewer than MIN_ROWS rows are skipped (PSI on a few hundred rows is noise).
Table B: a clean demo. Reference = Sep 5, window = Sep 6 (two similar training days), then two SIMULATED shifts of Sep 6:
         amounts x3, and 20% of rows relabelled as ACH. It shows PSI separating a calm baseline from a real change.
Writes artifacts/drift_psi_a.csv and artifacts/drift_psi_b.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from common import FEATURES, load_frame

EPS = 1e-6                                       # floor for an empty bucket, stops ln(0)
SEED = 42
MIN_ROWS = 10_000                                # smaller windows are skipped

df = load_frame()
df["day"] = pd.to_datetime(df["transaction_ts"]).dt.strftime("%m-%d")

model = xgb.XGBClassifier()
model.load_model("artifacts/xgb_v1.json")
df["model_score"] = model.predict_proba(df[FEATURES])[:, 1]
MONITORED = FEATURES + ["model_score"]


def make_reference(ref: pd.DataFrame) -> dict:
    """Buckets and bucket shares come from the reference only: deciles for numbers, the categories for payment_format."""
    out = {}
    for f in MONITORED:
        if f == "payment_format":
            bins = [str(c) for c in ref[f].cat.categories]
        else:
            edges = np.unique(np.quantile(ref[f].to_numpy(float), np.linspace(0, 1, 11)))   # up to 10 equal-sized buckets
            bins = edges[1:-1]                   # inner edges; values below/above fall in the first/last bucket
        out[f] = (bins, shares(ref[f], f, bins))
    return out


def shares(series: pd.Series, f: str, bins) -> np.ndarray:
    """Share of rows in each bucket."""
    if f == "payment_format":
        counts = series.astype(str).value_counts().reindex(bins, fill_value=0).to_numpy()
    else:
        counts = np.bincount(np.searchsorted(bins, series.to_numpy(float), side="right"), minlength=len(bins) + 1)
    return counts / counts.sum()


def psi_row(window: pd.DataFrame, reference: dict) -> dict:
    row = {}
    for f in MONITORED:
        bins, ref_share = reference[f]
        a = np.clip(shares(window[f], f, bins), EPS, None)
        e = np.clip(ref_share, EPS, None)
        row[f] = float(np.sum((a - e) * np.log(a / e)))
    return row


def show(table: pd.DataFrame) -> None:
    short = {f: f.replace("sender_", "s_").replace("receiver_", "r_") for f in MONITORED}
    print(table.rename(columns=short).map(lambda v: "n/a" if pd.isna(v) else f"{v:.3f}{'**' if v >= 0.25 else '*' if v >= 0.10 else ''}").to_string())


# ---- Table A: later days vs the training days ----
ref_a = make_reference(df[df["split"] == "train"])
rows = {}
for day, g in df[df["split"] != "train"].groupby("day"):
    rows[f"{day} ({len(g):,} rows)"] = psi_row(g, ref_a) if len(g) >= MIN_ROWS else {f: np.nan for f in MONITORED}
table_a = pd.DataFrame(rows).T
print(f"TABLE A: days after training vs the {int((df['split'] == 'train').sum()):,} training rows.   * moderate (>=0.10)   ** large (>=0.25)\n")
show(table_a)

# ---- Table B: calm baseline and simulated shifts ----
ref_b = make_reference(df[df["day"] == "09-05"])
base = df[df["day"] == "09-06"].copy()
rows = {"09-06 (no shift)": psi_row(base, ref_b)}

amt = base.copy()
amt["amount_paid"] = amt["amount_paid"] * 3                      # shift 1: every amount triples
amt["model_score"] = model.predict_proba(amt[FEATURES])[:, 1]    # re-score so the score drift shows too
rows["SIM amounts x3"] = psi_row(amt, ref_b)

fmt = base.copy()
flip = np.random.default_rng(SEED).random(len(fmt)) < 0.20      # shift 2: 20% of rows become ACH
fmt["payment_format"] = fmt["payment_format"].astype(str)
fmt.loc[flip, "payment_format"] = "ACH"
fmt["payment_format"] = pd.Categorical(fmt["payment_format"], categories=base["payment_format"].cat.categories)
fmt["model_score"] = model.predict_proba(fmt[FEATURES])[:, 1]
rows["SIM 20% -> ACH"] = psi_row(fmt, ref_b)

table_b = pd.DataFrame(rows).T
print("\nTABLE B: reference Sep 5 (training) vs Sep 6, then simulated shifts of Sep 6\n")
show(table_b)

Path("artifacts").mkdir(exist_ok=True)
table_a.to_csv("artifacts/drift_psi_a.csv")
table_b.to_csv("artifacts/drift_psi_b.csv")
