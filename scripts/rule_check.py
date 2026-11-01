"""Measure candidate AML rule flags on the TRAINING days only (before 2022-09-07).

Run from the project root:  python scripts/rule_check.py
For each rule it prints: how many rows it flags, how many of those are laundering,
precision (how many flagged rows are truly laundering) and recall (how many of all
laundering rows the rule catches). The validation and test days are never touched.
"""
import duckdb                                    # the database library; also runs SQL from Python

TRAIN_END = "2022-09-07"                         # training = everything BEFORE this timestamp

# Each rule is a name plus a SQL condition (true = the row is flagged).
RULES = {
    "payment_format = ACH": "payment_format = 'ACH'",
    "cross_currency":       "is_cross_currency",
    "self_transfer":        "is_self_transfer",
    "amount_paid > 10000":  "amount_paid > 10000",
}

con = duckdb.connect("data/aml.duckdb", read_only=True)   # read only: this script never changes the data

total_laundering = con.sql(
    f"select sum(is_laundering) from silver_transactions where transaction_ts < '{TRAIN_END}'"
).fetchone()[0]                                  # fetchone() returns one result row; [0] picks its first value
total_rows = con.sql(
    f"select count(*) from silver_transactions where transaction_ts < '{TRAIN_END}'"
).fetchone()[0]
print(f"training rows: {total_rows:,}   laundering rows: {total_laundering:,}\n")
print(f"{'rule':<24}{'flagged':>10}{'caught':>8}{'precision':>11}{'recall':>9}")

for name, condition in RULES.items():            # loop over the rules one by one
    flagged, caught = con.sql(f"""
        select
            count(*) filter (where {condition})                          as flagged,   -- rows the rule flags
            count(*) filter (where {condition} and is_laundering = 1)    as caught     -- flagged AND truly laundering
        from silver_transactions
        where transaction_ts < '{TRAIN_END}'
    """).fetchone()
    precision = caught / flagged if flagged else 0           # of the flagged rows, how many are real
    recall = caught / total_laundering                       # of all laundering rows, how many we catch
    print(f"{name:<24}{flagged:>10,}{caught:>8,}{precision:>11.4f}{recall:>9.4f}")
