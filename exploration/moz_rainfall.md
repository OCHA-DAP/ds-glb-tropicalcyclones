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

# Mozambique - rainfall

```python
%load_ext jupyter_black
%load_ext autoreload
%autoreload 2
```

```python
import xarray as xr

from src.datasources import ecmwf, era5
```

```python
years = range(1981, 2024)
```

```python
era5.download_era5_hourly(years)
```

```python

```
