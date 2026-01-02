import os
import re
from pathlib import Path

import pandas as pd
import pycountry

from src.datasources import gaul, ibtracs

DATA_DIR = Path(os.getenv("AA_DATA_DIR_NEW"))
EMDAT_RAW_DIR = DATA_DIR / "private" / "raw" / "glb" / "emdat"
EMDAT_PROC_DIR = DATA_DIR / "private" / "processed" / "glb" / "emdat"


def load_raw_emdat():
    filename = "emdat-tropicalcyclone-2000-2022.xlsx"
    return pd.read_excel(EMDAT_RAW_DIR / filename)


def join_emdat_to_ibtracs():
    adm0 = gaul.load_gaul()
    df = load_raw_emdat()

    def iso3_to_iso2(iso3):
        backup = {"SPI": "ES"}
        try:
            return pycountry.countries.get(alpha_3=iso3).alpha_2
        except AttributeError:
            return backup.get(iso3)

    df["isocode"] = df["ISO"].apply(iso3_to_iso2)
    df["Event Name"] = df["Event Name"].fillna("")
    df = df.merge(adm0[["asap0_id", "isocode"]], on="isocode")
    df = df.rename(columns={"isocode": "iso2", "ISO": "iso3"})

    tracks = ibtracs.load_ibtracs_with_wind("wmo")
    cyclones = tracks.groupby("sid")[["time", "name"]].first()
    cyclones["year"] = cyclones["time"].dt.year
    cyclones["month"] = cyclones["time"].dt.month
    cyclones = cyclones.drop(columns="time").reset_index()
    cyclones = cyclones[cyclones["year"] >= 1999]

    thresholds = ibtracs.load_thresholds("wmo", 0)
    thresholds = thresholds.merge(adm0[["asap0_id", "isocode"]], on="asap0_id")
    lenient_thresholds = thresholds[
        (thresholds["d_thresh"] == thresholds["d_thresh"].max())
        & (thresholds["s_thresh"] == thresholds["s_thresh"].min())
    ]

    typo_names = {
        "Galifo": "Gafilo",
        "Indhala": "Indlala",
        "Feleng": "Felleng",
        "Reshmi": "Rashmi",
        "Chata": "Chataan",
        "Chanom": "Chanhom",
        "Tinh": "Sontinh",
        "ChanHome": "Chanhom",
        "Mangkut": "Mangkhut",
        "Shaheen": "Shaheengu",
        "Maisak": "Maysak",
        "Kai": "Kaitak",
        "Ciramon": "Cimaron",
        "Hygos": "Higos",
        "Beatrix": "Beatriz",
        "Ulla": "Ula",
        "Gamde": "Gamede",
        "ExDineo": "Dineo",
        "Orphelia": "Ophelia",
    }

    # these tracks are NOT on IBTrACS, despite being tracked by PAGASA
    known_not_recognized = [
        ("Ineng", 2003, 126),
        ("Winnie", 2004, 126),
    ]

    phl_rename = {
        ("Biring", 2000): "Longwang",
        ("Kabayan", 2003): "Etau",
        ("Henry", 2006): "Prapiroon",
        ("Chedeng and Dodong", 2007): "Pabuk and Wutip",
        ("Goring", 2007): "Wipha",
        ("Tropical depression Maring", 2009): "Mujigae",
        ("Tropical Depression Nando", 2009): "Koppu",
        ("Typhoon Karen", 2012): "Sanba",
        ("Tropcal storm Auring", 2013): "Sonamu",
        ("Agaton (01W)", 2018): "Bolaven",
    }

    specific_sid = {
        ("Auring", 2001, 126): "2001047N09134",
        ('Tropical depression "Urduja"', 2009, 126): "2009324N06129",
        ("Tropical depression 02W (Crising)", 2017, 126): "2017104N11130",
        ("Tropical depression 'Usman'", 2018, 126): "2018358N07140",
        ("Tropical depression 'Amang' (01W)", 2019, 126): "2019004N03175",
        ("Tropical depression 'Ofel'", 2020, 126): "2020288N13124",
        ("03B", 2000, 101): "2000331N09092",
        ("01A", 2001, 101): "2001141N14068",
        ("Tropical depression 'Vicky' (Krovanh)", 2020, 134): "2020353N06129",
        ("Tropical depression 'Twe'", 2021, 134): "2021296N06127",
        ("04B", 2000, 140): "2000358N08086",
        ('Cyclone "Tomas"', 2010, 116): "2010069S12188",
        ("Waka", 2001, 31): "2001363S10185",
        ("Catarina", 2004, 191): "2004086S29318",
        ("Cyclone 'Yemyin'", 2007, 199): "2007172N15088",
        ("Cyclone 3A", 2013, 156): "2013310N06066",
    }

    # for impact events intended to cover two cyclones,
    # break the tie based on which one seemed more extreme,
    # and assign all the damage to that one

    # this can be done manually since there's only a few
    tiebreakers = {
        # George 2007 was Cat 5, Jacob was Cat 3
        ("George and Jacob", 2007, 208): "2007058S12135",
        # near Madagascar, Eline was Cat 1, Gloria was just TS
        ("Eline, Gloria", 2000, 51): "2000032S11116",
        # Eric was TS, Fanele was Cat 4
        ("Cyclones Eric and Fanele", 2009, 51): "2009017S20043",
        # Nesat was Cat 2, Haitang was TS
        ("Typhoon Nesat & Haitang", 2017, 126): "2017206N13129",
        ("Typhoon Nesat & Haitang", 2017, 137): "2017206N13129",
        ("Typhoon Nesat & Haitang", 2017, 62): "2017206N13129",
        # close call (both Cat 1),
        # but Utor seems to have had more impact in China
        ("Durian and Utor", 2001, 62): "2001181N08141",
    }

    def generate_regex_pattern(words_string: str):
        words_string = words_string.replace("'", " ").replace("/", " ")
        words = [
            re.escape(re.sub(r"[^a-zA-Z\s]", "", word))
            for word in words_string.split()
        ]
        words = [typo_names.get(word, word) for word in words if word != ""]
        pattern = r"\b(" + "|".join(words) + r")\b"
        return pattern

    def match_any_word_in_column(word, pattern):
        word = word.replace("-", "")
        if re.search(pattern, word, re.IGNORECASE):
            return True
        else:
            return False

    def emdat_row_to_sid(row, cyclones_df, thresholds_df):
        verbose = False
        emdat_name = row["Event Name"]
        emdat_year = row["Start Year"]
        emdat_asap0 = row["asap0_id"]
        id_string = f"{emdat_name}, {emdat_year}, {emdat_asap0}"
        if emdat_name == "":
            return ""
        if (emdat_name, emdat_year, emdat_asap0) in specific_sid:
            if verbose:
                print(f"found specific sid for {id_string}")
            return specific_sid.get((emdat_name, emdat_year, emdat_asap0))

        # rename specific cyclones in PHL since they use different names
        if emdat_asap0 == 126:
            emdat_name = phl_rename.get((emdat_name, emdat_year), emdat_name)

        pattern = generate_regex_pattern(emdat_name)
        dff = cyclones_df[
            cyclones_df["name"].apply(
                match_any_word_in_column, args=(pattern,)
            )
        ]
        if dff.empty:
            if emdat_year > 2021:
                if verbose:
                    print(f"no matching name, but year is {emdat_year}")
                return ""
            if (emdat_name, emdat_year, emdat_asap0) in known_not_recognized:
                if verbose:
                    print(
                        f"not recognized by IBTrACS, ignoring for {id_string}"
                    )
                return ""
            raise Exception(f"{pattern} not found for {id_string}")
        if verbose:
            print(f"{len(dff)} found matching name")
        dff = dff[dff["year"].isin([emdat_year, emdat_year - 1])]
        if dff.empty:
            if emdat_year > 2021:
                if verbose:
                    print(
                        f"no matching name in year, but year is {emdat_year}"
                    )
                return ""
            raise Exception(
                f"{pattern} in {emdat_year} not found for {id_string}"
            )
        if verbose:
            print(f"{len(dff)} found matching year")
        triggered_sids = thresholds_df[
            thresholds_df["asap0_id"] == emdat_asap0
        ]["sid"]
        dff_t = dff[dff["sid"].isin(triggered_sids)]
        if dff_t.empty:
            if emdat_year > 2021:
                if verbose:
                    print(f"no matching sid, but year is {emdat_year}")
                return ""
            if len(dff) == 1:
                dff_t = dff
                if verbose:
                    print(
                        "sid not triggered, "
                        "setting to match based on name and year"
                    )
            else:
                if verbose:
                    print("multiple sids match, taking one with matching year")
                dff_t = dff[dff["year"] == emdat_year]
                if len(dff_t) > 1:
                    print(dff)
                    raise Exception(
                        f"cannot decide which storm for {id_string}"
                    )
        if verbose:
            print(f"{len(dff_t)} found matching asap0 threshold")
        if len(dff_t) > 1:
            if (emdat_name, emdat_year, emdat_asap0) in tiebreakers:
                if verbose:
                    print(f"found tiebreaker for {id_string}")
                return tiebreakers.get((emdat_name, emdat_year, emdat_asap0))
            print(dff_t)
            raise Exception(f"multiple sids for {id_string}")
        return dff_t.iloc[0]["sid"]

    df["sid"] = df.apply(
        emdat_row_to_sid, args=(cyclones, lenient_thresholds), axis=1
    )

    filename = "emdat-tropicalcyclone-2000-2022-processed-sids.csv"

    df.to_csv(EMDAT_PROC_DIR / filename, index=False)


def load_emdat_with_sids():
    filename = "emdat-tropicalcyclone-2000-2022-processed-sids.csv"
    return pd.read_csv(EMDAT_PROC_DIR / filename)
