import os
from pathlib import Path
from typing import List

import cdsapi

from src.datasources import codab

DATA_DIR = Path(os.environ["AA_DATA_DIR_NEW"])
ERA5_MOZ_RAW_DIR = DATA_DIR / "public" / "raw" / "moz" / "era5"
ERA5_MOZ_RAW_HOURLY_DIR = ERA5_MOZ_RAW_DIR / "hourly"


def download_era5_hourly(years: List[int], clobber: bool = False):
    adm2 = codab.load_moz_codab()
    bounds = adm2.total_bounds
    area = [bounds[3] + 1, bounds[0], bounds[1], bounds[2] + 1]
    client = cdsapi.Client()
    fileformat = "grib"
    for year in years:
        data_request = {
            "product_type": "ensemble_mean",
            "format": fileformat,
            "variable": "total_precipitation",
            "year": f"{year}",
            "month": [
                "01",
                "02",
                "03",
                "04",
                "05",
                "06",
                "07",
                "08",
                "09",
                "10",
                "11",
                "12",
            ],
            "day": [
                "01",
                "02",
                "03",
                "04",
                "05",
                "06",
                "07",
                "08",
                "09",
                "10",
                "11",
                "12",
                "13",
                "14",
                "15",
                "16",
                "17",
                "18",
                "19",
                "20",
                "21",
                "22",
                "23",
                "24",
                "25",
                "26",
                "27",
                "28",
                "29",
                "30",
                "31",
            ],
            "time": [
                "00:00",
                "03:00",
                "06:00",
                "09:00",
                "12:00",
                "15:00",
                "18:00",
                "21:00",
            ],
            "area": area,
        }
        filename = f"ecmwf-reanalysis-hourly-precipitation-{year}.{fileformat}"
        save_path = ERA5_MOZ_RAW_HOURLY_DIR / filename
        if clobber or not save_path.exists():
            client.retrieve(
                "reanalysis-era5-single-levels",
                data_request,
                save_path,
            )
        else:
            print(f"File {save_path} already exists.")
