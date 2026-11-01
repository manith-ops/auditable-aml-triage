"""Generate a tiny SYNTHETIC transactions file in the same format as the IBM HI-Small file.

Used by CI (GitHub Actions) so the pipeline can be tested without downloading the real dataset.
The values are random; nothing here comes from the IBM data.

Run from the project root:  python scripts/make_sample_data.py
Writes data/sample/sample_trans.csv
"""
import csv                                       # stdlib: write CSV files
import random                                    # stdlib: random numbers
from datetime import datetime, timedelta         # stdlib: dates and time steps
from pathlib import Path                         # stdlib: file paths

TARGET = Path("data/sample/sample_trans.csv")
N_ROWS = 2_000
SEED = 42                                        # fixed seed = same "random" file every run, so CI is repeatable

HEADER = [                                       # same header as the real file (two columns are both called "Account")
    "Timestamp", "From Bank", "Account", "To Bank", "Account",
    "Amount Received", "Receiving Currency", "Amount Paid", "Payment Currency",
    "Payment Format", "Is Laundering",
]
CURRENCIES = ["US Dollar", "Euro", "Yen", "Rupee"]
FORMATS = ["ACH", "Cheque", "Credit Card", "Cash", "Wire", "Bitcoin", "Reinvestment"]


def make_account(rng: random.Random) -> tuple[str, str]:
    """Return a fake (bank, account) pair, e.g. ('010', '8000AB12C')."""
    bank = f"{rng.randint(1, 20):03d}"                               # 3-digit bank code with leading zeros
    account = "8" + "".join(rng.choices("0123456789ABCDEF", k=8))    # 9-character account ID
    return bank, account


def main() -> None:
    rng = random.Random(SEED)                    # own random generator, seeded
    pool = [make_account(rng) for _ in range(200)]      # 200 accounts that appear again and again, so fan-in/fan-out have something to count
    start = datetime(2022, 9, 1, 0, 0)

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with TARGET.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for i in range(N_ROWS):
            sender, receiver = rng.sample(pool, 2)               # two different accounts
            amount = f"{rng.uniform(1, 5000):.2f}"               # amount with 2 decimals, as text
            currency = rng.choice(CURRENCIES)
            ts = start + timedelta(minutes=i)                    # one transaction per minute
            writer.writerow([
                ts.strftime("%Y/%m/%d %H:%M"),                   # same date format as the real file
                sender[0], sender[1], receiver[0], receiver[1],
                amount, currency, amount, currency,
                rng.choice(FORMATS),
                1 if rng.random() < 0.01 else 0,                 # about 1% labelled laundering
            ])
    print(f"written: {TARGET} ({N_ROWS} synthetic rows)")


if __name__ == "__main__":
    main()
