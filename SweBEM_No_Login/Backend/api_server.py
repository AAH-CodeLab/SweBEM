#!/usr/bin/env python3
"""
Energy Simulation API Server
=============================

FastAPI backend that runs EnergyPlus simulations on-demand with SQLite caching.

SETUP:
    pip install fastapi uvicorn requests

RUN:
    python api_server.py

API will be available at http://localhost:8000
"""

import os
import sys
import json
import sqlite3
import subprocess
import time
import re
import math
import zipfile
import io
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal
from contextlib import contextmanager

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    import uvicorn
except ImportError:
    print("\n❌ Please install dependencies:")
    print("   pip install fastapi uvicorn requests")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("\n❌ Please install requests:")
    print("   pip install requests")
    sys.exit(1)

# ============================================================================
# CONFIGURATION - EDIT THESE!
# ============================================================================

# Path to the EnergyPlus executable. Set the ENERGYPLUS_PATH environment variable
# to override the default. Energy+.idd is looked up in the same folder.
ENERGYPLUS_PATH = os.environ.get("ENERGYPLUS_PATH", r"C:\EnergyPlusV25-2-0\energyplus.exe")

BASE_DIR = Path(__file__).parent
IDF_DIR = BASE_DIR / "idf_files"
WEATHER_DIR = BASE_DIR / "weather_files"
MODIFIED_IDF_DIR = BASE_DIR / "modified_idf"
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DB = BASE_DIR / "simulation_cache.db"

for d in [IDF_DIR, WEATHER_DIR, MODIFIED_IDF_DIR, OUTPUT_DIR]:
    d.mkdir(exist_ok=True)

ALL_IDF_FILES = {
    "single-family-house": {
        "before-1961": "sfh/SFH_before-1961.idf",
        "1961-1975":   "sfh/SFH_1961-1975.idf",
        "1976-1985":   "sfh/SFH_1976-1985.idf",
        "1986-1995":   "sfh/SFH_1986-1995.idf",
        "1996-2005":   "sfh/SFH_1996-2005.idf",
    },
    "mid-rise-apartment": {
        "before-1961": "mfd/MFD_before-1961.idf",
        "1961-1975":   "mfd/MFD_1961-1975.idf",
        "1976-1985":   "mfd/MFD_1976-1985.idf",
        "1986-1995":   "mfd/MFD_1986-1995.idf",
        "1996-2005":   "mfd/MFD_1996-2005.idf",
    },
    "office": {
        "before-1961": "office/Office_before-1961.idf",
        "1961-1975":   "office/Office_1961-1975.idf",
        "1976-1985":   "office/Office_1976-1985.idf",
        "1986-1995":   "office/Office_1986-1995.idf",
        "1996-2005":   "office/Office_1996-2005.idf",
    },
    "hotel": {
        "before-1961": "hotel/Hotel_before-1961.idf",
        "1961-1975":   "hotel/Hotel_1961-1975.idf",
        "1976-1985":   "hotel/Hotel_1976-1985.idf",
        "1986-1995":   "hotel/Hotel_1986-1995.idf",
        "1996-2005":   "hotel/Hotel_1996-2005.idf",
    },
    "school": {
        "before-1961": "school/School_before-1961.idf",
        "1961-1970":   "school/School_1961-1970.idf",
        "1971-1980":   "school/School_1971-1980.idf",
        "1981-1990":   "school/School_1981-1990.idf",
        "1991-2000":   "school/School_1991-2000.idf",
        "2000+":       "school/School_2000plus.idf",
    },
    "hospital": {
        "before-1961": "hospital/Hospital_before-1961.idf",
        "1961-1970":   "hospital/Hospital_1961-1970.idf",
        "1971-1980":   "hospital/Hospital_1971-1980.idf",
        "1981-1990":   "hospital/Hospital_1981-1990.idf",
        "1991-2000":   "hospital/Hospital_1991-2000.idf",
        "2000+":       "hospital/Hospital_2000plus.idf",
    },
    # Retail: ASHRAE 90.1-2022 RetailStandalone prototype. Single period only.
    # Place IDF at: backend/idf_files/retail/Retail_post2000.idf
    "retail": {
        "2000+": "retail/Retail_post2000.idf",
    },
    # Warehouse: ASHRAE 90.1-2022 Warehouse (Shurgard) prototype. Single period only.
    # Place IDF at: backend/idf_files/warehouse/Warehouse_post2000.idf
    "warehouse": {
        "2000+": "warehouse/Warehouse_post2000.idf",
    },
}

BASE_URL = "https://climate.onebuilding.org/WMO_Region_6_Europe/SWE_Sweden"

# 56 Swedish Weather Stations (matching frontend sweden-map.tsx)
REGIONS = {
    "NB_Norrbotten": [
        'kiruna', 'gallivare', 'lulea', 'boden', 'haparanda', 
        'pajala', 'jokkmokk', 'arvidsjaur'
    ],
    "VB_Vasterbotten": [
        'umea', 'skelleftea', 'lycksele', 'vilhelmina', 'storuman'
    ],
    "JA_Jamtland": [
        'ostersund', 'are', 'sveg'
    ],
    "VN_Vasternorrland": [
        'sundsvall', 'harnosand', 'ornskoldsvik'
    ],
    "GV_Gavleborg": [
        'gavle', 'soderhamn'
    ],
    "KO_Dalarna": [
        'borlange', 'mora', 'malung', 'idre'
    ],
    "VR_Varmland": [
        'karlstad', 'arvika', 'torsby'
    ],
    "OR_Orebro": [
        'orebro'
    ],
    "VM_Vastmanland": [
        'vasteras'
    ],
    "UP_Uppsala": [
        'uppsala'
    ],
    "ST_Stockholm": [
        'stockholm', 'stockholm-arlanda', 'stockholm-bromma'
    ],
    "SD_Sodermanland": [
        'eskilstuna', 'nykoping'
    ],
    "OG_Ostergotland": [
        'norrkoping', 'linkoping'
    ],
    "JO_Jonkoping": [
        'jonkoping'
    ],
    "KR_Kronoberg": [
        'vaxjo', 'ljungby'
    ],
    "KA_Kalmar": [
        'kalmar'
    ],
    "GT_Gotland": [
        'visby'
    ],
    "BL_Blekinge": [
        'karlskrona', 'ronneby'
    ],
    "SN_Skane": [
        'malmo', 'lund', 'helsingborg', 'kristianstad', 'angelholm'
    ],
    "HA_Halland": [
        'halmstad'
    ],
    "VG_Vastra_Gotaland": [
        'goteborg', 'goteborg-landvetter', 'trollhattan', 'skovde', 'satenas'
    ],
}

