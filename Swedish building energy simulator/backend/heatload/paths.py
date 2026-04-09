import json
from pathlib import Path

# Project paths
HEATLOAD_DIR = Path(__file__).parent            # backend/heatload
# BASE_DIR = HEATLOAD_DIR.parent                  # backend/
DATA_DIR = HEATLOAD_DIR / "data"                    # backend/data

IDF_DIR = DATA_DIR / "idf_files"
WEATHER_DIR = DATA_DIR / "weather_files"
MODIFIED_IDF_DIR = DATA_DIR / "modified_idf"

OUTPUT_DIR = HEATLOAD_DIR / "output"
CACHE_DB = HEATLOAD_DIR / "simulation_cache.db"
CONFIG_PATH = HEATLOAD_DIR / "config.json"

# Energy plus
# ENERGYPLUS_EXE = r"C:\EnergyPlusV25-2-0\energyplus.exe"
ENERGYPLUS_PATH = r"C:\EnergyPlusV25-2-0"
ENERGYPLUS_IDD = r"C:\EnergyPlusV25-2-0\Energy+.idd" #NOTE: Det skal måske defineres et andet sted

def set_sql_path(output_dir):
    return output_dir / "eplusout.sql"

def set_output_path(building_type, construction_period, weather_station, output_dir):
    return output_dir / f"{building_type}_{construction_period}_{weather_station}"

def load_config(config_path):
    with open(config_path) as f:
        return json.load(f)