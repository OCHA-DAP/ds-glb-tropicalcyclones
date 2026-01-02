import os
from pathlib import Path

import pandas as pd
import pycountry

from src.datasources import gaul

DATA_DIR = Path(os.getenv("AA_DATA_DIR"))
CERF_RAW_PATH = (
    DATA_DIR
    / "public"
    / "raw"
    / "glb"
    / "cerf"
    / "AllocationsByYear_all_2024-02-27.xlsx"
)
CERF_PROC_DIR = DATA_DIR / "public" / "processed" / "glb" / "cerf"
CERF_ISO_PROC_PATH = (
    CERF_PROC_DIR / "AllocationsByYear_all_2024-02-27_with_iso.csv"
)


def load_raw_cerf():
    return pd.read_excel(CERF_RAW_PATH)


def match_cerf_to_iso_asap():
    adm0 = gaul.load_gaul()
    df = load_raw_cerf()

    def cerf_country_to_iso2(cerf_country_name):
        backups = {
            "Cape Verde": "CV",
            "Cote d'Ivoire": "CI",
            "Democratic Republic of the Congo": "CD",
            "occupied Palestinian territory": "PS",
            "Republic of Congo": "CG",
            "Swaziland": "SZ",
        }
        country = pycountry.countries.get(name=cerf_country_name)
        if country is None:
            country = pycountry.countries.get(official_name=cerf_country_name)
            if country is None:
                country = pycountry.countries.get(
                    common_name=cerf_country_name
                )
                if country is None:
                    return backups.get(cerf_country_name, None)
        return country.alpha_2

    df["iso2"] = df["Country"].apply(cerf_country_to_iso2)

    print("CERF countries without ISO2:")
    print(df[df["iso2"].isnull()]["Country"].unique())

    def iso2_to_asap0(iso2):
        backups = {"VC": 11, "PS": 75}
        dff = adm0[adm0["isocode"] == iso2]
        if dff.empty:
            return backups.get(iso2, None)
        else:
            return dff.iloc[0]["asap0_id"]

    df["asap0_id"] = df["iso2"].apply(iso2_to_asap0)

    print("CERF countries without asap0_id:")
    print(df[df["asap0_id"].isnull()].groupby("Country")["iso2"].first())

    df.to_csv(CERF_ISO_PROC_PATH, index=False)


def load_cerf_with_iso():
    return pd.read_csv(CERF_ISO_PROC_PATH, parse_dates=["Allocation date"])
