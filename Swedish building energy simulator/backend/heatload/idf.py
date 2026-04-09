import re
from pathlib import Path
from eppy.modeleditor import IDF
import math

import paths


# Configure eppy with the IDD file — must be set before opening any IDF
IDF.setiddname(str(paths.ENERGYPLUS_IDD))

def get_idf_path(config, building_type, construction_period, idf_dir):
    all_idf_files = config["all_idf_files"]
    idf_lookup = all_idf_files.get(building_type, all_idf_files["single-family-house"])
    idf_filename = idf_lookup.get(construction_period)
    if not idf_filename:
        ValueError(f"IDF file not found: {idf_filename}")
    idf_path = idf_dir / idf_filename
    if not idf_path.exists():
        raise FileNotFoundError(f"IDF file not found: {idf_filename}")
    return idf_path

def read_idf_file(idf_path):
    return idf_path.read_text(encoding='utf-8', errors='ignore')

# def _read_idf_template(config, building_type, construction_period, idf_dir):
#     idf_path = _get_idf_path(config, building_type, construction_period, idf_dir)
#     return idf_path.read_text(encoding='utf-8', errors='ignore')

def modify_idf(idf_content, modified_idf_path, station_id, lat, lon, elev, ground_temps):
    # Set location
    content = idf_content
    location_pattern = r'(Site:Location,\s*)[^;]+'
    location_replacement = f'''Site:Location,
    {station_id},              !- Name
    {lat},                     !- Latitude
    {lon},                     !- Longitude
    1,                         !- Time Zone (CET)
    {elev}'''

    # Set ground temperature
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
    modified_idf_path.write_text(content)
    return content

def get_modified_idf_path(building_type: str, construction_period: str, weather_station: str, modified_idf_dir: Path):
    return modified_idf_dir / f"{building_type}_{construction_period}_{weather_station}.idf"

def calculate_ground_temps_and_location(epw_path): #NOTES: This function should be split into "get_ground_temps" and "get_location"
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
                    # print(f"✓ Using EPW ground temps at {best_depth}m depth")
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

def prepare_idf(
        config: dict,
        building_type: str,
        period: str,
        weather_station: str,
        epw_file: Path,
        idf_dir: Path,
        modified_idf_dir: Path,
        output_dir: Path,
) -> tuple[Path, Path, Path]:
    """
    Prepare a single modified IDF file for EnergyPlus simulation.

    Single-period counterpart to :func:`prepare_idfs`.

    Parameters
    ----------
    config : dict
        Project configuration mapping building types and construction periods
        to their base IDF filenames.
    building_type : str
        Identifier for the building archetype (e.g. ``"single-family-house"``).
    period : str
        Construction period label (e.g. ``"1961-1975"``).
    weather_station : str
        Identifier for the weather station, used in output naming and IDF
        location modification.
    epw_file : Path
        Path to the EnergyPlus EPW weather file. Ground temperatures and
        site coordinates are extracted from this file.
    idf_dir : Path
        Directory containing the original (unmodified) IDF files.
    modified_idf_dir : Path
        Directory where the modified IDF file will be written.
    output_dir : Path
        Directory under which the simulation output subdirectory will be created.

    Returns
    -------
    modified_idf_path : str
        Path to the modified IDF file.
    output_path : Path
        Path to the simulation output directory.
    sql_path : Path
        Path to the EnergyPlus SQL results file.
    """
    ground_temps, lat, lon, elev = calculate_ground_temps_and_location(epw_file)

    idf_file = get_idf_path(config, building_type, period, idf_dir)
    idf_content = read_idf_file(idf_file)

    modified_idf_path = get_modified_idf_path(building_type, period, weather_station, modified_idf_dir)
    modify_idf(idf_content, modified_idf_path, weather_station, lat, lon, elev, ground_temps)

    output_path = paths.set_output_path(building_type, period, weather_station, output_dir)
    sql_path = paths.set_sql_path(output_path)
    return modified_idf_path, output_path, sql_path

def prepare_idfs(
        config: dict, 
        building_type: str, 
        construction_periods: list[str], 
        weather_station: str,
        epw_file: Path, 
        idf_dir: Path, 
        modified_idf_dir: Path, 
        output_dir: Path,
        ) -> tuple[list[str], list[str], list[str]]:
    """
    Prepare a set of modified IDF files for parallel EnergyPlus simulation.

    Parameters
    ----------
    config : dict
        Project configuration mapping building types and construction periods
        to their base IDF filenames.
    building_type : str
        Identifier for the building archetype (e.g. ``"single-family-house"``).
    construction_periods : list[str]
        Ordered list of construction period labels to simulate
        (e.g. ``["before-1961","1961-1975", "1976-1985","1986-1995","1996-2005"]``).
    weather_station : str
        Identifier for the weather station, used in output naming and IDF
        location modification.
    epw_file : Path
        Path to the EnergyPlus EPW weather file. Ground temperatures and
        site coordinates are extracted from this file.
    idf_dir : Path
        Directory containing the original (unmodified) IDF files.
    modified_idf_dir : Path
        Directory containing the modified IDF files.
    output_dir : Path
        Directory under which simulation output subdirectories will be created.

    Returns
    -------
    modified_idfs : list[str]
        Paths to the modified IDF files, one per construction period.
    output_paths : list[str]
        Corresponding output directories, one per construction period.
    sql_paths : list[Path]
        Corresponding SQL result file paths, one per construction period.
    """

    modified_idfs, output_paths, sql_paths = [], [], []
    for period in construction_periods:
        modified_idf, output_path, sql_path = prepare_idf(
            config, building_type, period, weather_station, epw_file,
            idf_dir, modified_idf_dir, output_dir,
        )
        modified_idfs.append(modified_idf)
        output_paths.append(output_path)
        sql_paths.append(sql_path)
    return modified_idfs, output_paths, sql_paths
