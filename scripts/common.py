"""Shared code for the modelling scripts: the feature list and the data loader."""
import duckdb

FEATURES = [                                     # the model inputs; the label is_laundering is NOT one of them
    "amount_paid", "hour_of_day", "payment_format",
    "sender_sent_before", "sender_sent_amount_before", "sender_fan_out_before",
    "receiver_received_before", "receiver_received_amount_before", "receiver_fan_in_before",
]
LABEL = "is_laundering"


def load_frame():
    """Return a pandas DataFrame: one row per transaction, with features, split and the ACH rule flag."""
    con = duckdb.connect("data/aml.duckdb", read_only=True)      # read only: scripts never change the data
    df = con.sql("""
        select f.*, g.split, g.rule_ach                -- features plus the split and the ACH rule flag
        from gold_transaction_features f
        join gold_transaction_flags g using (raw_row_id)
        order by f.raw_row_id                          -- fixed row order, so every run sees the data identically
    """).df()                                    # .df() = turn the SQL result into a pandas DataFrame
    df["payment_format"] = df["payment_format"].astype("category")   # a category column, not a number
    for col in FEATURES:
        if col != "payment_format":
            df[col] = df[col].astype(float)      # decimals -> plain floats for the model
    return df
