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

# EMDAT

From [https://public.emdat.be/data](https://public.emdat.be/data)

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import re

import pycountry
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd

from src.datasources import emdat, gaul, ibtracs
```

```python
test = gaul.load_gaul(admin_level=1)
```

```python
test[test["name0"].str.startswith("Haiti")]
```

```python
# emdat.join_emdat_to_ibtracs()
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
cyclones["sid"]
```

```python
thresholds = ibtracs.load_thresholds("wmo", 0)
thresholds = thresholds.merge(
    cyclones[["sid", "name", "nameyear", "year"]], on="sid"
)
```

```python
thresholds
```

```python
thresholds[thresholds["name"] == "TOMAS"].groupby(["sid", "asap0_id"]).first()
```

```python
adm0 = gaul.load_gaul()
```

```python
for _, row in adm0.sort_values("asap0_id").iterrows():
    print(f'{row["asap0_id"]}\t{row["isocode"]}\t{row["name0"]}')
```

```python
for _, row in adm0.sort_values("name0").iterrows():
    print(f'{row["asap0_id"]}\t{row["isocode"]}\t{row["name0"]}')
```

```python
damage = emdat.load_emdat_with_sids()
print(len(damage))
damage["sid"] = damage["sid"].fillna("")
damage = damage.merge(cyclones[["sid", "nameyear"]], on="sid", how="left")
print(len(damage))
```

```python
damage.columns
```

```python
ADJ_DAMAGE = "Total Damage, Adjusted ('000 US$)"
DEATHS = "Total Deaths"
AFFECTED = "Total Affected"
```

```python
iso2 = "FJ"
asap0_id = adm0[adm0["isocode"] == iso2].iloc[0]["asap0_id"]
country_name = adm0[adm0["isocode"] == iso2].iloc[0]["name0"]
year = 2000
d_thresh = 250
s_thresh = 95


thresholds_f = (
    thresholds[
        (thresholds["asap0_id"] == asap0_id) & (thresholds["year"] >= year)
    ]
    .groupby(["nameyear", "d_thresh", "year"])["s_thresh"]
    .max()
    .reset_index()
)
thresholds_f = thresholds_f.sort_values(
    ["year", "d_thresh", "s_thresh"], ascending=False
)
country_cyclones = thresholds[
    (thresholds["asap0_id"] == int(asap0_id))
    & (thresholds["year"] >= int(year))
].copy()
country_cyclones["triggered"] = (country_cyclones["s_thresh"] == s_thresh) & (
    country_cyclones["d_thresh"] == d_thresh
)
country_cyclones = country_cyclones.sort_values("year", ascending=False)
triggered = country_cyclones.groupby("sid")["triggered"].any().reset_index()

damage_f = damage[damage["asap0_id"] == asap0_id].sort_values(AFFECTED)
damage_f = damage_f.merge(triggered, on="sid", how="left")
```

```python
plot_col = ADJ_DAMAGE

df_plot = damage_f.copy()
df_plot = df_plot[df_plot[plot_col] > 0].sort_values(plot_col)
df_plot["color"] = df_plot["triggered"].map(
    {True: "red", False: "blue", np.nan: "grey"}
)

fig = go.Figure()

fig.add_trace(
    go.Bar(
        x=df_plot["nameyear"],
        y=df_plot[plot_col],
        hovertemplate="%{y:,.0f}",
        marker_color=df_plot["color"],
        showlegend=False,
        name="",
    )
)

for legend_name, color in zip(
    ["Triggered", "Not Triggered", "No Track Data"], ["red", "blue", "grey"]
):
    fig.add_trace(
        go.Bar(x=[None], y=[None], marker_color=color, name=legend_name)
    )

fig.update_layout(
    title=(
        f"Cyclone Impact: '{plot_col}'<br>"
        f"<sup>{country_name}, impact data since {max(year, 2000)}</sup>"
    ),
    xaxis_title="Cyclone",
    yaxis_title=plot_col,
    barmode="group",
    height=500,
    template="simple_white",
    legend=dict(
        x=0,
        y=1,
        xanchor="left",
        yanchor="top",
    ),
    margin=dict(t=60),
    hovermode="x",
)
```

```python
fig = px.line(thresholds_f, x="d_thresh", y="s_thresh", color="nameyear")
fig.update_layout(height=600, template="simple_white")
```

```python

```