# Station ID to EPW filename mapping (verified on climate.onebuilding.org)
# 56 stations matching frontend sweden-map.tsx
STATION_FILENAMES = {
    # Norrbotten (8 stations)
    "kiruna": "SWE_NB_Kiruna.AP",
    "gallivare": "SWE_NB_Gallivare-Lapland-Malmberget",
    "lulea": "SWE_NB_Lulea.AP",
    "boden": "SWE_NB_Boden",
    "haparanda": "SWE_NB_Haparanda",
    "pajala": "SWE_NB_Pajala",
    "jokkmokk": "SWE_NB_Jokkmokk.AP",
    "arvidsjaur": "SWE_NB_Arvidsjaur.AP",
    # Västerbotten (5 stations)
    "umea": "SWE_VB_Umea.AP",
    "skelleftea": "SWE_VB_Skelleftea.AP",
    "lycksele": "SWE_VB_Lycksele.AP",
    "vilhelmina": "SWE_VB_Vilhelmina.Lansen.AP",
    "storuman": "SWE_VB_Gunnarn-Storuman.AP",
    # Jämtland (3 stations)
    "ostersund": "SWE_JA_Ostersund-Froson.AP",
    "are": "SWE_JA_Are",
    "sveg": "SWE_JA_Harjedalen.Sveg.AP",
    # Västernorrland (3 stations)
    "sundsvall": "SWE_VN_Harnosand-Sundsvall.Timra.AP",
    "harnosand": "SWE_VN_Harnosand-Sundsvall.Timra.AP",
    "ornskoldsvik": "SWE_VN_Ornskoldsvik.AP",
    # Gävleborg (2 stations)
    "gavle": "SWE_GV_Gavle",
    "soderhamn": "SWE_GV_Soderhamn-Helsinge.AP",
    # Dalarna (4 stations)
    "borlange": "SWE_KO_Borlange-Dala.AP",
    "mora": "SWE_KO_Mora-Siljan.AP",
    "malung": "SWE_KO_Malung",
    "idre": "SWE_KO_Idre",
    # Värmland (3 stations)
    "karlstad": "SWE_VR_Karlstad.AP",
    "arvika": "SWE_VR_Arvika.AP",
    "torsby": "SWE_VR_Torsby.AP",
    # Örebro (1 station)
    "orebro": "SWE_OR_Orebro.AP",
    # Västmanland (1 station)
    "vasteras": "SWE_VM_Stockholm.Vasteras.AP",
    # Uppsala (1 station)
    "uppsala": "SWE_UP_Uppsala-Arna.AP",
    # Stockholm (3 stations)
    "stockholm": "SWE_ST_Stockholm",
    "stockholm-arlanda": "SWE_ST_Stockholm.Arlanda.AP",
    "stockholm-bromma": "SWE_ST_Stockholm.Bromma.AP",
    # Södermanland (2 stations)
    "eskilstuna": "SWE_SD_Eskilstuna.AP",
    "nykoping": "SWE_SD_Stockholm.Skavsta.AP-Nykoping",
    # Östergötland (2 stations)
    "norrkoping": "SWE_OG_Norrkoping.AP",
    "linkoping": "SWE_OG_Linkoping.AP",
    # Jönköping (1 station)
    "jonkoping": "SWE_JO_Jonkoping.AP",
    # Kronoberg (2 stations)
    "vaxjo": "SWE_KR_Vaxjo",
    "ljungby": "SWE_KR_Ljungby",
    # Kalmar (1 station)
    "kalmar": "SWE_KA_Kalmar.AP",
    # Gotland (1 station)
    "visby": "SWE_GT_Visby.AP",
    # Blekinge (2 stations)
    "karlskrona": "SWE_BL_Karlskrona-Soderstjerna",
    "ronneby": "SWE_BL_Ronneby.AP",
    # Skåne (5 stations)
    "malmo": "SWE_SN_Malmo",
    "lund": "SWE_SN_Lund.Sol",
    "helsingborg": "SWE_SN_Helsingborg",
    "kristianstad": "SWE_SN_Kristianstad.AP",
    "angelholm": "SWE_SN_Angelholm-Helsingborg.AP",
    # Halland (1 station)
    "halmstad": "SWE_HA_Halmstad",
    # Västra Götaland (5 stations)
    "goteborg": "SWE_VG_Gothenburg-Landvetter.AP",
    "goteborg-landvetter": "SWE_VG_Gothenburg-Landvetter.AP",
    "trollhattan": "SWE_VG_Trollhattan.Vanersborg.AP",
    "skovde": "SWE_VG_Skovde.AP",
    "satenas": "SWE_VG_Satenas.AP",
}

# Legacy mappings for backwards compatibility
STATION_MAPPINGS = {
    # No longer needed - station IDs now match frontend directly
}

# ============================================================================
# DATABASE
# ============================================================================

