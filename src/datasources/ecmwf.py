import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
import pandas as pd

DATA_DIR = Path(os.getenv("AA_DATA_DIR_NEW"))
OLD_DATA_DIR = Path(os.getenv("AA_DATA_DIR"))
SLB_PROC_EC_DIR = (
    DATA_DIR / "public" / "processed" / "slb" / "ecmwf" / "cyclone_hindcasts"
)
ECMWF_RAW = (
    DATA_DIR / "public" / "exploration" / "glb" / "ecmwf" / "cyclone_hindcasts"
)
FJI_CRS = "+proj=longlat +ellps=WGS84 +lon_wrap=180 +datum=WGS84 +no_defs"
KNOTS_PER_MS = 1.94384


def knots2cat(knots: float) -> int:
    """
    Convert from knots to Category (Australian scale)
    Parameters
    ----------
    knots: float
        Wind speed in knots

    Returns
    -------
    Category
    """
    category = 0
    if knots > 107:
        category = 5
    elif knots > 85:
        category = 4
    elif knots > 63:
        category = 3
    elif knots > 47:
        category = 2
    elif knots > 33:
        category = 1
    return category


def xml2csv(filename, valid_names, dry_run: bool = False):
    try:
        tree = ET.parse(filename)
    except ET.ParseError:
        print("Error with file, skipping")
        return
    root = tree.getroot()

    prod_center = root.find("header/productionCenter").text
    baseTime = root.find("header/baseTime").text

    # Create one dictonary for each time point, and append it to a list
    for members in root.findall("data"):
        mtype = members.get("type")
        if mtype not in ["forecast"]:
            continue
        for members2 in members.findall("disturbance"):
            cyclone_name = [
                name.text.lower().strip()
                for name in members2.findall("cycloneName")
            ]
            if not cyclone_name:
                continue
            cyclone_name = cyclone_name[0].lower()
            # basin = members2.find("basin").text
            if cyclone_name not in list(valid_names):
                continue
            # print(f"Found typhoon {cyclone_name}")
            for members3 in members2.findall("fix"):
                tem_dic = {}
                tem_dic["mtype"] = [mtype]
                tem_dic["product"] = [
                    re.sub("\\s+", " ", prod_center).strip().lower()
                ]
                tem_dic["cyc_number"] = [
                    name.text for name in members2.findall("cycloneNumber")
                ]
                tem_dic["ensemble"] = [members.get("member")]
                tem_dic["speed"] = [
                    name.text
                    for name in members3.findall(
                        "cycloneData/maximumWind/speed"
                    )
                ]
                tem_dic["pressure"] = [
                    name.text
                    for name in members3.findall(
                        "cycloneData/minimumPressure/pressure"
                    )
                ]
                time = [name.text for name in members3.findall("validTime")]
                tem_dic["time"] = [
                    "/".join(time[0].split("T")[0].split("-"))
                    + ", "
                    + time[0].split("T")[1][:-1]
                ]
                # set sign of lat/lon based on N/S/E/W
                tem_dic["lat"] = [
                    "-" + name.text
                    if name.attrib.get("units") == "deg S"
                    else name.text
                    for name in members3.findall("latitude")
                ]
                tem_dic["lon"] = [
                    "-" + name.text
                    if name.attrib.get("units") == "deg W"
                    else name.text
                    for name in members3.findall("longitude")
                ]
                tem_dic["lead_time"] = [members3.get("hour")]
                tem_dic["forecast_time"] = [
                    "/".join(baseTime.split("T")[0].split("-"))
                    + ", "
                    + baseTime.split("T")[1][:-1]
                ]
                tem_dic1 = dict(
                    [
                        (k, "".join(str(e).lower().strip() for e in v))
                        for k, v in tem_dic.items()
                    ]
                )
                # Save to CSV
                if not dry_run:
                    outfile = SLB_PROC_EC_DIR / f"csv/{cyclone_name}_all.csv"
                    pd.DataFrame(tem_dic1, index=[0]).to_csv(
                        outfile,
                        mode="a",
                        header=not os.path.exists(outfile),
                        index=False,
                    )


def process_ecmwf_besttrack_hindcasts():
    """
    Take best track forecasts from ECMWF CSVs.
    Also set correct starting year for each cyclone, including ones with
    duplicated years across years, and ones spanning one calendar year to the
    next.
    """
    ecmwf_filelist = os.listdir(SLB_PROC_EC_DIR / "csv")
    ecmwf_filelist = [x for x in ecmwf_filelist if not x.startswith(".")]

    # take only best-track forecasts
    forecast = pd.DataFrame()
    for filename in ecmwf_filelist:
        df = pd.read_csv(SLB_PROC_EC_DIR / "csv" / filename)
        df = df[df["mtype"] == "forecast"]
        drop_cols = ["mtype", "product", "ensemble"]
        df = df.drop(columns=drop_cols)
        df["name"] = filename.split("_")[0]
        forecast = pd.concat([forecast, df], ignore_index=True)

    forecast["time"] = pd.to_datetime(forecast["time"])
    forecast["forecast_time"] = pd.to_datetime(forecast["forecast_time"])
    # deal with "double negatives" (i.e. negative degrees West)
    forecast[["lat", "lon"]] = forecast[["lat", "lon"]].applymap(
        lambda x: str(x).replace("--", "")
    )
    forecast["lon"] = pd.to_numeric(forecast["lon"])
    forecast["lon"] = forecast["lon"].apply(lambda x: x + 360 if x < 0 else x)

    forecast["speed_knots"] = forecast["speed"] * KNOTS_PER_MS
    forecast["category_numeric"] = forecast["speed_knots"].apply(knots2cat)

    # set correct start years for each cylone
    # including duplicate cyclone names
    forecast["year"] = forecast["forecast_time"].dt.year
    forecast = forecast.sort_values("forecast_time")
    forecast["nameyear"] = ""
    for name in forecast["name"].unique():
        dff = forecast[forecast["name"] == name].groupby("year").first()
        if len(dff) == 1:
            forecast.loc[forecast["name"] == name, "nameyear"] = name + str(
                dff.index[0]
            )
            continue
        dff = dff.reset_index()
        j = 0
        while j < len(dff):
            year0 = dff.iloc[j]["year"]
            if j == len(dff) - 1:
                year1 = 0
                forecast.loc[
                    (forecast["name"] == name) & (forecast["year"] == year0),
                    "nameyear",
                ] = name + str(dff.index[0])
            else:
                year1 = dff.iloc[j + 1]["year"]
            if year1 == year0 + 1:
                j += 1
            else:
                year1 = 0
            forecast.loc[
                (forecast["name"] == name)
                & ((forecast["year"] == year0) | (forecast["year"] == year1)),
                "nameyear",
            ] = name + str(year0)
            j += 1

    forecast = forecast.drop(columns="year")
    forecast.to_csv(SLB_PROC_EC_DIR / "besttrack_forecasts.csv", index=False)


def load_ecmwf_besttrack_hindcasts():
    df = pd.read_csv(SLB_PROC_EC_DIR / "besttrack_forecasts.csv")
    cols = ["time", "forecast_time"]
    for col in cols:
        df[col] = pd.to_datetime(df[col])
    gdf = gpd.GeoDataFrame(
        data=df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"], crs="EPSG:4326"),
    )
    gdf = gdf.to_crs(FJI_CRS)
    return gdf
