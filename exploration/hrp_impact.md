---
jupyter:
  jupytext:
    formats: ipynb,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.16.1
  kernelspec:
    display_name: ds-glb-tropicalcyclones
    language: python
    name: ds-glb-tropicalcyclones
---

# HRP country impact

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import pandas as pd

from src.datasources import humanitarianinfo, gaul, ibtracs
```

```python
# humanitarianinfo.download_operations_list()
```

```python
# humanitarianinfo.process_operations_list()
```

```python
adm0 = gaul.load_gaul()
adm0 = adm0.sort_values("name0")
adm0["geometry"] = adm0["geometry"].simplify(0.1)
```

```python
for iso2, row in adm0.set_index("isocode").iterrows():
    print([iso2, row["name0"]])
```

```python
df = humanitarianinfo.load_operations_list()
hrp = df[df["Plan type"] == "HRP"]
hrp = hrp.merge(
    adm0[["asap0_id", "isocode", "geometry"]],
    right_on="isocode",
    left_on="ISO2",
)
hrp
```

```python
tracks = ibtracs.load_ibtracs_with_wind("usa")
cyclones = tracks.groupby("sid").first().reset_index()
cyclones["year"] = cyclones["time"].dt.year
```

```python
thresholds = ibtracs.load_thresholds("usa")
thresholds = thresholds.merge(cyclones[["sid", "year", "name"]], on="sid")
thresholds
```

```python
# combine Taiwan and China
thresholds.loc[thresholds["asap0_id"] == 137, "asap0_id"] = 62
```

```python
thresholds = thresholds.drop_duplicates()
```

```python
year_thresh = 2000
max_year = thresholds["year"].max()
d_thresh = 250
major_s_thresh = 95
total_years = max_year - year_thresh

major_triggered = thresholds[
    (thresholds["d_thresh"] == d_thresh)
    & (thresholds["s_thresh"] == major_s_thresh)
    & (thresholds["year"] >= year_thresh)
]
rp = major_triggered.groupby("asap0_id").size().reset_index(name="major_tot")
rp["major_p_yr"] = rp["major_tot"] / total_years

all_triggered = thresholds[
    (thresholds["d_thresh"] == d_thresh)
    & (thresholds["s_thresh"] == thresholds["s_thresh"].min())
    & (thresholds["year"] >= year_thresh)
]
rp_all = all_triggered.groupby("asap0_id").size().reset_index(name="all_tot")
rp_all["all_p_yr"] = rp_all["all_tot"] / total_years

rp = rp.merge(rp_all[["asap0_id", "all_tot", "all_p_yr"]], on="asap0_id")

rp = rp.merge(
    adm0[["asap0_id", "name0", "isocode", "geometry"]],
    on="asap0_id",
    how="outer",
)
cols = [
    "major_tot",
    "major_p_yr",
    "all_tot",
    "all_p_yr",
]
rp[cols] = rp[cols].fillna(0)
cols = [
    "major_tot",
    "all_tot",
]
rp[cols] = rp[cols].astype(int)
# tag countries with HRP
# Hdf_add list taken from 2024 Global HNO
# need to manually add Gaza and West Bank since they do not have a isocode
rp["hrp"] = rp.apply(
    lambda row: row["isocode"] in humanitarianinfo.HRP_2024_ISO2S
    or row["name0"] in ["Gaza Strip", "West Bank"],
    axis=1,
)

rp = gpd.GeoDataFrame(
    data=rp.drop(columns=["geometry"]), geometry=rp["geometry"]
)
rp = rp.sort_values("major_tot", ascending=False)
```

```python
rp
```

```python
rp.sort_values("major_tot", ascending=False).iloc[:10]
```

```python
rp[rp["hrp"]].sort_values("major_tot", ascending=False).iloc[:10]
```

```python
filestem = "cyclone-count-bycountry-stateofdata2024-usawind-2000-2023"
rp.to_file(ibtracs.IBTRACS_PROC_DIR / filestem)
rp.drop(columns="geometry").to_csv(
    ibtracs.IBTRACS_PROC_DIR / f"{filestem}.csv", index=False
)
```

```python
rp.plot(column="all_count", legend=True)
```

```python
rp.hist("all_count", bins=20)
```

```python
fig, ax = plt.subplots(figsize=(15, 15))
adm0.boundary.plot(ax=ax, linewidth=0.05, color="k")