def init_database():
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulation_cache (
            id TEXT PRIMARY KEY,
            weather_station TEXT,
            construction_period TEXT,
            building_type TEXT,
            annual_results TEXT,
            hourly_results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    print(f"✓ Database initialized: {CACHE_DB}")

@contextmanager
def get_db():
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_cache_id(weather_station, construction_period, building_type):
    key = f"{weather_station}_{construction_period}_{building_type}"
    return hashlib.md5(key.encode()).hexdigest()

def get_cached_result(weather_station, construction_period, building_type):
    cache_id = get_cache_id(weather_station, construction_period, building_type)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT annual_results, hourly_results FROM simulation_cache WHERE id = ?', (cache_id,))
        row = cursor.fetchone()
        if row:
            return {
                "annual": json.loads(row["annual_results"]),
                "hourly": json.loads(row["hourly_results"]),
                "cached": True
            }
    return None

def save_to_cache(weather_station, construction_period, building_type, annual, hourly):
    cache_id = get_cache_id(weather_station, construction_period, building_type)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO simulation_cache 
            (id, weather_station, construction_period, building_type, annual_results, hourly_results)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cache_id, weather_station, construction_period, building_type, json.dumps(annual), json.dumps(hourly)))
        conn.commit()

# ============================================================================
# WEATHER
# ============================================================================

def find_region_for_station(station_id):
    search_term = STATION_MAPPINGS.get(station_id, station_id)
    for region, cities in REGIONS.items():
        if search_term in cities:
            return region
    return None

def discover_epw_url(station_id):
    """Get EPW download URL. Uses STATION_FILENAMES for accurate matching."""
    lookup_id = STATION_MAPPINGS.get(station_id, station_id)
    region = find_region_for_station(station_id)
    if not region:
        return None
    
    # Get the filename pattern for this station
    filename = STATION_FILENAMES.get(lookup_id, lookup_id)
    region_url = f"{BASE_URL}/{region}/"
    
    try:
        response = requests.get(region_url, timeout=30)
        if response.status_code != 200:
            return None
        html = response.text
        all_zips = re.findall(r'href="([^"]+\.zip)"', html)
        
        # First try 2009-2023 data
        for zf in all_zips:
            if filename in zf and "2009-2023" in zf:
                return f"{BASE_URL}/{region}/{zf}"
        
        # Then try any TMYx
        for zf in all_zips:
            if filename in zf and "TMYx" in zf:
                return f"{BASE_URL}/{region}/{zf}"
        
        # Fallback to search term matching
        search_term = lookup_id
        for zf in all_zips:
            if search_term in zf.lower():
                if "2009-2023" in zf:
                    return f"{BASE_URL}/{region}/{zf}"
        for zf in all_zips:
            if search_term in zf.lower() and "TMYx" in zf:
                return f"{BASE_URL}/{region}/{zf}"
        
        return None
    except:
        return None

def download_epw(station_id):
    epw_path = WEATHER_DIR / f"{station_id}.epw"
    if epw_path.exists():
        return epw_path
    url = discover_epw_url(station_id)
    if not url:
        print(f"Could not find EPW URL for {station_id}")
        return None
    print(f"Downloading EPW for {station_id}...")
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            epw_files = [f for f in zf.namelist() if f.endswith('.epw')]
            if not epw_files:
                return None
            with open(epw_path, 'wb') as f:
                f.write(zf.read(epw_files[0]))
            print(f"✓ Downloaded: {epw_path}")
            return epw_path
    except Exception as e:
        print(f"Error downloading EPW: {e}")
        return None

# ============================================================================
# GROUND TEMPS
# ============================================================================

