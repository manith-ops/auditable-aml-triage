"""Make a small CSV with deliberately broken rows, to show that the dbt tests catch bad data.

Run from the project root:  python scripts/make_bad_batch.py
Reads the first 10,000 real rows and writes data/bad_batch/HI-Small_Trans_bad.csv.
The real raw file is never changed.
"""
import csv                                   # stdlib: read and write CSV files
from pathlib import Path                     # stdlib: work with file paths

SOURCE = Path("data/raw/HI-Small_Trans.csv")             # the real file (read only)
TARGET = Path("data/bad_batch/HI-Small_Trans_bad.csv")   # the broken copy we create
N_ROWS = 10_000                                          # how many data rows to copy (underscores are just for readability)

# Column positions in the file (counting from 0). The two "Account" columns are 2 and 4.
COL_TIMESTAMP, COL_FROM_ACCOUNT, COL_AMOUNT_PAID, COL_LABEL = 0, 2, 7, 10

# row number (0 = first data row) -> (column to break, bad value, what it simulates)
FAULTS = {
    100: (COL_TIMESTAMP, "not-a-date", "unparseable timestamp"),
    200: (COL_AMOUNT_PAID, "abc", "non-numeric amount"),
    300: (COL_LABEL, "2", "label outside 0/1"),
    400: (COL_FROM_ACCOUNT, "", "missing sender account"),
}


def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)     # create data/bad_batch/ if missing
    with SOURCE.open(newline="") as src, TARGET.open("w", newline="") as out:
        reader = csv.reader(src)                         # yields each line as a list of text values
        writer = csv.writer(out)
        writer.writerow(next(reader))                    # copy the header line unchanged
        for i, row in enumerate(reader):                 # enumerate gives a counter i plus the row
            if i >= N_ROWS:
                break                                    # stop after N_ROWS data rows
            if i in FAULTS:
                col, bad_value, why = FAULTS[i]
                print(f"row {i}: {why}: {row[col]!r} -> {bad_value!r}")
                row[col] = bad_value                     # overwrite one value with the bad one
            writer.writerow(row)
    print(f"written: {TARGET}  ({N_ROWS} rows, {len(FAULTS)} broken)")


if __name__ == "__main__":
    main()
