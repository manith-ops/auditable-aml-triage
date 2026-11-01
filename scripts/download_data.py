"""Download the IBM AMLworld HI-Small files from Kaggle into data/raw/.

Run from the project root:  python scripts/download_data.py
Needs KAGGLE_API_TOKEN in the .env file (never commit .env).
Dataset license: CDLA-Sharing 1.0. Do not commit or re-host the raw files.
"""
import zipfile                                   # stdlib: open .zip files
from pathlib import Path                         # stdlib: work with file paths safely

from dotenv import load_dotenv                   # python-dotenv: reads .env into environment variables

load_dotenv()                                    # must run BEFORE kaggle authenticates, so it can see KAGGLE_API_TOKEN

from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402  (imported after load_dotenv on purpose)

DATASET = "ealtman2019/ibm-transactions-for-anti-money-laundering-aml"  # Kaggle owner/dataset-name
FILES = [                                        # the HI-Small set: transactions, laundering patterns, accounts
    "HI-Small_Trans.csv",
    "HI-Small_Patterns.txt",
    "HI-Small_accounts.csv",
]
RAW_DIR = Path("data/raw")                       # git-ignored folder made in step 1


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)   # make sure the folder exists
    api = KaggleApi()
    api.authenticate()                           # logs in using the token from the environment

    for name in FILES:
        target = RAW_DIR / name
        if target.exists():                      # skip files we already have (safe to re-run)
            print(f"skip (already there): {name}")
            continue
        print(f"downloading: {name}")
        api.dataset_download_file(DATASET, name, path=str(RAW_DIR), quiet=False)
        zipped = RAW_DIR / f"{name}.zip"         # Kaggle may deliver each file zipped
        if zipped.exists():
            with zipfile.ZipFile(zipped) as z:
                z.extractall(RAW_DIR)            # unzip next to it
            zipped.unlink()                      # delete the .zip after extracting

    print("done. files in", RAW_DIR)


if __name__ == "__main__":                       # only run main() when executed directly, not when imported
    main()
