import sqlite3
from pathlib import Path


def parse_results_single(sql_path: Path) -> dict:
    return {
        "annual": parse_annual_results(sql_path),
        "hourly": parse_hourly_results(sql_path),
    }


def parse_results_parallel(sql_paths: list[Path], periods: list[str]) -> dict:
    return {period: {
        "annual": parse_annual_results(sql_path),
        "hourly": parse_hourly_results(sql_path),
    } for period, sql_path in zip(periods, sql_paths)}


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