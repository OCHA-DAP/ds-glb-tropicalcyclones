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

# CERF allocations

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import pycountry

from src.datasources import emdat, gaul, ibtracs, cerf
```

```python
cerf.match_cerf_to_iso_asap()
```

```python
tracks = ibtracs.load_ibtracs_with_wind("wmo")
cyclones = tracks.groupby("sid").first().reset_index()
cyclones["year"] = cyclones["time"].dt.year
cyclones["nameyear"] = cyclones.apply(
    lambda row: f'{row["name"].capitalize()} {row["year"]}', axis=1
)
```

```python
thresholds = ibtracs.load_thresholds("wmo", 0)
thresholds = thresholds.merge(
    cyclones[["sid", "name", "nameyear", "year"]], on="sid"
)
thresholds
thresholds_recent = thresholds[thresholds["year"] >= 2000]
```

```python
damage = emdat.load_emdat_with_sids()
```

```python
damage.columns
```

```python
damage[damage["Event Name"].isnull()]
```

```python
damage[damage["iso2"] == "GT"]
```

```python
df = cerf.load_cerf_with_iso()
df = df[df["Emergency"] == "Storm"]
df["asap0_id"] = df["asap0_id"].astype(int)
df["allocation_year"] = df["Allocation date"].dt.year
```

```python
df[df["Country"] == "Fiji"]["Amount in US$"].mean()
```

```python
known_sids = {
    ("Bangladesh", "2020-06-17"): "2020136N10088",
    ("Bangladesh", "2017-06-15"): "2017147N14087",
    ("Bangladesh", "2007-11-19"): "2007314N10093",
    ("Comoros", "2019-05-13"): "2019112S10053",
    ("Cuba", "2022-10-18"): "2022266N12294",
    ("Cuba", "2017-09-28"): "2017242N16333",
    ("Cuba", "2012-11-12"): "2012296N14283",
    (
        "Democratic People's Republic of Korea",
        "2019-10-21",
    ): "2019243N06136",
    ("Dominican Republic", "2007-12-28"): "2007345N18298",
    ("Dominican Republic", "2007-11-09"): "2007297N18300",
    ("El Salvador", "2020-07-08"): "2020152N12269",
    ("Fiji", "2021-02-02"): "2020346S13168",
    ("Fiji", "2020-06-05"): "2020092S09155",
    ("Fiji", "2016-03-08"): "2016041S14170",
    ("Guatemala", "2020-12-15"): "2020306N15288",
    # weirdly, not included in EM-DAT
    ("Guatemala", "2011-11-03"): "2011280N10268",
    ("Guatemala", "2010-06-15"): "2010149N13266",
    ("Haiti", "2016-12-21"): "2016273N13300",
    ("Haiti", "2016-10-19"): "2016273N13300",
    ("Haiti", "2012-11-26"): "2012296N14283",
    # note: next three are actually for Hanna, Gustav, Ike, and Fay
    # but only recording Ike here for simplicity
    ("Haiti", "2008-12-23"): "2008245N17323",
    ("Haiti", "2008-11-28"): "2008245N17323",
    ("Haiti", "2008-09-29"): "2008245N17323",
    # note: for Eta and Iota, only listing Eta here
    ("Honduras", "2020-12-09"): "2020306N15288",
    # note: for Batsirai, Emnati, and Freddy,
    # but none are IBTrACS best track yet
    ("Madagascar", "2023-04-19"): "",
    # note: for Batsirai and Emnati,
    # but none are IBTrACS best track yet
    ("Madagascar", "2022-03-11"): "",
    ("Madagascar", "2013-09-19"): "2013046S20042",
    # Irina and Giovanna, only recording Giovanna
    ("Madagascar", "2012-09-05"): "2012039S14075",
    # Bondo, Clovis, Favio, Gamede, but
    # Favio and Gemede not in EMDAT
    # so using Indhala as it has the most damage
    ("Madagascar", "2007-05-14"): "2007066S12066",
    # also using Clovis for first allocation
    ("Madagascar", "2007-04-11"): "2006364S12058",
    # Freddy for both, but no SID yet
    ("Malawi", "2023-12-14"): "",
    ("Malawi", "2023-03-30"): "",
    # Freddy
    ("Mozambique", "2023-04-05"): "",
    # Gombe, but no SID
    ("Mozambique", "2022-04-07"): "",
    ("Mozambique", "2019-05-16"): "2019112S10053",
    ("Mozambique", "2019-03-28"): "2019063S18038",
    ("Mozambique", "2008-03-20"): "2008062S10064",
    # Iota and Eta, only recording Iota
    ("Nicaragua", "2020-12-24"): "2020318N16289",
    ("Nicaragua", "2009-11-25"): "2009308N11279",
    ("Philippines", "2021-12-31"): "2021346N05145",
    ("Philippines", "2020-11-25"): "2020299N11144",
    ("Philippines", "2015-11-24"): "2015285N14151",
    ("Philippines", "2013-11-15"): "2013306N07162",
    ("Philippines", "2007-07-03"): "2006329N06150",
    ("Vanuatu", "2015-03-27"): "2015066S08170",
    ("Viet Nam", "2017-11-28"): "2017304N11127",
    # Cyclone Mocha, no SID yet
    ("Bangladesh", "2023-06-14"): "",
}
```

```python
def cerf_to_sid(row):
    cerf_id_tuple = (
        row["Country"],
        row["Allocation date"].strftime("%Y-%m-%d"),
    )

    sid = known_sids.get(cerf_id_tuple, None)
    if sid is not None:
        # pass
        return sid

    known_not_cyclone = [
        ("Bangladesh", "2007-08-30"),
        ("Cuba", "2019-03-05"),
        ("Haiti", "2006-06-06"),
    ]
    if cerf_id_tuple in known_not_cyclone:
        return None

    # rule_out = [
    #     ("Colombia", "2010-12-07")
    # ]
    # if (
    #     row["Country"],
    #     row["Allocation date"].strftime("%Y-%m-%d"),
    # ) in rule_out:
    #     return None
    damage_f = damage[
        (damage["iso2"] == row["iso2"])
        & damage["Start Year"].isin(
            [row["allocation_year"], row["allocation_year"] - 1]
        )
    ]
    thresholds_f = thresholds_recent[
        (thresholds_recent["asap0_id"] == row["asap0_id"])
        & (
            thresholds_recent["year"].isin(
                [row["allocation_year"], row["allocation_year"] - 1]
            )
        )
    ]

    if damage_f.empty:
        return None
        # thresholds_f = thresholds_recent[
        #     (thresholds_recent["asap0_id"] == row["asap0_id"])
        #     & (thresholds_recent["year"].isin([row["year"], row["year"] - 1]))
        # ]
        # if thresholds_f.empty:
        #     return None
        # print(row)
        # print(thresholds_f.groupby("sid")["nameyear"].first())
    if len(damage_f) == 1:
        # pass
        print(f"only one for {cerf_id_tuple}")
        return damage_f.iloc[0]["sid"]

    print(cerf_id_tuple)
    cols = [
        "Total Damage, Adjusted ('000 US$)",
        "Total Affected",
        "Total Deaths",
        "sid",
        "Event Name",
        "Start Year",
        "Start Month",
        "End Year",
        "End Month",
    ]
    display(
        damage_f.sort_values(
            [
                "Start Year",
                "Total Damage, Adjusted ('000 US$)",
                "Total Deaths",
            ],
            ascending=False,
        )[cols]
    )
    display(
        thresholds_f.sort_values("s_thresh", ascending=False)
        .groupby("sid")
        .first()
        .sort_values("s_thresh", ascending=False)
    )

    return None


df["sid"] = df.apply(cerf_to_sid, axis=1)
df_withcyclones = df.merge(cyclones[["sid", "nameyear"]], on="sid")
```

```python
df["sid"] = df["sid"].fillna("")
```

```python
df
```

```python
filename = "cerf-storms-with-sids-2024-02-27.csv"
df.to_csv(cerf.CERF_PROC_DIR / filename, index=False)
```

```python

```
