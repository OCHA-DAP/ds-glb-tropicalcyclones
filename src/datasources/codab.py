import os
from pathlib import Path

import geopandas as gpd

DATA_DIR = Path(os.getenv("AA_DATA_DIR"))
MOZ_CODAB_DIR = DATA_DIR / "public" / "raw" / "moz" / "cod_ab"


def load_moz_codab(admin_level: int = 0):
    filename = f"moz_admbnda_adm{admin_level}_ine_20190607.shp"
    gdf = gpd.read_file(MOZ_CODAB_DIR / filename)
    return gdf
