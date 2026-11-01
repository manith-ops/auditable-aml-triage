"""Analyst alert queue (prototype on public synthetic data).

Run from the project root:  streamlit run app/streamlit_app.py
Shows the ranked alerts with reasons. The analyst decides; every decision goes to the append-only audit log.
Nothing is ever filed automatically, and the true label is never shown.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))   # so "import audit" finds app/audit.py
import audit

ALERTS_FILE = "artifacts/alerts.csv"
LABELS = {"escalate": "Escalate to case", "dismiss": "Dismiss (false positive)", "more_info": "Request more information"}

st.set_page_config(page_title="AML alert queue", layout="wide")
st.title("AML alert queue")
st.caption("Prototype on public synthetic data. Personal project. Scores are model output; the analyst decides.")


@st.cache_data                                   # read the file once, not on every click
def load_alerts() -> pd.DataFrame:
    return pd.read_csv(ALERTS_FILE)


if not Path(ALERTS_FILE).exists():
    st.error(f"{ALERTS_FILE} not found. Run: python scripts/build_alerts.py")
    st.stop()

alerts = load_alerts()
log = audit.read_all()
latest = {}                                      # alert_id -> its most recent decision
for row in reversed(log):                        # oldest first, so later rows overwrite earlier ones
    latest[row["alert_id"]] = row["decision"]
alerts["status"] = alerts["alert_id"].map(lambda a: LABELS[latest[a]] if a in latest else "Open")

with st.sidebar:
    analyst = st.text_input("Analyst name (required to record a decision)")
    st.metric("Alerts in queue", len(alerts))
    st.metric("Reviewed", len(latest))
    show = st.radio("Show", ["All", "Open only"])

view = alerts if show == "All" else alerts[alerts["status"] == "Open"]
tab_queue, tab_log = st.tabs(["Queue", "Audit log"])

with tab_queue:
    st.dataframe(
        view[["alert_id", "transaction_ts", "from_account_key", "to_account_key",
              "amount_paid", "payment_format", "score", "status"]],
        hide_index=True,
    )
    if view.empty:
        st.success("No open alerts.")
        st.stop()

    chosen = st.selectbox("Open an alert", view["alert_id"], format_func=lambda a: f"Alert {a}")
    a = alerts[alerts["alert_id"] == chosen].iloc[0]

    st.subheader(f"Alert {int(a['alert_id'])}  |  risk score {a['score']:.3f}")
    left, right = st.columns(2)
    left.write(f"**From:** {a['from_account_key']}")
    left.write(f"**To:** {a['to_account_key']}")
    left.write(f"**Amount:** {a['amount_paid']:,.2f}   **Payment format:** {a['payment_format']}")
    left.write(f"**Time:** {a['transaction_ts']}")
    right.write("**Why it was flagged (model reasons):**")
    for reason in a["reasons"].split(" | "):
        right.write(f"- {reason}")
    right.caption("Model explanations, not legal reason codes. The model ranks risk; it does not decide.")

    decision = st.radio("Your decision", list(LABELS), format_func=LABELS.get, horizontal=True)
    note = st.text_area("Note (optional)")
    if st.button("Record decision"):
        try:
            audit.record(analyst, a["alert_id"], a["raw_row_id"], decision, note, a["score"], a["model_version"])
            st.success("Recorded in the audit log.")
            st.rerun()                           # redraw the page so the status updates
        except ValueError as e:
            st.warning(str(e))

with tab_log:
    st.caption("Append-only: rows cannot be edited or deleted.")
    st.dataframe(pd.DataFrame(log), hide_index=True)
