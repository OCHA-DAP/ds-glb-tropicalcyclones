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

# ECMWF forecast plot

For Harold in Solomon Islands

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import plotly.graph_objects as go
import numpy as np
import matplotlib.pyplot as plt

from src.datasources import ecmwf, gaul, ibtracs
```

```python
tracks = ibtracs.load_ibtracs_with_wind()
cyclones = tracks.groupby("sid").first()
```

```python
cyclones["year"] = cyclones["time"].dt.year
cyclones["nameyear"] = cyclones["name"].str.lower() + cyclones["year"].astype(
    str
)
```

```python
cyclones
```

```python
0.15*45+(0.15+0.2)*(15+60)
```

```python
all_forecasts = ecmwf.load_ecmwf_besttrack_hindcasts()
```

```python
all_forecasts["nameyear"].unique()
```

```python
adm0 = gaul.load_gaul()
adm0 = adm0[adm0["name0"].str.contains("Solomon")]
```

```python
adm0
```

```python
buffer_km = 250
trigger_zone = adm0.to_crs(3857).buffer(buffer_km * 1000).to_crs(4326)
```

```python
trigger_zone
```

```python
nameyear = "ului2010"
# nameyear = "harold2020"
# nameyear = "yasi2011"
sid = cyclones[cyclones["nameyear"] == nameyear].index[0]
print(sid)
single_actual = tracks[tracks["sid"] == sid].copy()
single_actual["category"] = single_actual["wmo_wind"].apply(ecmwf.knots2cat)
single_forecast = all_forecasts[all_forecasts["nameyear"] == nameyear]
single_forecast = single_forecast.sort_values(["forecast_time", "time"])
single_forecast["category+1"] = single_forecast["category_numeric"].apply(
    lambda x: min(5, x + 1)
)
single_forecast
```

```python
single_actual
```

```python
fig = go.Figure()

x, y = trigger_zone.iloc[0].boundary.xy

# trigger zone
fig.add_trace(
    go.Scattermapbox(
        lat=np.array(y),
        lon=np.array(x),
        mode="lines",
        name="Area within 250km of Sols",
        line=dict(width=1, color="dodgerblue"),
        hoverinfo="skip",
        # showlegend=False,
    )
)

# actual
fig.add_trace(
    go.Scattermapbox(
        lat=single_actual["lat"],
        lon=single_actual["lon"],
        text=single_actual["category"].astype(str),
        mode="text+lines",
        name="Actual",
        line=dict(width=2, color="black"),
        textfont=dict(size=20, color="black"),
        customdata=single_actual[["wmo_wind", "time"]],
        hovertemplate="Wind speed: %{customdata[0]} knots<br>"
        "Datetime: %{customdata[1]}",
        visible="legendonly",
        # hoverinfo="skip",
        # showlegend=False,
    )
)


# forecasts
for forecast_time, group in single_forecast.groupby("forecast_time"):
    # display(group)
    fig.add_trace(
        go.Scattermapbox(
            lon=group["lon"],
            lat=group["lat"],
            mode="lines+text",
            text=group["category+1"].astype(str),
            textfont=dict(size=20, color="black"),
            # line=dict(color="black", width=2),
            marker=dict(size=5),
            name=forecast_time.strftime("%Y-%m-%d %H:%M"),
            customdata=group[["speed_knots", "time"]],
            hovertemplate="Wind speed: %{customdata[0]:.0f} knots<br>"
            "Datetime: %{customdata[1]}",
            # legendgroup="actual",
            # legendgrouptitle_text="",
            visible="legendonly",
        )
    )

fig.add_annotation(
    x=0.01,
    y=0.99,
    xref="paper",
    yref="paper",
    text=f'Cyclone {single_actual.iloc[0]["name"].capitalize()} '
    f'{single_actual.iloc[0]["time"].year}',
    showarrow=False,
    font=dict(size=20, color="black"),
)

fig.update_layout(
    mapbox_style="open-street-map",
    # mapbox_accesstoken=os.getenv("MB_TOKEN"),
    mapbox_zoom=5,
    mapbox_center_lat=-9,
    mapbox_center_lon=162,
    margin={"r": 0, "t": 0, "l": 0, "b": 0, "pad": 0},
    autosize=True,
    # title=f"{name_season}<br>" f"<sup>{subtitle}</sup>",
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="right",
        x=0.99,
        bgcolor="rgba(255,255,255,0.5)",
    ),
)

fig_config = config = {"displayModeBar": False, "showTips": False}

fig.show(
    config=fig_config,
)

# save as html
filename = f"{nameyear}_forecasts.html"

f = open(ecmwf.SLB_PROC_EC_DIR / "plots" / filename, "w")
f.close()
with open(ecmwf.SLB_PROC_EC_DIR / "plots" / filename, "a") as f:
    f.write(
        fig.to_html(
            full_html=True,
            include_plotlyjs="cdn",
            auto_play=False,
            config=fig_config,
        )
    )
f.close()
```

```python
fig, ax = plt.subplots()
single_forecast.groupby("forecast_time").first().plot.line(
    x="time", y="speed_knots", ax=ax
)
single_actual.plot.line(x="time", y="wmo_wind", ax=ax)
```

```python

```
