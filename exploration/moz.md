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

# Mozambique analysis

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import pandas as pd
from tqdm.notebook import tqdm

from src.datasources import codab, ibtracs
```

```python
adm1 = codab.load_moz_codab(admin_level=1)
adm1 = adm1.to_crs(3857)
adm1 = adm1.set_index("ADM1_PCODE")
```

```python
adm1.plot()
```

```python
adm1
```

```python
all_tracks = ibtracs.load_ibtracs_with_wind(wind_provider="usa")
all_tracks = all_tracks.to_crs(3857)
```

```python
all_tracks.crs
```

```python
start_year = 1980
end_year = 2023
wind_provider = "usa"

gdf = all_tracks[
    (all_tracks["time"].dt.year >= start_year)
    & (all_tracks["time"].dt.year <= end_year)
]

for adm1_pcode in tqdm(adm1.index):
    adm1_geo = adm1.loc[adm1_pcode, "geometry"]
    distances = pd.DataFrame()
    distances["distance (m)"] = gdf.geometry.distance(adm1_geo).astype(int)
    distances["row_id"] = gdf["row_id"]
    distances["ADM1_PCODE"] = adm1_pcode
    filename = (
        f"adm1_{adm1_pcode}_distances_"
        f"{wind_provider}_{start_year}-{end_year}.parquet"
    )
    distances.to_parquet(
        ibtracs.MOZ_IBTRACS_PROC_DIR / "adm1_distances" / filename, index=False
    )
```

```python
load_dir = ibtracs.MOZ_IBTRACS_PROC_DIR / "adm1_distances"
dfs = []
for adm1_pcode in tqdm(adm1.index):
    filename = (
        f"adm1_{adm1_pcode}_distances_"
        f"{wind_provider}_{start_year}-{end_year}.parquet"
    )
    df_in = pd.read_parquet(load_dir / filename)
    dfs.append(df_in)

all_distances = pd.concat(dfs, ignore_index=True)
filename = (
    f"all_moz_adm1_distances_{wind_provider}_{start_year}-{end_year}.parquet"
)
all_distances.to_parquet(ibtracs.MOZ_IBTRACS_PROC_DIR / filename)
```

```python
gdf["usa_wind"].unique()
```

```python
all_tracks
```

```python
all_distances_sid = all_distances.merge(
    all_tracks[["row_id", "sid", "time", "name", f"{wind_provider}_wind"]],
    on="row_id",
)
d_threshs = range(0, 401, 10)
s_threshs = range(0, int(all_tracks[f"{wind_provider}_wind"].max() + 1), 5)
```

```python
all_tracks[f"{wind_provider}_wind"].hist()
```

```python
all_distances_sid
```

```python
s_threshs
```

```python
dfs = []
for d_thresh in tqdm(d_threshs):
    for s_thresh in s_threshs:
        dff = all_distances_sid[
            (all_distances_sid[f"{wind_provider}_wind"] >= s_thresh)
            & (all_distances_sid["distance (m)"] <= d_thresh * 1000)
        ]
        dff = dff.groupby(["sid", "ADM1_PCODE"]).first().reset_index()
        df_add = dff[["sid", "ADM1_PCODE"]].copy()
        df_add["d_thresh"] = d_thresh
        df_add["s_thresh"] = s_thresh
        df_add = df_add.astype(
            {col: "int32" for col in ["d_thresh", "s_thresh"]}
        )
        dfs.append(df_add)

all_thresholds = pd.concat(dfs, ignore_index=True)
filename = (
    f"all_moz_adm1_thresholds_{wind_provider}_{start_year}-{end_year}.parquet"
)
all_thresholds.to_parquet(ibtracs.MOZ_IBTRACS_PROC_DIR / filename, index=False)
```

```python
# determine close passes by adm1

d_thresh = 250

dff = all_distances_sid[all_distances_sid["distance (m)"] < d_thresh * 1000]
adm1_sid = dff.groupby(["ADM1_PCODE", "sid"])

for (adm1_pcode, sid), group in adm1_sid:
    display(group)

filestem = f"cyclones_within{d_thresh}km_moz_adm1"
dff.drop(columns=["row_id"]).to_csv(
    ibtracs.MOZ_IBTRACS_PROC_DIR / f"{filestem}.csv", index=False
)
dff.drop(columns=["row_id"]).to_parquet(
    ibtracs.MOZ_IBTRACS_PROC_DIR / f"{filestem}.parquet", index=False
)
```

```python
d_thresh = 100

dff = all_distances_sid[all_distances_sid["distance (m)"] < d_thresh * 1000]
adm1_sid = dff.groupby(["ADM1_PCODE", "sid"])

dicts = []
for (adm1_pcode, sid), group in adm1_sid:
    name = group.iloc[0]["name"]
    max_wind = group["usa_wind"].max()
    closest_date = group.loc[group["distance (m)"].idxmax()]["time"]
    dicts.append(
        {
            "closest_date": closest_date,
            f"max_wind_within_{d_thresh}km": max_wind,
            "name": name,
            "sid": sid,
            "ADM1_PCODE": adm1_pcode,
        }
    )
```

```python
closest_dates = pd.DataFrame(dicts)
```

```python
closest_dates
```

```python
filestem = f"closest_passes_within{d_thresh}km_moz_adm1"
closest_dates.to_csv(
    ibtracs.MOZ_IBTRACS_PROC_DIR / f"{filestem}.csv", index=False
)
closest_dates.to_parquet(
    ibtracs.MOZ_IBTRACS_PROC_DIR / f"{filestem}.parquet", index=False
)
```

```python
len(dff[dff["time"].dt.year >= 2000]["sid"].unique())
```

```python
closest_dates["max_wind_within_100km"].hist()
```

```python

```
