import os
import re
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import pycountry
import requests

DATA_DIR = Path(os.getenv("AA_DATA_DIR_NEW"))
DOWNLOAD_URL = "https://humanitarianaction.info/download/6344/download"
HUMINFO_RAW_DIR = DATA_DIR / "public" / "raw" / "glb" / "humanitarianinfo"
HUMINFO_PROC_DIR = (
    DATA_DIR / "public" / "processed" / "glb" / "humanitarianinfo"
)
HRP_2024_ISO2S = [
    "AF",
    "BF",
    "CM",
    "CF",
    "TD",
    "CO",
    "CD",
    "SV",
    "ET",
    "GT",
    "HT",
    "HN",
    "ML",
    "MZ",
    "MM",
    "NE",
    "NG",
    "PS",
    "SO",
    "SS",
    "SD",
    "SY",
    "UA",
    "VE",
    "YE",
]


def download_operations_list():
    """Download the latest operations list from HumanitarianAction."""
    if not HUMINFO_RAW_DIR.exists():
        HUMINFO_RAW_DIR.mkdir(parents=True, exist_ok=True)
    response = requests.get(DOWNLOAD_URL)
    content_disposition = response.headers["Content-Disposition"]
    filename = re.findall("filename=(.+)", content_disposition)[0]
    filename = unquote(filename).strip('"')  # Decode URL-encoded string
    with open(HUMINFO_RAW_DIR / filename, "wb") as f:
        f.write(response.content)


def process_operations_list():
    """Process operations lists from HumanitarianAction."""
    if not HUMINFO_PROC_DIR.exists():
        HUMINFO_PROC_DIR.mkdir(parents=True, exist_ok=True)

    fallbacks = {
        "Occupied Palestinian Territory": "PS",
        "Venezuela": "VE",
        "Democratic Republic of the Congo": "CD",
    }

    def get_iso2(country_name):
        try:
            return pycountry.countries.get(name=country_name).alpha_2
        except AttributeError:
            return fallbacks.get(country_name, "Unknown")

    for filename in HUMINFO_RAW_DIR.glob("*.xlsx"):
        metadata = pd.read_excel(
            HUMINFO_RAW_DIR / filename,
            sheet_name="Meta data",
            engine="openpyxl",
        )
        pub_date = metadata.iloc[4, 1]
        pub_date = pd.to_datetime(pub_date)
        data = pd.read_excel(
            HUMINFO_RAW_DIR / filename,
            sheet_name="Export data",
            header=2,
            engine="openpyxl",
        )
        data["ISO2"] = data["Plans"].apply(get_iso2)
        save_name = f"operations_list_{pub_date:%Y-%m-%d}.csv"
        data.to_csv(HUMINFO_PROC_DIR / save_name, index=False)


def load_operations_list(pub_date: str = None):
    """Load processed operations list from HumanitarianAction.
    Args:
        pub_date (str, optional): Publication date of the operations list.
            If None, the latest operations list is loaded. Defaults to None.
    """
    filenames = [f.name for f in HUMINFO_PROC_DIR.glob("*.csv")]
    if pub_date is None:
        return pd.read_csv(HUMINFO_PROC_DIR / filenames[-1])
    else:
        load_path = HUMINFO_PROC_DIR / f"operations_list_{pub_date}.csv"
        return pd.read_csv(load_path)