def calculate_ground_temps_and_location(epw_path):
    """
    Extract ground temperatures and location from EPW file.
    
    Ground temps are read directly from EPW header line 4 (GROUND TEMPERATURES).
    This is more accurate than Kusuda formula because EPW values are based on
    site-specific soil models accounting for soil type, groundwater, snow cover.
    
    Falls back to Kusuda calculation if EPW doesn't have ground temp data.
    """
    lat, lon, elev = 60.0, 15.0, 100
    ground_temps = None
    
    try:
        with open(epw_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Parse header line 1: Location (lat, lon, elevation)
        if lines:
            h = lines[0].split(',')
            if len(h) > 9:
                try:
                    lat, lon, elev = float(h[6]), float(h[7]), float(h[9])
                except:
                    pass
        
        # Parse header line 4: Ground Temperatures
        # Format: GROUND TEMPERATURES,N,depth1,cond,dens,cp,jan,feb,...,dec,depth2,...
        for line in lines[:10]:
            if line.startswith('GROUND TEMPERATURES'):
                parts = line.split(',')
                num_depths = int(parts[1])
                
                # Find the depth closest to 2.0m
                best_depth = None
                best_temps = None
                idx = 2
                
                for d in range(num_depths):
                    depth = float(parts[idx])
                    # Extract 12 monthly values (skip 4 fields: depth, conductivity, density, specific heat)
                    monthly = []
                    for m in range(12):
                        val = parts[idx + 4 + m].strip()
                        monthly.append(float(val) if val else 0)
                    
                    # Prefer depth closest to 2.0m
                    if best_depth is None or abs(depth - 2.0) < abs(best_depth - 2.0):
                        best_depth = depth
                        best_temps = monthly
                    
                    idx += 16  # Move to next depth section
                
                if best_temps:
                    ground_temps = best_temps
                    print(f"✓ Using EPW ground temps at {best_depth}m depth")
                break
        
        # Fallback: Calculate using Kusuda formula if no ground temps in EPW
        if ground_temps is None:
            print("⚠ No ground temps in EPW, using Kusuda formula")
            ground_temps = _calculate_kusuda_ground_temps(lines)
        
        return ground_temps, lat, lon, elev
        
    except Exception as e:
        print(f"Error reading EPW: {e}")
        return [4, 2.5, 2, 3, 6, 10, 13, 15, 14, 12, 9, 6], lat, lon, elev


def _calculate_kusuda_ground_temps(lines):
    """
    Fallback: Calculate ground temps using Kusuda-Achenbach formula.
    Only used if EPW file doesn't contain ground temperature data.
    """
    monthly_temps = [[] for _ in range(12)]
    
    for line in lines[8:]:
        p = line.strip().split(',')
        if len(p) >= 7:
            try:
                month = int(p[1]) - 1
                temp = float(p[6])
                if -60 < temp < 60:
                    monthly_temps[month].append(temp)
            except:
                pass
    
    monthly_avg = [sum(t)/len(t) if t else 5 for t in monthly_temps]
    t_avg = sum(monthly_avg) / 12
    t_amp = (max(monthly_avg) - min(monthly_avg)) / 2
    min_month = monthly_avg.index(min(monthly_avg))
    t0 = min_month * 30.5 + 15
    
    alpha, z = 0.04, 2.0
    ground_temps = []
    
    for m in range(12):
        t = m * 30.5 + 15
        exp_term = math.exp(-z * math.sqrt(math.pi / (365 * alpha)))
        phase = z / 2 * math.sqrt(365 / (math.pi * alpha))
        tg = t_avg - t_amp * exp_term * math.cos(2 * math.pi / 365 * (t - t0 - phase))
        ground_temps.append(round(tg, 2))
    
    return ground_temps

# ============================================================================
# IDF MODIFICATION
# ============================================================================

def modify_idf(idf_content, station_id, lat, lon, elev, ground_temps):
    content = idf_content
    location_pattern = r'(Site:Location,\s*)[^;]+'
    location_replacement = f'''Site:Location,
    {station_id},              !- Name
    {lat},                     !- Latitude
    {lon},                     !- Longitude
    1,                         !- Time Zone (CET)
    {elev}'''
    content = re.sub(location_pattern, location_replacement, content, flags=re.IGNORECASE)
    gt_pattern = r'Site:GroundTemperature:BuildingSurface,[^;]+'
    gt_str = ','.join([f'{t:.1f}' for t in ground_temps])
    gt_replacement = f'''Site:GroundTemperature:BuildingSurface,
    {gt_str}'''
    content = re.sub(gt_pattern, gt_replacement, content, flags=re.IGNORECASE)
    
    # Add hourly output variables for heating and cooling power
    hourly_outputs = '''

!-   ===========  HOURLY OUTPUT VARIABLES (ADDED BY API) ===========

Output:Variable,
    *,                       !- Key Value
    Zone Ideal Loads Supply Air Total Heating Rate,  !- Variable Name
    Hourly;                  !- Reporting Frequency

Output:Variable,
    *,                       !- Key Value
    Zone Ideal Loads Supply Air Total Cooling Rate,  !- Variable Name
    Hourly;                  !- Reporting Frequency

Output:Variable,
    *,                       !- Key Value
    Facility Total Electric Demand Power,  !- Variable Name
    Hourly;                  !- Reporting Frequency

Output:Meter,
    Heating:EnergyTransfer,  !- Key Name
    Hourly;                  !- Reporting Frequency

Output:Meter,
    Cooling:EnergyTransfer,  !- Key Name
    Hourly;                  !- Reporting Frequency

'''
    content += hourly_outputs
    return content

# ============================================================================
# SIMULATION
# ============================================================================

def run_energyplus(idf_path, epw_path, output_dir):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    cmd = [ENERGYPLUS_PATH, "-w", str(epw_path), "-d", str(output_dir), "-r", str(idf_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        sql_path = output_dir / "eplusout.sql"
        if sql_path.exists():
            return output_dir
        # Print EnergyPlus error file if available
        err_path = output_dir / "eplusout.err"
        if err_path.exists():
            err_text = err_path.read_text(encoding="utf-8", errors="ignore")
            # Print last 60 lines of error file
            lines = err_text.strip().splitlines()
            print("\n=== EnergyPlus Error Output ===")
            print("\n".join(lines[-60:]))
            print("=== End Error Output ===\n")
        else:
            print(f"EnergyPlus stdout: {result.stdout[-2000:]}")
            print(f"EnergyPlus stderr: {result.stderr[-2000:]}")
        return None
    except subprocess.TimeoutExpired:
        print("EnergyPlus simulation timed out after 600 seconds")
        return None
    except Exception as e:
        print(f"EnergyPlus failed: {e}")
        return None

# ============================================================================
# RESULT PARSING (FIXED)
# ============================================================================

def parse_annual_results(sql_path):
    if not sql_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(sql_path))
        c = conn.cursor()
        end_uses = {}
        
        # Try kWh first
        c.execute("""SELECT RowName, Value FROM TabularDataWithStrings 
                     WHERE TableName='End Uses' AND ColumnName='Electricity' AND Units='kWh'""")
        rows = c.fetchall()
        if rows:
            for r in rows:
                name = r[0].strip() if r[0] else ""
                val = float(r[1]) if r[1] else 0
                end_uses[name] = round(val, 2)
        
        # Try GJ
        if not end_uses:
            c.execute("""SELECT RowName, Value FROM TabularDataWithStrings 
                         WHERE TableName='End Uses' AND ColumnName='Electricity' AND Units='GJ'""")
            rows = c.fetchall()
            for r in rows:
                name = r[0].strip() if r[0] else ""
                val = float(r[1]) * 277.778 if r[1] else 0
                end_uses[name] = round(val, 2)
        
        # Try Total Energy
        if not end_uses:
            c.execute("""SELECT RowName, Value FROM TabularDataWithStrings 
                         WHERE TableName='End Uses' AND ColumnName='Total Energy'""")
            rows = c.fetchall()
            for r in rows:
                name = r[0].strip() if r[0] else ""
                val = float(r[1]) if r[1] else 0
                end_uses[name] = round(val * 277.778 if val < 1000 else val, 2)
        
        # Floor area
        area = 125.0
        c.execute("""SELECT Value FROM TabularDataWithStrings 
                     WHERE TableName='Building Area' AND RowName='Net Conditioned Building Area'""")
        r = c.fetchone()
        if r and r[0]:
            try:
                area = float(r[0])
            except:
                pass
        
        conn.close()
        
        result = {
            "heating": end_uses.get("Heating", 0),
            "cooling": end_uses.get("Cooling", 0),
            "dhw": end_uses.get("Water Systems", 0),
            "lighting": end_uses.get("Interior Lighting", 0) + end_uses.get("Exterior Lighting", 0),
            "equipment": end_uses.get("Interior Equipment", 0) + end_uses.get("Exterior Equipment", 0),
            "fans": end_uses.get("Fans", 0),
            "floor_area": round(area, 1),
        }
        result["total"] = round(sum([result["heating"], result["cooling"], result["dhw"],
                                     result["lighting"], result["equipment"], result["fans"]]), 2)
        result["eui"] = round(result["total"] / area, 1) if area > 0 else 0
        result["peak_power_kw"] = 0
        result["peak_heating_kw"] = 0
        result["peak_cooling_kw"] = 0
        result["avg_power_kw"] = 0
        return result
    except Exception as e:
        print(f"Error parsing annual: {e}")
        return None

def parse_hourly_results(sql_path):
    if not sql_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(sql_path))
        c = conn.cursor()
        
        heating_power = [0.0] * 8760
        cooling_power = [0.0] * 8760
        total_power = [0.0] * 8760
        
        # Get available variables
        c.execute("SELECT ReportDataDictionaryIndex, Name FROM ReportDataDictionary")
        available_vars = {r[0]: r[1] for r in c.fetchall()}
        
        heating_indices = [idx for idx, name in available_vars.items() if 'Heating' in name and 'Rate' in name]
        cooling_indices = [idx for idx, name in available_vars.items() if 'Cooling' in name and 'Rate' in name]
        power_indices = [idx for idx, name in available_vars.items() 
                        if 'Rate' in name and ('Heating' in name or 'Cooling' in name or 'Fan' in name or 'Electricity' in name)]
        
        if heating_indices:
            placeholders = ','.join(['?'] * len(heating_indices))
            c.execute(f"SELECT TimeIndex, SUM(Value) FROM ReportData WHERE ReportDataDictionaryIndex IN ({placeholders}) GROUP BY TimeIndex", heating_indices)
            for row in c.fetchall():
                idx = int(row[0]) - 1
                if 0 <= idx < 8760:
                    heating_power[idx] = float(row[1]) / 1000.0 if row[1] else 0
        
        if cooling_indices:
            placeholders = ','.join(['?'] * len(cooling_indices))
            c.execute(f"SELECT TimeIndex, SUM(Value) FROM ReportData WHERE ReportDataDictionaryIndex IN ({placeholders}) GROUP BY TimeIndex", cooling_indices)
            for row in c.fetchall():
                idx = int(row[0]) - 1
                if 0 <= idx < 8760:
                    cooling_power[idx] = float(row[1]) / 1000.0 if row[1] else 0
        
        if power_indices:
            placeholders = ','.join(['?'] * len(power_indices))
            c.execute(f"SELECT TimeIndex, SUM(Value) FROM ReportData WHERE ReportDataDictionaryIndex IN ({placeholders}) GROUP BY TimeIndex", power_indices)
            for row in c.fetchall():
                idx = int(row[0]) - 1
                if 0 <= idx < 8760:
                    total_power[idx] = float(row[1]) / 1000.0 if row[1] else 0
        
        conn.close()
        
        heating_power = [round(p, 2) for p in heating_power]
        cooling_power = [round(p, 2) for p in cooling_power]
        total_power = [round(p, 2) for p in total_power]
        
        if max(total_power) == 0:
            total_power = [round(h + c, 2) for h, c in zip(heating_power, cooling_power)]
        
        return {
            "heating_power_kw": heating_power,
            "cooling_power_kw": cooling_power,
            "total_power_kw": total_power,
            "peak_power_kw": round(max(total_power), 2),
            "peak_heating_kw": round(max(heating_power), 2),
            "peak_cooling_kw": round(max(cooling_power), 2),
            "avg_power_kw": round(sum(total_power) / 8760, 2),
        }
    except Exception as e:
        print(f"Error parsing hourly: {e}")
        return None

# ============================================================================
# MAIN SIMULATION
# ============================================================================

def run_simulation(weather_station, construction_period, building_type):
    cached = get_cached_result(weather_station, construction_period, building_type)
    if cached:
        print(f"✓ Cache hit: {weather_station} / {construction_period} / {building_type}")
        return cached
    
    print(f"Running simulation: {weather_station} / {construction_period} / {building_type}")
    
    # Select IDF based on building type
    idf_lookup = ALL_IDF_FILES.get(building_type, ALL_IDF_FILES["single-family-house"])
    idf_filename = idf_lookup.get(construction_period)
    if not idf_filename:
        raise HTTPException(status_code=400, detail=f"Invalid construction period: {construction_period}")
    
    idf_path = IDF_DIR / idf_filename
    if not idf_path.exists():
        raise HTTPException(status_code=500, detail=f"IDF file not found: {idf_filename}")
    
    epw_path = download_epw(weather_station)
    if not epw_path:
        raise HTTPException(status_code=500, detail=f"Could not download weather file for: {weather_station}")
    
    ground_temps, lat, lon, elev = calculate_ground_temps_and_location(epw_path)
    
    idf_content = idf_path.read_text(encoding='utf-8', errors='ignore')
    modified_idf = modify_idf(idf_content, weather_station, lat, lon, elev, ground_temps)
    
    modified_idf_path = MODIFIED_IDF_DIR / f"{building_type}_{construction_period}_{weather_station}.idf"
    modified_idf_path.write_text(modified_idf)
    
    output_dir = OUTPUT_DIR / f"{building_type}_{construction_period}_{weather_station}"
    sim_result = run_energyplus(modified_idf_path, epw_path, output_dir)
    
    if not sim_result:
        raise HTTPException(status_code=500, detail="Simulation failed")
    
    sql_path = output_dir / "eplusout.sql"
    annual = parse_annual_results(sql_path)
    hourly = parse_hourly_results(sql_path)
    
    if not annual:
        raise HTTPException(status_code=500, detail="Could not parse simulation results")
    
    if hourly:
        annual["peak_power_kw"] = hourly["peak_power_kw"]
        annual["peak_heating_kw"] = hourly["peak_heating_kw"]
        annual["peak_cooling_kw"] = hourly["peak_cooling_kw"]
        annual["avg_power_kw"] = hourly["avg_power_kw"]
    
    hourly_data = {
        "heating_power_kw": hourly["heating_power_kw"] if hourly else [],
        "cooling_power_kw": hourly["cooling_power_kw"] if hourly else [],
        "total_power_kw": hourly["total_power_kw"] if hourly else []
    }
    
    save_to_cache(weather_station, construction_period, building_type, annual, hourly_data)
    print(f"✓ Saved to cache: {weather_station} / {construction_period}")
    
    return {"annual": annual, "hourly": hourly_data, "cached": False}

# ============================================================================
# FASTAPI
# ============================================================================

app = FastAPI(title="Energy Simulation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationRequest(BaseModel):
    weatherStation: str
    constructionPeriod: str
    buildingType: str = "single-family-house"

class CustomSimulationRequest(BaseModel):
    # Numeric bounds are deliberately wider than the frontend sliders; they only
    # reject physically meaningless input (negative, zero, NaN/inf, absurd values).
    weatherStation: str
    wallU: float = Field(..., ge=0.05, le=5.0)
    atticU: float = Field(..., ge=0.05, le=5.0)
    groundU: float = Field(..., ge=0.05, le=5.0)
    ach: float = Field(..., ge=0.0, le=5.0)
    windowType: Literal["single", "double", "triple"]
    wwr: int = Field(..., ge=1, le=90)
    ventilationType: str = "mvhr"   # nv | mev-bv | mvhr (legacy names accepted)
    heatedFloorArea: float = Field(125.0, gt=0, le=1_000_000)
    numberOfFloors: int = Field(2, ge=1, le=50)
    buildingType: str = "single-family-house"


def _require_choice(value, allowed, field):
    """Reject values outside a fixed set. These values end up in file paths,
    so anything not on the allow-list (e.g. '../') must never get through."""
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid {field}: {value!r}")

# Window U-values for each type
WINDOW_U_VALUES = {
    "single": 2.8,
    "double": 2.3,
    "triple": 1.8
}

# Base IDF templates for custom (real-time) simulation, per building type + ventilation type
CUSTOM_IDF_TEMPLATES = {
    "single-family-house": {
        "nv":     "sfh/SFH_before-1961.idf",
        "mev-bv": "sfh/SFH_1976-1985.idf",
        "mvhr":   "sfh/SFH_1986-1995.idf",
    },
    "mid-rise-apartment": {
        "nv":     "mfd/MFD_before-1961.idf",
        "mev-bv": "mfd/MFD_1976-1985.idf",
        "mvhr":   "mfd/MFD_1986-1995.idf",
    },
    "office": {
        "nv":     "office/Office_before-1961.idf",
        "mev-bv": "office/Office_1976-1985.idf",
        "mvhr":   "office/Office_1986-1995.idf",
    },
    "hotel": {
        "nv":     "hotel/Hotel_before-1961.idf",
        "mev-bv": "hotel/Hotel_1976-1985.idf",
        "mvhr":   "hotel/Hotel_1986-1995.idf",
    },
    "school": {
        "nv":     "school/School_before-1961.idf",
        "mev-bv": "school/School_1971-1980.idf",
        "mvhr":   "school/School_1981-1990.idf",
    },
    "hospital": {
        "nv":     "hospital/Hospital_before-1961.idf",
        "mev-bv": "hospital/Hospital_1971-1980.idf",
        "mvhr":   "hospital/Hospital_1981-1990.idf",
    },
    # Retail: single IDF for all ventilation types. Heat recovery is controlled
    # by eppy modifying ZoneHVAC:IdealLoadsAirSystem fields in generate_custom_idf_eppy.
    "retail": {
        "nv":     "retail/Retail_post2000.idf",
        "mev-bv": "retail/Retail_post2000.idf",
        "mvhr":   "retail/Retail_post2000.idf",
    },
    # Warehouse: same approach as retail.
    "warehouse": {
        "nv":     "warehouse/Warehouse_post2000.idf",
        "mev-bv": "warehouse/Warehouse_post2000.idf",
        "mvhr":   "warehouse/Warehouse_post2000.idf",
    },
}

# Legacy ventilation keys (used by the Sobol / factorial scripts and older
# requests) resolve to the same templates as the new NV / MEV/BV / MVHR keys.
for _templates in CUSTOM_IDF_TEMPLATES.values():
    _templates["self-propelled"]        = _templates["nv"]
    _templates["mechanical-exhaust"]    = _templates["mev-bv"]
    _templates["mechanical-exhaust-hr"] = _templates["mvhr"]

def _normalize_vent(value):
    """NV / MEV/BV / MVHR normalisation, shared with eppy_custom_simulation."""
    try:
        from eppy_custom_simulation import normalize_ventilation_type
        return normalize_ventilation_type(value)
    except ImportError:
        return value


def get_custom_cache_id(params):
    """Generate a unique cache ID for custom simulation parameters."""
    key = f"custom_{params.get('buildingType', 'single-family-house')}_{params['weatherStation']}_{params['wallU']}_{params['atticU']}_{params['groundU']}_{params['ach']}_{params['windowType']}_{params['wwr']}_{_normalize_vent(params.get('ventilationType', 'mvhr'))}_{params.get('heatedFloorArea', 125)}_{params.get('numberOfFloors', 2)}"
    return hashlib.md5(key.encode()).hexdigest()

def get_cached_custom_result(params):
    """Check cache for custom simulation result."""
    cache_id = get_custom_cache_id(params)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT annual_results, hourly_results FROM simulation_cache WHERE id = ?', (cache_id,))
        row = cursor.fetchone()
        if row:
            return {
                "annual": json.loads(row["annual_results"]),
                "hourly": json.loads(row["hourly_results"]),
                "cached": True
            }
    return None

def save_custom_to_cache(params, annual, hourly):
    """Save custom simulation result to cache."""
    cache_id = get_custom_cache_id(params)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO simulation_cache 
            (id, weather_station, construction_period, building_type, annual_results, hourly_results)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cache_id, params['weatherStation'], 'custom', 'custom', json.dumps(annual), json.dumps(hourly)))
        conn.commit()

