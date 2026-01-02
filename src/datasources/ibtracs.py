import os
import urllib
from pathlib import Path
from typing import Literal

import geopandas as gpd
import pandas as pd
import xarray as xr
from shapely import Point
from tqdm import tqdm

from src.datasources import gaul

DATA_DIR = Path(os.getenv("AA_DATA_DIR_NEW"))
IBTRACS_RAW_DIR = DATA_DIR / "public" / "raw" / "glb" / "ibtracs"
IBTRACS_PROC_DIR = DATA_DIR / "public" / "processed" / "glb" / "ibtracs"
MOZ_IBTRACS_PROC_DIR = DATA_DIR / "public" / "processed" / "moz" / "ibtracs"


def download_ibtracs(dataset: Literal["ALL", "last3years"] = "ALL"):
    """Download IBTrACS data."""
    url = (
        "https://www.ncei.noaa.gov/data/"
        "international-best-track-archive-for-climate-stewardship-ibtracs/"
        f"v04r00/access/netcdf/IBTrACS.{dataset}.v04r00.nc"
    )
    download_path = IBTRACS_RAW_DIR / f"IBTrACS.{dataset}.v04r00.nc"
    urllib.request.urlretrieve(url, download_path)


def load_all_ibtracs():
    """Load IBTrACS data from NetCDF file."""
    load_path = IBTRACS_RAW_DIR / "IBTrACS.ALL.v04r00.nc"
    return xr.load_dataset(load_path)


def process_all_ibtracs(wind_provider: Literal["usa", "wmo"] = "wmo"):
    ds = load_all_ibtracs()
    subset_vars = ["sid", f"{wind_provider}_wind", "name"]
    ds_subset = ds[subset_vars]
    str_vars = ["name", "sid"]
    ds_subset[str_vars] = ds_subset[str_vars].astype(str)
    ds_subset["time"] = ds_subset["time"].astype("datetime64[s]")
    df = ds_subset.to_dataframe().dropna().reset_index()
    cols = subset_vars + ["time", "lat", "lon"]
    df = df[cols]
    filestem = f"ibtracs_with_{wind_provider}_wind"
    df["row_id"] = df.index
    df.to_parquet(IBTRACS_PROC_DIR / f"{filestem}.parquet", index=False)


def load_ibtracs_with_wind(wind_provider: Literal["usa", "wmo"] = "wmo"):
    """Load IBTrACS data with wind speed data from a specific provider."""
    load_path = IBTRACS_PROC_DIR / f"ibtracs_with_{wind_provider}_wind.parquet"
    df = pd.read_parquet(load_path)
    geometry = [Point(lon, lat) for lon, lat in zip(df["lon"], df["lat"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    return gdf


def calculate_adm0_distances(
    wind_provider: Literal["usa", "wmo"] = "wmo",
    start_year: int = 2000,
    end_year: int = 2023,
):
    all_adm0 = gaul.load_gaul(admin_level=0)
    all_adm0 = all_adm0.to_crs(3857).set_index("asap0_id")
    gdf = load_ibtracs_with_wind(wind_provider)
    gdf = gdf[
        (gdf["time"].dt.year >= start_year) & (gdf["time"].dt.year <= end_year)
    ]
    gdf = gdf.to_crs(3857)
    save_dir = IBTRACS_PROC_DIR / "adm0_distances"
    for adm0 in tqdm(all_adm0.index):
        adm0_geo = all_adm0.loc[adm0, "geometry"]
        distances = pd.DataFrame()
        distances["distance (m)"] = gdf.geometry.distance(adm0_geo).astype(int)
        distances["row_id"] = gdf["row_id"]
        distances["asap0_id"] = adm0
        filename = (
            f"adm0_{adm0}_distances_"
            f"{wind_provider}_{start_year}-{end_year}.parquet"
        )
        distances.to_parquet(save_dir / filename, index=False)


def concat_adm0_distances(
    wind_provider: Literal["usa", "wmo"] = "wmo",
    start_year: int = 2000,
    end_year: int = 2023,
):
    load_dir = IBTRACS_PROC_DIR / "adm0_distances"
    all_adm0 = gaul.load_gaul(admin_level=0)
    all_adm0 = all_adm0.set_index("asap0_id")
    dfs = []
    for adm0 in tqdm(all_adm0.index):
        filename = (
            f"adm0_{adm0}_distances_"
            f"{wind_provider}_{start_year}-{end_year}.parquet"
        )
        df_in = pd.read_parquet(load_dir / filename)
        dfs.append(df_in)

    all_distances = pd.concat(dfs, ignore_index=True)
    save_dir = DATA_DIR / "public" / "processed" / "glb" / "ibtracs"
    filename = (
        f"all_adm0_distances_{wind_provider}_{start_year}-{end_year}.parquet"
    )
    all_distances.to_parquet(save_dir / filename)


def load_all_adm0_distances(
    wind_provider: Literal["usa", "wmo"] = "wmo",
    start_year: int = 2000,
    end_year: int = 2023,
):
    return pd.read_parquet(
        IBTRACS_PROC_DIR
        / f"all_adm0_distances_{wind_provider}_{start_year}-{end_year}.parquet"
    )


def calculate_thresholds(
    wind_provider: Literal["usa", "wmo"] = "wmo",
    start_year: int = 2000,
    end_year: int = 2023,
):
    speeds = load_ibtracs_with_wind(wind_provider)
    distances = load_all_adm0_distances(wind_provider, start_year, end_year)
    distances = distances.merge(
        speeds[["row_id", "sid", f"{wind_provider}_wind"]], on="row_id"
    )
    d_threshs = range(0, 401, 10)
    s_threshs = range(30, int(speeds[f"{wind_provider}_wind"].max() + 1), 5)

    dfs = []
    for d_thresh in tqdm(d_threshs):
        for s_thresh in s_threshs:
            dff = distances[
                (distances[f"{wind_provider}_wind"] >= s_thresh)
                & (distances["distance (m)"] <= d_thresh * 1000)
            ]
            dff = dff.groupby(["sid", "asap0_id"]).first().reset_index()
            df_add = dff[["sid", "asap0_id"]]
            df_add["d_thresh"] = d_thresh
            df_add["s_thresh"] = s_thresh
            df_add = df_add.astype(
                {col: "int32" for col in ["asap0_id", "d_thresh", "s_thresh"]}
            )
            dfs.append(df_add)

    all_thresholds = pd.concat(dfs, ignore_index=True)
    filename = (
        f"all_adm0_thresholds_{wind_provider}_{start_year}-{end_year}.parquet"
    )
    all_thresholds.to_parquet(IBTRACS_PROC_DIR / filename, index=False)


def load_thresholds(
    wind_provider: Literal["usa", "wmo"] = "wmo",
    start_year: int = 2000,
    end_year: int = 2023,
):
    if start_year == 0 and wind_provider == "wmo":
        filename = "all_adm0_thresholds.parquet"
    else:
        filename = (
            f"all_adm0_thresholds_{wind_provider}"
            f"_{start_year}-{end_year}.parquet"
        )
    return pd.read_parquet(IBTRACS_PROC_DIR / filename)
