import json
import sqlite3
import hashlib
from contextlib import contextmanager

def init_database(cache_db):
    conn = sqlite3.connect(cache_db)
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
    print(f"✓ Database initialized: {cache_db}")

@contextmanager
def get_db(cache_db):
    conn = sqlite3.connect(cache_db)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_cache_id(weather_station, construction_period, building_type):
    key = f"{weather_station}_{construction_period}_{building_type}"
    return hashlib.md5(key.encode()).hexdigest()

def get_cached_result(cache_db, weather_station, construction_period, building_type):
    cache_id = get_cache_id(weather_station, construction_period, building_type)
    with get_db(cache_db) as conn:
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