def generate_custom_idf(base_idf_path, output_idf_path, station, lat, lon, elev,
                         ground_temps, wall_u, attic_u, ground_u, ach, window_type,
                         wwr, heated_floor_area=125.0, num_floors=2,
                         building_type="single-family-house",
                         ventilation_type="mvhr"):
    """
    Generate customized IDF with user parameters via eppy.
    Supports all 8 building types: SFH, MFD, Office, Hotel, School, Hospital, Retail, Warehouse.
    Raises RuntimeError if eppy is not available or fails.
    """
    from eppy_custom_simulation import generate_custom_idf_eppy, EPPY_AVAILABLE
    if not EPPY_AVAILABLE:
        raise RuntimeError("eppy is not installed. Install with: pip install eppy")
    return generate_custom_idf_eppy(
        base_idf_path=str(base_idf_path),
        output_idf_path=str(output_idf_path),
        station_name=station,
        latitude=lat,
        longitude=lon,
        elevation=elev,
        ground_temps=ground_temps,
        wall_u=wall_u,
        attic_u=attic_u,
        ground_u=ground_u,
        ach=ach,
        window_type=window_type,
        wwr=wwr,
        heated_floor_area=heated_floor_area,
        num_floors=num_floors,
        building_type=building_type,
        energyplus_path=ENERGYPLUS_PATH,
        ventilation_type=ventilation_type,
    )