rp_plot = rp.copy()

cutoffs = [4, 8]

bins = [-1, 0, *cutoffs, rp["major_count"].max()]
labels = [
    "0",
    f"1-{cutoffs[0]}",
    f"{cutoffs[0]+1}-{cutoffs[1]}",
    f">{cutoffs[1]}",
]
rp_plot["count_bins"] = pd.cut(
    rp_plot["major_count"], bins=bins, labels=labels
)

hrp_colors = {
    "0": "white",
    f"1-{cutoffs[0]}": "yellow",
    f"{cutoffs[0]+1}-{cutoffs[1]}": "darkorange",
    f">{cutoffs[1]}": "red",
}
nonhrp_colors = {
    "0": "white",
    f"1-{cutoffs[0]}": "gainsboro",
    f"{cutoffs[0]+1}-{cutoffs[1]}": "darkgray",
    f">{cutoffs[1]}": "gray",
}

rp_plot["plot_color"] = rp_plot.apply(
    lambda row: hrp_colors.get(row["count_bins"])
    if row["hrp"]
    else nonhrp_colors.get(row["count_bins"]),
    axis=1,
)

rp_plot.plot(color=rp_plot["plot_color"], ax=ax)

ax.axis("off")

print(hrp_colors)
```

```python
rp[rp["hrp"]]
```

```python
major_triggered["major"] = True
```

```python
all_triggered["major"] = False
```

```python
combined_triggered = pd.concat(
    [major_triggered, all_triggered], ignore_index=True
)
combined_triggered = combined_triggered.drop(columns=["d_thresh", "s_thresh"])
combined_triggered = combined_triggered.drop_duplicates(
    subset=["sid", "asap0_id"]
)
```

```python
len(major_triggered)
```

```python
len(combined_triggered[combined_triggered["major"]])
```

```python
len(all_triggered)
```

```python
len(combined_triggered)
```

```python
combined_triggered
```

```python
filename = "cyclone-ids-bycountry.csv"
combined_triggered.to_csv(ibtracs.IBTRACS_PROC_DIR / filename, index=False)
```

```python
all_tracks = ibtracs.load_ibtracs_with_wmo_wind()
```

```python
all_tracks
```

```python
triggered_tracks = all_tracks[
    all_tracks["sid"].isin(combined_triggered["sid"].unique())
]
triggered_tracks = triggered_tracks.drop(
    columns=["row_id", "geometry", "name"]
)
```

```python
triggered_tracks
```

```python
filename = "cyclone-tracks-closetocountries.csv"
triggered_tracks.to_csv(ibtracs.IBTRACS_PROC_DIR / filename, index=False)
```

```python
tracks = pd.read_csv(
    ibtracs.IBTRACS_PROC_DIR / "cyclone-tracks-closetocountries.csv"
)
cyclones = pd.read_csv(ibtracs.IBTRACS_PROC_DIR / "cyclone-ids-bycountry.csv")
countries = gpd.read_file(
    ibtracs.IBTRACS_PROC_DIR / "cyclone-count-bycountry-stateofdata2024"
)
countries["hrp"] = countries["hrp"].astype(bool)
```

```python
cyclones
```

```python
countries
```

```python
cyclones = cyclones.merge(countries[["asap0_id", "hrp"]], on="asap0_id")
cyclones
```

```python
hrp_major_cyclones = cyclones[cyclones["hrp"] & cyclones["major"]]
hrp_major_cyclone_tracks = tracks[
    tracks["sid"].isin(hrp_major_cyclones["sid"])
]
```
