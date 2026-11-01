"""Link the laundering-pattern file to transaction rows.

Run from the project root:  python scripts/load_patterns.py
HI-Small_Patterns.txt lists every laundering attempt (370) with its pattern type (fan-out, cycle, ...) and its transactions.
Those transactions have the same columns as the main CSV, so we match them to bronze_transactions on every column.
Writes artifacts/laundering_patterns.csv (raw_row_id, attempt_id, pattern_type) and prints how well the match worked.
This only reads the data. It computes no model metric and does not touch the test results.
"""
import csv                                       # read comma-separated lines
from pathlib import Path

import duckdb
import pandas as pd

PATTERN_FILE = "data/raw/HI-Small_Patterns.txt"
COLS = ["timestamp", "from_bank", "from_account", "to_bank", "to_account", "amount_received",
        "receiving_currency", "amount_paid", "payment_currency", "payment_format", "is_laundering"]

# ---- 1. Parse the text file: "BEGIN ... ATTEMPT - TYPE: description" starts a block, "END ..." closes it ----
rows, attempt_id, pattern_type = [], 0, None
for line in Path(PATTERN_FILE).read_text().splitlines():
    if line.startswith("BEGIN LAUNDERING ATTEMPT"):
        attempt_id += 1                          # each BEGIN line is a new attempt
        pattern_type = line.split(" - ")[1].split(":")[0].strip()    # e.g. "FAN-OUT"
    elif line.startswith("END LAUNDERING ATTEMPT") or not line.strip():
        continue                                 # block end or blank line: nothing to keep
    else:
        fields = next(csv.reader([line]))        # split one line on commas
        rows.append([attempt_id, pattern_type, *fields])
pat = pd.DataFrame(rows, columns=["attempt_id", "pattern_type", *COLS])
print(f"pattern file: {attempt_id} attempts, {len(pat):,} transaction rows")

# ---- 2. Match to bronze on every column (bronze keeps the text exactly as in the CSV) ----
con = duckdb.connect("data/aml.duckdb", read_only=True)
con.register("pat", pat)                         # let SQL see the pandas table under the name "pat"
cond = " and ".join(f"b.{c} = p.{c}" for c in COLS)
matched = con.sql(f"""
    select b.raw_row_id, p.attempt_id, p.pattern_type
    from bronze_transactions b join pat p on {cond}
""").df()

# one transaction can match two identical pattern rows; keep one (the lowest attempt) per raw_row_id
matched = matched.sort_values(["raw_row_id", "attempt_id"]).drop_duplicates("raw_row_id")

total_laundering = con.sql("select count(*) from bronze_transactions where is_laundering = '1'").fetchone()[0]
print(f"transactions matched to a pattern: {len(matched):,}")
print(f"laundering transactions in the data: {total_laundering:,}")
print(f"laundering transactions WITHOUT a pattern: {total_laundering - len(matched):,}")
print("\nmatched transactions per pattern type:")
print(matched["pattern_type"].value_counts().to_string())

Path("artifacts").mkdir(exist_ok=True)
matched.to_csv("artifacts/laundering_patterns.csv", index=False)
print("\nsaved artifacts/laundering_patterns.csv")