def run_custom_simulation(params):
    """Run a custom simulation with user-specified parameters."""
    params_dict = params.dict() if hasattr(params, 'dict') else params
    
    # Check cache first
    cached = get_cached_custom_result(params_dict)
    if cached:
        print(f"✓ Cache hit for custom simulation: {params_dict['weatherStation']}")
        return cached
    
    print(f"Running custom simulation: {params_dict}")
    
    # Select base IDF template based on ventilation type and building type
    ventilation_type = _normalize_vent(params_dict.get('ventilationType', 'mvhr'))
    building_type = params_dict.get('buildingType', 'single-family-house')
    
    type_templates = CUSTOM_IDF_TEMPLATES.get(building_type, CUSTOM_IDF_TEMPLATES["single-family-house"])
    idf_template = type_templates.get(ventilation_type, type_templates["mvhr"])
    base_idf_path = IDF_DIR / idf_template
    
    print(f"  Ventilation type: {ventilation_type}")
    print(f"  Using IDF template: {idf_template}")
    
    if not base_idf_path.exists():
        raise HTTPException(status_code=500, detail=f"Base IDF template not found: {idf_template}")
    
    # Download weather file
    epw_path = download_epw(params_dict['weatherStation'])
    if not epw_path:
        raise HTTPException(status_code=500, detail=f"Could not download weather file for: {params_dict['weatherStation']}")
    
    # Get ground temps and location
    ground_temps, lat, lon, elev = calculate_ground_temps_and_location(epw_path)
    
    # Generate custom IDF path
    cache_id = get_custom_cache_id(params_dict)
    custom_idf_path = MODIFIED_IDF_DIR / f"custom_{cache_id}.idf"
    
    # Get geometry parameters
    heated_floor_area = params_dict.get('heatedFloorArea', 125.0)
    num_floors = params_dict.get('numberOfFloors', 2)
    
    # Generate custom IDF (uses eppy if available, else regex fallback)
    generate_custom_idf(
        base_idf_path,
        custom_idf_path,
        params_dict['weatherStation'],
        lat, lon, elev,
        ground_temps,
        params_dict['wallU'],
        params_dict['atticU'],
        params_dict['groundU'],
        params_dict['ach'],
        params_dict['windowType'],
        params_dict['wwr'],
        heated_floor_area,
        num_floors,
        building_type,
        ventilation_type,
    )
    
    # Run simulation
    output_dir = OUTPUT_DIR / f"custom_{cache_id}"
    sim_result = run_energyplus(custom_idf_path, epw_path, output_dir)
    
    if not sim_result:
        raise HTTPException(status_code=500, detail="Custom simulation failed")
    
    # Parse results
    sql_path = output_dir / "eplusout.sql"
    annual = parse_annual_results(sql_path)
    hourly = parse_hourly_results(sql_path)
    
    if not annual:
        raise HTTPException(status_code=500, detail="Could not parse custom simulation results")

    # ── Post-simulation area/floor scaling ────────────────────────────────────
    # For SFH: vertex scaling in eppy_custom_simulation.py handles geometry
    #           changes directly — no post-multiply needed.
    # For MFD, Office, Hotel: zone multipliers in eppy handle floor count.
    #           EnergyPlus simulates (num_floors × prototype_area_per_floor) m².
    #           Post-multiply corrects for any footprint area difference.
    # For School, Hospital, Retail, Warehouse: no geometry or multiplier changes
    #           in eppy. EnergyPlus always simulates the prototype area.
    #           Post-multiply scales all energy outputs to user-specified area.
    #
    # Prototype values (m²) sourced from COMMERCIAL_FLOOR_AREAS in
    # eppy_custom_simulation.py and MFD_FLOOR_AREA / MFD_NUM_FLOORS constants.
    # Area-per-floor = prototype_total_area / prototype_num_floors.

    PROTOTYPE_AREA_PER_FLOOR = {
        "mid-rise-apartment": 3135.0 / 4,   # 783.75 m²/floor (G + M×2 + T default)
        "office":             4982.0 / 3,   # 1660.67 m²/floor (3-floor prototype)
        "hotel":             11873.0 / 6,   # 1978.83 m²/floor (6-floor prototype)
    }
    PROTOTYPE_TOTAL_AREA = {
        "school":    6871.0,
        "hospital": 22422.0,
        "retail":    2294.0,
        "warehouse": 4598.0,
    }

    if building_type in PROTOTYPE_AREA_PER_FLOOR:
        # MFD, Office, Hotel — zone multiplier handles floor count.
        # EnergyPlus simulated area = num_floors × area_per_floor.
        simulated_area = num_floors * PROTOTYPE_AREA_PER_FLOOR[building_type]
        area_ratio = heated_floor_area / simulated_area if simulated_area > 0 else 1.0

    elif building_type in PROTOTYPE_TOTAL_AREA:
        # School, Hospital, Retail, Warehouse — no geometry changes in eppy.
        # EnergyPlus always simulates the prototype total area.
        simulated_area = PROTOTYPE_TOTAL_AREA[building_type]
        area_ratio = heated_floor_area / simulated_area if simulated_area > 0 else 1.0

    else:
        # SFH — vertex scaling handles everything; no post-multiply needed.
        area_ratio = 1.0
        simulated_area = heated_floor_area

    if abs(area_ratio - 1.0) > 0.001:
        print(f"  Post-simulation area scaling: {building_type}, "
              f"simulated={simulated_area:.1f} m², "
              f"user={heated_floor_area:.1f} m², "
              f"ratio={area_ratio:.4f}")
        for key in ("heating", "cooling", "dhw", "lighting", "equipment", "fans", "total"):
            if key in annual:
                annual[key] = round(annual[key] * area_ratio, 2)
        if hourly:
            # Scale hourly arrays element-wise for peak calculations
            hourly["heating_power_kw"] = [
                round(v * area_ratio, 4) for v in hourly["heating_power_kw"]]
            hourly["cooling_power_kw"] = [
                round(v * area_ratio, 4) for v in hourly["cooling_power_kw"]]
            hourly["total_power_kw"] = [
                round(v * area_ratio, 4) for v in hourly["total_power_kw"]]

    # Update floor_area in annual results to reflect user input
    annual["floor_area"] = heated_floor_area

    if hourly:
        annual["peak_power_kw"]    = hourly["peak_power_kw"]
        annual["peak_heating_kw"]  = max(hourly["heating_power_kw"]) if hourly["heating_power_kw"] else 0
        annual["peak_cooling_kw"]  = max(hourly["cooling_power_kw"]) if hourly["cooling_power_kw"] else 0
        annual["avg_power_kw"]     = hourly["avg_power_kw"]

    # Recalculate EUI based on user-specified floor area
    annual["eui"] = round(annual["total"] / heated_floor_area, 1) if heated_floor_area > 0 else 0
    
    hourly_data = {
        "heating_power_kw": hourly["heating_power_kw"] if hourly else [],
        "cooling_power_kw": hourly["cooling_power_kw"] if hourly else [],
        "total_power_kw": hourly["total_power_kw"] if hourly else []
    }
    
    # Add parameters to response
    annual["parameters"] = {
        "wall_u": params_dict['wallU'],
        "attic_u": params_dict['atticU'],
        "ground_u": params_dict['groundU'],
        "ach": params_dict['ach'],
        "window_type": params_dict['windowType'],
        "window_u": WINDOW_U_VALUES.get(params_dict['windowType'], 2.3),
        "wwr": params_dict['wwr'],
        "heated_floor_area": heated_floor_area,
        "num_floors": num_floors
    }
    
    # Save to cache
    save_custom_to_cache(params_dict, annual, hourly_data)
    print(f"✓ Custom simulation complete and cached")
    
    return {"annual": annual, "hourly": hourly_data, "cached": False}

