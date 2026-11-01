"""Show the top alerts on the VALIDATION days with their reason codes (SHAP values).

Run from the project root:  python scripts/explain_alerts.py
A reason = a feature that pushed this transaction's score up (toward laundering) or down.
Contributions are in log-odds units: positive pushes toward laundering, negative away from it.
These are model explanations, not legal reason codes.
"""
import numpy as np
import xgboost as xgb

from common import FEATURES, LABEL, load_frame

N_ALERTS = 5                                     # how many top alerts to print
N_REASONS = 3                                    # reasons shown per alert

df = load_frame()
valid = df[df["split"] == "validation"].reset_index(drop=True)   # reset_index: renumber rows 0, 1, 2 ...

model = xgb.XGBClassifier()
model.load_model("artifacts/xgb_v1.json")        # the model saved by train_model.py
scores = model.predict_proba(valid[FEATURES])[:, 1]

top = np.argsort(-scores)[:N_ALERTS]             # row positions of the highest scores

# TreeSHAP built into XGBoost: one contribution per feature per row, plus a final "bias" column
dmatrix = xgb.DMatrix(valid.loc[top, FEATURES], enable_categorical=True)
contrib = model.get_booster().predict(dmatrix, pred_contribs=True)

for rank, (pos, row_contrib) in enumerate(zip(top, contrib), start=1):
    row = valid.loc[pos]
    print(f"\n#{rank}  raw_row_id {int(row['raw_row_id'])}  score {scores[pos]:.3f}  "
          f"true label: {'LAUNDERING' if row[LABEL] == 1 else 'normal'}")
    feature_contrib = row_contrib[:-1]           # drop the last column (the bias / base value)
    strongest = np.argsort(-np.abs(feature_contrib))[:N_REASONS]   # biggest pushes, up or down
    for i in strongest:
        direction = "toward laundering" if feature_contrib[i] > 0 else "away from laundering"
        print(f"    {FEATURES[i]} = {row[FEATURES[i]]}   ->  {feature_contrib[i]:+.2f}  ({direction})")