@app.on_event("startup")
async def startup():
    init_database()
    if not Path(ENERGYPLUS_PATH).exists():
        print(f"\n⚠️  EnergyPlus not found at: {ENERGYPLUS_PATH}")

@app.get("/")
async def root():
    return {"status": "running", "energyplus": Path(ENERGYPLUS_PATH).exists(), "cache_db": CACHE_DB.exists()}

@app.post("/simulate")
async def simulate(request: SimulationRequest):
    _require_choice(request.weatherStation, STATION_FILENAMES, "weatherStation")
    _require_choice(request.buildingType, ALL_IDF_FILES, "buildingType")
    _require_choice(request.constructionPeriod, ALL_IDF_FILES[request.buildingType], "constructionPeriod")
    return run_simulation(request.weatherStation, request.constructionPeriod, request.buildingType)

@app.post("/simulate/custom")
async def simulate_custom(request: CustomSimulationRequest):
    """
    Run a custom simulation with user-specified parameters.
    
    Parameters:
    - weatherStation: Weather station ID (e.g., "stockholm", "lund")
    - wallU: Wall U-value (0.1 - 1.0 W/m²K)
    - atticU: Attic U-value (0.1 - 0.5 W/m²K)
    - groundU: Ground slab U-value (0.1 - 0.5 W/m²K)
    - ach: Air changes per hour (0 - 1.0)
    - windowType: Window type ("single", "double", "triple")
    - wwr: Window-to-wall ratio (15, 20, 30, 40)
    """
    _require_choice(request.weatherStation, STATION_FILENAMES, "weatherStation")
    _require_choice(request.buildingType, CUSTOM_IDF_TEMPLATES, "buildingType")
    try:
        vent_ok = _normalize_vent(request.ventilationType) in CUSTOM_IDF_TEMPLATES[request.buildingType]
    except ValueError:
        vent_ok = False
    if not vent_ok:
        raise HTTPException(status_code=400, detail=f"Invalid ventilationType: {request.ventilationType!r}")
    return run_custom_simulation(request)

@app.get("/cache/stats")
async def cache_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM simulation_cache')
        count = cursor.fetchone()[0]
        cursor.execute('SELECT weather_station, construction_period, building_type FROM simulation_cache')
        entries = [{"station": r[0], "period": r[1], "type": r[2]} for r in cursor.fetchall()]
    return {"total_cached": count, "entries": entries}

# Note: there is intentionally no endpoint for clearing the cache. To reset it,
# stop the server and delete simulation_cache.db.

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ENERGY SIMULATION API SERVER")
    print("="*60)
    print(f"\n  EnergyPlus: {ENERGYPLUS_PATH}")
    print(f"  IDF Dir: {IDF_DIR}")
    print(f"  Cache DB: {CACHE_DB}")
    print(f"\n  Starting server at http://localhost:8000")
    print("="*60 + "\n")
    # Bind to localhost only: the API has no authentication and must not be exposed publicly.
    uvicorn.run(app, host="127.0.0.1", port=8000)
