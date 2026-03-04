"""
Custom Simulation Module using EPPY
====================================
Properly modifies IDF files using the eppy library for reliable EnergyPlus manipulation.

SETUP:
    pip install eppy

This module provides functions to:
1. Modify material properties (U-values via thickness/conductivity)
2. Modify window properties (U-value, SHGC)
3. Modify infiltration rates (ACH)
4. Modify window geometry (WWR)
5. Update location and ground temperatures
"""

import os
import math
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Try to import eppy
try:
    from eppy import modeleditor
    from eppy.modeleditor import IDF
    EPPY_AVAILABLE = True
except ImportError:
    EPPY_AVAILABLE = False
    print("WARNING: eppy not installed. Install with: pip install eppy")


# ============================================================================
# CONFIGURATION
# ============================================================================

# Window U-values for each glazing type (W/m²K)
WINDOW_U_VALUES = {
    "single": 2.8,
    "double": 2.3,
    "triple": 1.8
}

# Window SHGC (Solar Heat Gain Coefficient) for each type
WINDOW_SHGC = {
    "single": 0.81,
    "double": 0.56,
    "triple": 0.40
}

# WWR options and target window areas (m²)
# Based on total wall area of 189.75 m²
WWR_WINDOW_AREAS = {
    15: 28.46,   # Current ~15%
    20: 37.95,
    30: 56.93,
    40: 75.90
}

# Building geometry constants
TOTAL_WALL_AREA = 189.75  # m²
FLOOR_AREA = 125.0  # m²
BUILDING_WIDTH = 7.8125  # m
BUILDING_DEPTH = 8.0  # m
FLOOR_HEIGHT = 3.0  # m

# Original material properties from IDF (based on new 1986-1995.idf)
# U-values are composite values including film resistances (from verified Excel)
# R_rest = R_total - R_insulation (accounts for other layers + film resistances)
ORIGINAL_VALUES = {
    "wall_u": 0.17,           # Composite U with films (Rsi=0.13, Rse=0.04)
    "wall_ins_thickness": 0.132595,
    "wall_ins_conductivity": 0.029427,
    "wall_R_rest": 1.376,     # 1/0.17 - 0.132595/0.029427
    "attic_u": 0.12,          # Composite U with films (Rsi=0.10, Rse=0.04)
    "attic_ins_thickness": 0.218872,
    "attic_ins_conductivity": 0.0480833,
    "attic_R_rest": 3.781,    # 1/0.12 - 0.218872/0.0480833
    "slab_u": 0.24,           # Composite U with films (Rsi=0.17, Rse=0.00)
    "slab_ins_thickness": 0.113987,
    "slab_ins_conductivity": 0.029427,
    "slab_R_rest": 0.293,     # 1/0.24 - 0.113987/0.029427
}

# MFD (Mid-Rise Apartment) material properties from MFD_1986-1995.idf
# Verified against Excel U-value comparison report
MFD_ORIGINAL_VALUES = {
    "wall_u": 0.2027,         # Composite U with films
    "wall_ins_name": "mineral wool board",
    "wall_ins_thickness": 0.17,
    "wall_ins_conductivity": 0.038,
    "wall_R_rest": 0.460,     # 1/0.2027 - 0.17/0.038
    "attic_u": 0.1499,        # Composite U with films
    "attic_ins_name": "mineral wool loose fill",
    "attic_ins_thickness": 0.258,
    "attic_ins_conductivity": 0.04,
    "attic_R_rest": 0.221,    # 1/0.1499 - 0.258/0.04
    "slab_u": 0.2425,         # Composite U with films
    "slab_ins_name": "xps insulation",
    "slab_ins_thickness": 0.12,
    "slab_ins_conductivity": 0.035,
    "slab_R_rest": 0.695,     # 1/0.2425 - 0.12/0.035
}

# Office/Hotel 1986-1995 base template material properties
# Wall: Concrete 70mm panel + Wall Mineral Wool_0.038 + Concrete + Gypsum board 13mm
# Roof: Asphalt felt + Roof Mineral Wool + Vapour barrier + Concrete roof slab
# Slab: Ground slab Concrete + EPS for ground slab + Cement Screed + Linoleum/Vinyl
OFFICE_HOTEL_ORIGINAL_VALUES = {
    "wall_u": 0.302,          # Composite U with films
    "wall_ins_thickness": 0.12,
    "wall_ins_conductivity": 0.04,
    "wall_R_rest": 0.311,     # 1/0.302 - 0.12/0.04
    "attic_u": 0.199,         # Composite U with films
    "attic_ins_thickness": 0.19,
    "attic_ins_conductivity": 0.04,
    "attic_R_rest": 0.272,    # 1/0.199 - 0.19/0.04
    "slab_u": 0.299,          # Composite U with films
    "slab_ins_thickness": 0.11,
    "slab_ins_conductivity": 0.036,
    "slab_R_rest": 0.290,     # 1/0.299 - 0.11/0.036
}

# School 1981-1990 base template material properties (SE_EDU_* naming)
# Uses same conductivity values as Office/Hotel, slightly different thicknesses
SCHOOL_ORIGINAL_VALUES = {
    "wall_u": 0.254,          # Composite U with films
    "wall_ins_thickness": 0.145,
    "wall_ins_conductivity": 0.04,
    "wall_R_rest": 0.311,
    "attic_u": 0.170,         # Composite U with films
    "attic_ins_thickness": 0.225,
    "attic_ins_conductivity": 0.04,
    "attic_R_rest": 0.272,
    "slab_u": 0.299,          # Composite U with films
    "slab_ins_thickness": 0.11,
    "slab_ins_conductivity": 0.036,
    "slab_R_rest": 0.290,
}

# Hospital 1981-1990 base template material properties (SE_HOS_* naming)
HOSPITAL_ORIGINAL_VALUES = {
    "wall_u": 0.264,          # Composite U with films
    "wall_ins_thickness": 0.135,
    "wall_ins_conductivity": 0.04,
    "wall_R_rest": 0.311,
    "attic_u": 0.170,         # Composite U with films
    "attic_ins_thickness": 0.225,
    "attic_ins_conductivity": 0.04,
    "attic_R_rest": 0.272,
    "slab_u": 0.299,          # Composite U with films
    "slab_ins_thickness": 0.11,
    "slab_ins_conductivity": 0.036,
    "slab_R_rest": 0.290,
}

# MFD building geometry constants
MFD_FLOOR_AREA = 3135.0  # m² E+ conditioned area (4 floors: G + M×2 + T, 783.7 m²/floor)
MFD_BUILDING_WIDTH = 46.33  # m
MFD_BUILDING_DEPTH = 7.62   # m
MFD_FLOOR_HEIGHT = 3.048    # m
MFD_NUM_FLOORS = 4          # Default: G(1) + M(×2 via Zone Multiplier) + T(1)

# Commercial building default floor areas (from IDF data)
COMMERCIAL_FLOOR_AREAS = {
    "office":   {"area": 4982.0,  "floors": 3},
    "hotel":    {"area": 11873.0, "floors": 6},
    "school":   {"area": 6871.0,  "floors": 2},
    "hospital": {"area": 22422.0, "floors": 5},
}


# ============================================================================
# EPPY IDF MODIFICATION FUNCTIONS
# ============================================================================

def set_idd_path(energyplus_path: str = None):
    """
    Set the IDD file path for eppy.
    Must be called before using IDF class.
    """
    if not EPPY_AVAILABLE:
        raise ImportError("eppy is not installed. Install with: pip install eppy")
    
    # Try to find IDD file
    idd_paths = [
        # Windows paths
        r"C:\EnergyPlusV25-2-0\Energy+.idd",
        r"C:\EnergyPlusV24-2-0\Energy+.idd",
        r"C:\EnergyPlusV23-2-0\Energy+.idd",
        # Linux paths
        "/usr/local/EnergyPlus-25-2-0/Energy+.idd",
        "/usr/local/EnergyPlus-24-2-0/Energy+.idd",
        # Mac paths
        "/Applications/EnergyPlus-25-2-0/Energy+.idd",
    ]
    
    if energyplus_path:
        # Extract directory from exe path
        ep_dir = Path(energyplus_path).parent
        idd_paths.insert(0, str(ep_dir / "Energy+.idd"))
    
    for idd_path in idd_paths:
        if os.path.exists(idd_path):
            IDF.setiddname(idd_path)
            print(f"✓ IDD file set: {idd_path}")
            return True
    
    raise FileNotFoundError(f"Could not find Energy+.idd file. Searched: {idd_paths}")


def load_idf(idf_path: str) -> IDF:
    """Load an IDF file."""
    return IDF(idf_path)


def save_idf(idf: IDF, output_path: str):
    """Save the modified IDF to a file."""
    idf.saveas(output_path)


# ============================================================================
# LOCATION AND CLIMATE
# ============================================================================

def update_location(idf: IDF, name: str, latitude: float, longitude: float, 
                    timezone: float = 1.0, elevation: float = 100.0):
    """Update the Site:Location object."""
    locations = idf.idfobjects['SITE:LOCATION']
    if locations:
        loc = locations[0]
        loc.Name = name
        loc.Latitude = latitude
        loc.Longitude = longitude
        loc.Time_Zone = timezone
        loc.Elevation = elevation
    else:
        # Create new location object
        idf.newidfobject('SITE:LOCATION',
                         Name=name,
                         Latitude=latitude,
                         Longitude=longitude,
                         Time_Zone=timezone,
                         Elevation=elevation)


def update_ground_temperatures(idf: IDF, monthly_temps: List[float]):
    """
    Update Site:GroundTemperature:BuildingSurface with 12 monthly values.
    
    Args:
        monthly_temps: List of 12 monthly ground temperatures in °C
    """
    if len(monthly_temps) != 12:
        raise ValueError("monthly_temps must have exactly 12 values")
    
    gt_objects = idf.idfobjects['SITE:GROUNDTEMPERATURE:BUILDINGSURFACE']
    if gt_objects:
        gt = gt_objects[0]
        gt.January_Ground_Temperature = monthly_temps[0]
        gt.February_Ground_Temperature = monthly_temps[1]
        gt.March_Ground_Temperature = monthly_temps[2]
        gt.April_Ground_Temperature = monthly_temps[3]
        gt.May_Ground_Temperature = monthly_temps[4]
        gt.June_Ground_Temperature = monthly_temps[5]
        gt.July_Ground_Temperature = monthly_temps[6]
        gt.August_Ground_Temperature = monthly_temps[7]
        gt.September_Ground_Temperature = monthly_temps[8]
        gt.October_Ground_Temperature = monthly_temps[9]
        gt.November_Ground_Temperature = monthly_temps[10]
        gt.December_Ground_Temperature = monthly_temps[11]


# ============================================================================
# MATERIAL PROPERTIES (U-VALUES)
# ============================================================================

def calculate_insulation_thickness(target_u: float, original_u: float, 
                                   original_thickness: float,
                                   conductivity: float = None,
                                   R_rest: float = None) -> float:
    """
    Calculate new insulation thickness to achieve target U-value.
    
    Uses R-value decomposition for composite constructions:
    R_total = R_rest + R_insulation
    R_insulation_new = (1/target_u) - R_rest
    new_thickness = R_insulation_new * conductivity
    
    Args:
        target_u: Target U-value (W/m²K)
        original_u: Original composite U-value (W/m²K)
        original_thickness: Original insulation thickness (m)
        conductivity: Insulation conductivity (W/mK)
        R_rest: Thermal resistance of non-insulation layers + film resistances
    
    Returns:
        New insulation thickness (m)
    """
    if R_rest is not None and conductivity is not None:
        # Correct method: decompose composite R-value
        target_R_total = 1.0 / target_u
        new_R_ins = target_R_total - R_rest
        new_thickness = max(0.01, new_R_ins * conductivity)
    else:
        # Fallback: simple proportional scaling
        scale_factor = original_u / target_u
        new_thickness = original_thickness * scale_factor
    
    # Clamp to reasonable bounds
    return max(0.01, min(2.0, new_thickness))


def update_wall_u_value(idf: IDF, target_u: float, building_type: str = "single-family-house"):
    """
    Update wall insulation to achieve target U-value.
    SFH: 'wall rigid ins'. MFD: 'Mineral wool board'.
    Office/Hotel: 'Wall Mineral Wool'. School: 'SE_EDU_*_MineralWool_Wall'.
    Hospital: 'SE_HOS_*_MineralWool_Wall'.
    """
    materials = idf.idfobjects['MATERIAL']

    if building_type == "mid-rise-apartment":
        vals = MFD_ORIGINAL_VALUES
        search_names = ['mineral wool board']
    elif building_type in ("office", "hotel"):
        vals = OFFICE_HOTEL_ORIGINAL_VALUES
        search_names = ['wall mineral wool']
    elif building_type == "school":
        vals = SCHOOL_ORIGINAL_VALUES
        search_names = ['mineralwool_wall', 'mineralwool wall']
    elif building_type == "hospital":
        vals = HOSPITAL_ORIGINAL_VALUES
        search_names = ['mineralwool_wall', 'mineralwool wall']
    else:
        vals = ORIGINAL_VALUES
        search_names = ['wall rigid ins', 'wall_rigid_ins']

    for mat in materials:
        mat_lower = mat.Name.lower()
        if any(name in mat_lower for name in search_names):
            new_thickness = calculate_insulation_thickness(
                target_u,
                vals['wall_u'],
                vals['wall_ins_thickness'],
                conductivity=vals['wall_ins_conductivity'],
                R_rest=vals['wall_R_rest']
            )
            mat.Thickness = new_thickness
            print(f"  Wall insulation ({mat.Name}): {vals['wall_ins_thickness']:.4f} → {new_thickness:.4f} m")
            print(f"  Target wall U-value: {target_u} W/m²K")
            return

    print(f"  WARNING: Could not find wall insulation material for {building_type}")


def update_attic_u_value(idf: IDF, target_u: float, building_type: str = "single-family-house"):
    """
    Update attic/ceiling insulation to achieve target U-value.
    SFH: 'ceiling loosefill ins'. MFD: 'Mineral wool loose fill'.
    Office/Hotel: 'Roof Mineral Wool'. School: 'SE_EDU_*_MineralWool_Roof'.
    Hospital: 'SE_HOS_*_MineralWool_Roof'.
    """
    materials = idf.idfobjects['MATERIAL']

    if building_type == "mid-rise-apartment":
        vals = MFD_ORIGINAL_VALUES
        search_names = ['mineral wool loose fill']
    elif building_type in ("office", "hotel"):
        vals = OFFICE_HOTEL_ORIGINAL_VALUES
        search_names = ['roof mineral wool']
    elif building_type == "school":
        vals = SCHOOL_ORIGINAL_VALUES
        search_names = ['mineralwool_roof', 'mineralwool roof']
    elif building_type == "hospital":
        vals = HOSPITAL_ORIGINAL_VALUES
        search_names = ['mineralwool_roof', 'mineralwool roof']
    else:
        vals = ORIGINAL_VALUES
        search_names = ['ceiling loosefill', 'attic']

    for mat in materials:
        mat_lower = mat.Name.lower()
        if any(name in mat_lower for name in search_names):
            new_thickness = calculate_insulation_thickness(
                target_u,
                vals['attic_u'],
                vals['attic_ins_thickness'],
                conductivity=vals['attic_ins_conductivity'],
                R_rest=vals['attic_R_rest']
            )
            mat.Thickness = new_thickness
            print(f"  Attic insulation ({mat.Name}): {vals['attic_ins_thickness']:.4f} → {new_thickness:.4f} m")
            print(f"  Target attic U-value: {target_u} W/m²K")
            return

    print(f"  WARNING: Could not find attic insulation material for {building_type}")


def update_ground_slab_u_value(idf: IDF, target_u: float, building_type: str = "single-family-house"):
    """
    Update ground slab insulation to achieve target U-value.
    SFH: 'slab rigid ins'. MFD: 'XPS Insulation'.
    Office/Hotel: 'EPS for ground slab'. School: 'SE_EDU_*_Floor_EPS_for_ground_slab'.
    Hospital: 'SE_HOS_*_EPS'.
    """
    materials = idf.idfobjects['MATERIAL']

    if building_type == "mid-rise-apartment":
        vals = MFD_ORIGINAL_VALUES
        search_names = ['xps insulation']
    elif building_type in ("office", "hotel"):
        vals = OFFICE_HOTEL_ORIGINAL_VALUES
        search_names = ['eps for ground slab', 'eps_for_ground_slab']
    elif building_type == "school":
        vals = SCHOOL_ORIGINAL_VALUES
        search_names = ['_eps_for_ground', 'eps_for_ground', 'floor_eps']
    elif building_type == "hospital":
        vals = HOSPITAL_ORIGINAL_VALUES
        search_names = ['_eps', 'eps insulation']
    else:
        vals = ORIGINAL_VALUES
        search_names = ['slab rigid ins', 'floor rigid ins']

    for mat in materials:
        mat_lower = mat.Name.lower()
        if any(name in mat_lower for name in search_names):
            new_thickness = calculate_insulation_thickness(
                target_u,
                vals['slab_u'],
                vals['slab_ins_thickness'],
                conductivity=vals['slab_ins_conductivity'],
                R_rest=vals['slab_R_rest']
            )
            mat.Thickness = new_thickness
            print(f"  Slab insulation ({mat.Name}): {vals['slab_ins_thickness']:.4f} → {new_thickness:.4f} m")
            print(f"  Target slab U-value: {target_u} W/m²K")
            return

    print(f"  WARNING: Could not find slab insulation material for {building_type}")


# ============================================================================
# WINDOW PROPERTIES
# ============================================================================

def update_window_properties(idf: IDF, window_type: str):
    """
    Update window glazing properties (U-value and SHGC).
    Modifies WindowMaterial:SimpleGlazingSystem objects.
    
    Args:
        window_type: "single", "double", or "triple"
    """
    u_value = WINDOW_U_VALUES.get(window_type, 2.3)
    shgc = WINDOW_SHGC.get(window_type, 0.56)
    
    # Find and update SimpleGlazingSystem materials
    glazing_materials = idf.idfobjects['WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM']
    
    for mat in glazing_materials:
        mat.UFactor = u_value
        mat.Solar_Heat_Gain_Coefficient = shgc
        print(f"  Window U-value: {u_value} W/m²K, SHGC: {shgc}")
        return
    
    print("  WARNING: Could not find window glazing material")


# ============================================================================
# INFILTRATION (ACH)
# ============================================================================

def update_infiltration_ach(idf: IDF, ach: float):
    """
    Update air infiltration rate for all zones.
    Modifies ZoneInfiltration:DesignFlowRate objects.
    
    Args:
        ach: Air changes per hour
    """
    infiltration_objects = idf.idfobjects['ZONEINFILTRATION:DESIGNFLOWRATE']
    
    count = 0
    for inf in infiltration_objects:
        # Check if it uses ACH method
        if inf.Design_Flow_Rate_Calculation_Method == 'AirChanges/Hour':
            inf.Air_Changes_per_Hour = ach
            count += 1
    
    print(f"  Updated ACH to {ach} for {count} zone(s)")


# ============================================================================
# WINDOW-TO-WALL RATIO (WWR)
# ============================================================================

def calculate_window_scale_factor(target_wwr: int) -> float:
    """
    Calculate the scale factor for window dimensions to achieve target WWR.
    
    Current WWR is ~15% (28 m² windows / 189.75 m² walls)
    """
    current_wwr = 15
    target_area = WWR_WINDOW_AREAS.get(target_wwr, 28.46)
    current_area = WWR_WINDOW_AREAS[15]
    
    # Scale factor for linear dimensions (sqrt because area = length × height)
    # Actually, we'll scale height only to keep windows centered
    return target_area / current_area


def update_window_wwr(idf: IDF, target_wwr: int):
    """
    Update window sizes to achieve target window-to-wall ratio.
    
    This modifies the FenestrationSurface:Detailed objects by scaling
    window dimensions proportionally.
    
    Args:
        target_wwr: Target WWR percentage (15, 20, 30, or 40)
    """
    if target_wwr == 15:
        print(f"  WWR unchanged at 15%")
        return
    
    scale_factor = calculate_window_scale_factor(target_wwr)
    
    # Get all fenestration surfaces
    windows = idf.idfobjects['FENESTRATIONSURFACE:DETAILED']
    
    for window in windows:
        if window.Surface_Type.lower() == 'window':
            # Get the number of vertices
            num_vertices = int(window.Number_of_Vertices)
            
            # For each window, we scale the height (Z coordinates)
            # while keeping the bottom edge fixed
            # This maintains window position but changes size
            
            # Find min Z (bottom of window)
            z_coords = []
            for i in range(num_vertices):
                z_field = f'Vertex_{i+1}_Zcoordinate'
                if hasattr(window, z_field):
                    z_coords.append(getattr(window, z_field))
            
            if z_coords:
                min_z = min(z_coords)
                
                # Scale Z coordinates relative to bottom edge
                for i in range(num_vertices):
                    z_field = f'Vertex_{i+1}_Zcoordinate'
                    if hasattr(window, z_field):
                        old_z = getattr(window, z_field)
                        # Scale the height above the bottom edge
                        height_above_bottom = old_z - min_z
                        new_height = height_above_bottom * math.sqrt(scale_factor)
                        new_z = min_z + new_height
                        setattr(window, z_field, new_z)
    
    print(f"  WWR scaled from 15% to {target_wwr}% (scale factor: {scale_factor:.2f})")


def update_window_wwr_multiplier(idf: IDF, target_wwr: int, building_type: str = "single-family-house"):
    """
    Update WWR using multiplier (>= base) or vertex Z-scaling (< base).
    EnergyPlus requires window Multiplier >= 1.0, so when target < base
    we shrink windows by scaling their height via vertex coordinates.
    """
    BASE_WWR_BY_TYPE = {
        "single-family-house": 15.0,
        "mid-rise-apartment":  20.0,
        "office":              34.0,
        "hotel":               27.0,
        "school":              38.0,
        "hospital":            14.0,
    }
    base_wwr = BASE_WWR_BY_TYPE.get(building_type, 15.0)

    if target_wwr == base_wwr:
        print(f"  WWR unchanged at {base_wwr:.0f}%")
        return

    ratio = target_wwr / base_wwr  # e.g. 30/34 = 0.88 or 40/34 = 1.18
    windows = idf.idfobjects['FENESTRATIONSURFACE:DETAILED']

    if ratio >= 1.0:
        # Scale UP: use multiplier (always valid when >= 1)
        for window in windows:
            if window.Surface_Type.lower() == 'window':
                window.Multiplier = ratio
        print(f"  WWR scaled UP via multiplier {ratio:.3f} ({base_wwr:.0f}% → {target_wwr}%)")
    else:
        # Scale DOWN: shrink window vertices (multiplier < 1 is invalid in E+)
        # Scale both height and width by sqrt(ratio) to preserve aspect ratio
        height_scale = math.sqrt(ratio)
        width_scale = math.sqrt(ratio)
        for window in windows:
            if window.Surface_Type.lower() != 'window':
                continue
            num_verts = int(window.Number_of_Vertices)
            # Collect current X, Y, Z per vertex
            xs = [float(getattr(window, f'Vertex_{i+1}_Xcoordinate', 0)) for i in range(num_verts)]
            ys = [float(getattr(window, f'Vertex_{i+1}_Ycoordinate', 0)) for i in range(num_verts)]
            zs = [float(getattr(window, f'Vertex_{i+1}_Zcoordinate', 0)) for i in range(num_verts)]
            # Centroid
            cx = sum(xs) / num_verts
            cy = sum(ys) / num_verts
            cz = sum(zs) / num_verts
            # Scale each vertex toward centroid
            for i in range(num_verts):
                setattr(window, f'Vertex_{i+1}_Xcoordinate', cx + (xs[i] - cx) * width_scale)
                setattr(window, f'Vertex_{i+1}_Ycoordinate', cy + (ys[i] - cy) * width_scale)
                setattr(window, f'Vertex_{i+1}_Zcoordinate', cz + (zs[i] - cz) * height_scale)
        print(f"  WWR scaled DOWN via vertex shrink {ratio:.3f} ({base_wwr:.0f}% → {target_wwr}%)")


# ============================================================================
# OUTPUT VARIABLES
# ============================================================================

def add_hourly_output_variables(idf: IDF):
    """Add hourly output variables for heating and cooling power."""
    
    # Check if variables already exist
    existing_vars = idf.idfobjects['OUTPUT:VARIABLE']
    existing_names = [v.Variable_Name for v in existing_vars if hasattr(v, 'Variable_Name')]
    
    variables_to_add = [
        ('*', 'Zone Ideal Loads Supply Air Total Heating Rate', 'Hourly'),
        ('*', 'Zone Ideal Loads Supply Air Total Cooling Rate', 'Hourly'),
        ('*', 'Facility Total Electric Demand Power', 'Hourly'),
    ]
    
    for key, var_name, freq in variables_to_add:
        if var_name not in existing_names:
            idf.newidfobject('OUTPUT:VARIABLE',
                            Key_Value=key,
                            Variable_Name=var_name,
                            Reporting_Frequency=freq)
    
    # Add output meters
    existing_meters = idf.idfobjects['OUTPUT:METER']
    existing_meter_names = [m.Key_Name for m in existing_meters if hasattr(m, 'Key_Name')]
    
    meters_to_add = [
        ('Heating:EnergyTransfer', 'Hourly'),
        ('Cooling:EnergyTransfer', 'Hourly'),
    ]
    
    for meter_name, freq in meters_to_add:
        if meter_name not in existing_meter_names:
            idf.newidfobject('OUTPUT:METER',
                            Key_Name=meter_name,
                            Reporting_Frequency=freq)
    
    print("  Added hourly output variables")


# ============================================================================
# BUILDING GEOMETRY SCALING
# ============================================================================

def scale_building_geometry(idf: IDF, heated_floor_area: float, num_floors: int, building_type: str = "single-family-house"):
    """
    Scale building geometry to match user-specified heated floor area and number of floors.
    
    SFH base: 2 heated floors (Living Space + First Floor), each ~62.5 m² = 125 m² total
    MFD base: 3 floors (G/M/T), each ~784 m² = 2351 m² total
    
    For MFD, geometry scaling is disabled (complex multi-zone layout). Only internal loads scale.
    
    Args:
        idf: The IDF object to modify
        heated_floor_area: Total heated floor area in m²
        num_floors: Number of heated floors (1, 2, or 3)
        building_type: "single-family-house" or "mid-rise-apartment"
    """
    is_mfd = building_type == "mid-rise-apartment"
    is_commercial = building_type in ("office", "hotel", "school", "hospital")

    if is_mfd or is_commercial:
        # MFD/Commercial: complex multi-zone geometry, skip vertex scaling
        # Commercial IDFs use density-based specs (W/m², people/m²) that auto-scale
        # MFD uses absolute counts but we scale safely only for People method
        if is_commercial:
            defaults = COMMERCIAL_FLOOR_AREAS[building_type]
            original_floor_area = defaults["area"]
        else:
            original_floor_area = MFD_FLOOR_AREA
        total_area_ratio = heated_floor_area / original_floor_area
        
        print(f"  {building_type}: skipping geometry vertex scaling (complex multi-zone)")
        print(f"  Area ratio for load scaling: {total_area_ratio:.3f}")
        
        if is_mfd:
            # MFD: safely scale absolute-count People objects only
            people_objects = idf.idfobjects['PEOPLE']
            for person_obj in people_objects:
                method = getattr(person_obj, 'Number_of_People_Calculation_Method', '')
                if str(method).lower() == 'people':
                    try:
                        old_val = float(person_obj.Number_of_People)
                        person_obj.Number_of_People = old_val * total_area_ratio
                    except (ValueError, TypeError):
                        pass
        # Commercial: skip load scaling — density fields auto-scale with EUI calc
        
        print(f"  Load scaling complete")
        return
    
    # SFH geometry scaling (original logic)
    original_floor_area = 125.0  # m² (2 floors x 62.5 m²)
    original_floors = 2
    original_floor_area_per_floor = 62.5  # m²
    original_width = 7.8125  # m
    original_depth = 8.0  # m
    floor_height = 3.0  # m
    
    # Calculate new values
    new_floor_area_per_floor = heated_floor_area / num_floors
    
    # Scale factor for floor dimensions (square root because area = width x depth)
    # We keep the aspect ratio the same
    area_scale = new_floor_area_per_floor / original_floor_area_per_floor
    linear_scale = math.sqrt(area_scale)
    
    new_width = original_width * linear_scale
    new_depth = original_depth * linear_scale
    
    print(f"  Original: {original_floor_area} m² ({original_floors} floors, {original_floor_area_per_floor} m²/floor)")
    print(f"  New: {heated_floor_area} m² ({num_floors} floors, {new_floor_area_per_floor:.1f} m²/floor)")
    print(f"  Linear scale factor: {linear_scale:.3f}")
    print(f"  New dimensions: {new_width:.2f}m x {new_depth:.2f}m")
    
    # Get all building surfaces
    surfaces = idf.idfobjects['BUILDINGSURFACE:DETAILED']
    fenestrations = idf.idfobjects['FENESTRATIONSURFACE:DETAILED']
    
    # Define which zones exist in the base IDF
    # Base IDF has: "Living Space" (ground floor), "First Floor", "Attic"
    base_zones = {
        "living space": 0,  # Ground floor, Z = 0 to 3
        "first floor": 1,   # First floor, Z = 3 to 6
        "attic": 2,         # Attic, Z = 6+
    }
    
    # Scale all surface vertices
    for surface in surfaces:
        num_vertices = int(surface.Number_of_Vertices)
        zone_name = surface.Zone_Name.lower() if hasattr(surface, 'Zone_Name') else ""
        
        for i in range(num_vertices):
            x_field = f'Vertex_{i+1}_Xcoordinate'
            y_field = f'Vertex_{i+1}_Ycoordinate'
            z_field = f'Vertex_{i+1}_Zcoordinate'
            
            if hasattr(surface, x_field) and hasattr(surface, y_field):
                old_x = getattr(surface, x_field)
                old_y = getattr(surface, y_field)
                old_z = getattr(surface, z_field) if hasattr(surface, z_field) else 0
                
                # Scale X and Y coordinates
                new_x = old_x * linear_scale
                new_y = old_y * linear_scale
                
                # For Z coordinates, handle floor addition/removal
                # Keep Z as-is for now (floor heights don't change)
                new_z = old_z
                
                setattr(surface, x_field, new_x)
                setattr(surface, y_field, new_y)
                setattr(surface, z_field, new_z)
    
    # Scale fenestration (window) vertices
    for window in fenestrations:
        num_vertices = int(window.Number_of_Vertices)
        
        for i in range(num_vertices):
            x_field = f'Vertex_{i+1}_Xcoordinate'
            y_field = f'Vertex_{i+1}_Ycoordinate'
            z_field = f'Vertex_{i+1}_Zcoordinate'
            
            if hasattr(window, x_field) and hasattr(window, y_field):
                old_x = getattr(window, x_field)
                old_y = getattr(window, y_field)
                
                new_x = old_x * linear_scale
                new_y = old_y * linear_scale
                
                setattr(window, x_field, new_x)
                setattr(window, y_field, new_y)
    
    # Update zone floor areas if present
    zones = idf.idfobjects['ZONE']
    for zone in zones:
        zone_name = zone.Name.lower()
        if 'attic' not in zone_name:
            # Update floor area for heated zones
            if hasattr(zone, 'Floor_Area'):
                zone.Floor_Area = new_floor_area_per_floor
    
    # Handle number of floors by adjusting zone multipliers or enabling/disabling zones
    # For simplicity, we use a multiplier approach on internal loads
    # The actual zone geometry stays as 2 floors, but loads scale
    
    floor_ratio = num_floors / original_floors
    print(f"  Floor ratio (for load scaling): {floor_ratio:.2f}")
    
    # Scale internal loads (People, Lights, Equipment) based on total area
    total_area_ratio = heated_floor_area / original_floor_area
    
    # Scale People
    people_objects = idf.idfobjects['PEOPLE']
    for people in people_objects:
        if hasattr(people, 'Number_of_People'):
            old_val = people.Number_of_People
            people.Number_of_People = old_val * total_area_ratio
    
    # Scale Lights
    lights_objects = idf.idfobjects['LIGHTS']
    for light in lights_objects:
        if hasattr(light, 'Lighting_Level'):
            old_val = light.Lighting_Level
            light.Lighting_Level = old_val * total_area_ratio
    
    # Scale Electric Equipment
    equip_objects = idf.idfobjects['ELECTRICEQUIPMENT']
    for equip in equip_objects:
        if hasattr(equip, 'Design_Level'):
            old_val = equip.Design_Level
            equip.Design_Level = old_val * total_area_ratio
    
    print(f"  Scaled internal loads by factor: {total_area_ratio:.2f}")
    
    return new_floor_area_per_floor * num_floors  # Return actual heated area


# ============================================================================
# MAIN FUNCTION: GENERATE CUSTOM IDF
# ============================================================================

def generate_custom_idf_eppy(
    base_idf_path: str,
    output_idf_path: str,
    station_name: str,
    latitude: float,
    longitude: float,
    elevation: float,
    ground_temps: List[float],
    wall_u: float,
    attic_u: float,
    ground_u: float,
    ach: float,
    window_type: str,
    wwr: int,
    heated_floor_area: float = 125.0,
    num_floors: int = 2,
    building_type: str = "single-family-house",
    energyplus_path: str = None
) -> str:
    """
    Generate a customized IDF file with user-specified parameters using eppy.
    
    Args:
        base_idf_path: Path to the base IDF template
        output_idf_path: Path to save the modified IDF
        station_name: Weather station name
        latitude: Site latitude
        longitude: Site longitude
        elevation: Site elevation (m)
        ground_temps: List of 12 monthly ground temperatures
        wall_u: Target wall U-value (W/m²K)
        attic_u: Target attic U-value (W/m²K)
        ground_u: Target ground slab U-value (W/m²K)
        ach: Air changes per hour
        window_type: "single", "double", or "triple"
        wwr: Window-to-wall ratio (15, 20, 30, or 40)
        heated_floor_area: Total heated floor area in m²
        num_floors: Number of heated floors (1, 2, or 3)
        energyplus_path: Path to EnergyPlus executable (for finding IDD)
    
    Returns:
        Path to the generated IDF file
    """
    if not EPPY_AVAILABLE:
        raise ImportError("eppy is not installed. Install with: pip install eppy")
    
    print(f"\n{'='*60}")
    print("GENERATING CUSTOM IDF WITH EPPY")
    print(f"{'='*60}")
    
    # Set IDD path (required for eppy)
    set_idd_path(energyplus_path)
    
    # Load the base IDF
    print(f"\nLoading base IDF: {base_idf_path}")
    idf = load_idf(base_idf_path)
    
    # Update location
    print(f"\nUpdating location: {station_name} ({latitude}, {longitude})")
    update_location(idf, station_name, latitude, longitude, 1.0, elevation)
    
    # Update ground temperatures
    print(f"Updating ground temperatures...")
    update_ground_temperatures(idf, ground_temps)
    
    # Scale building geometry if different from default
    if building_type == "mid-rise-apartment":
        default_area = MFD_FLOOR_AREA
        default_floors = MFD_NUM_FLOORS
    elif building_type in COMMERCIAL_FLOOR_AREAS:
        default_area = COMMERCIAL_FLOOR_AREAS[building_type]["area"]
        default_floors = COMMERCIAL_FLOOR_AREAS[building_type]["floors"]
    else:
        default_area = 125.0
        default_floors = 2
    if heated_floor_area != default_area or num_floors != default_floors:
        print(f"\nScaling building geometry:")
        scale_building_geometry(idf, heated_floor_area, num_floors, building_type)
    
    # Update U-values
    print(f"\nUpdating thermal properties ({building_type}):")
    update_wall_u_value(idf, wall_u, building_type)
    update_attic_u_value(idf, attic_u, building_type)
    update_ground_slab_u_value(idf, ground_u, building_type)
    
    # Update window properties
    print(f"\nUpdating window properties:")
    update_window_properties(idf, window_type)
    
    # Update infiltration
    print(f"\nUpdating infiltration:")
    update_infiltration_ach(idf, ach)
    
    # Update WWR (using multiplier method for simplicity)
    print(f"\nUpdating WWR:")
    update_window_wwr_multiplier(idf, wwr, building_type)
    
    # Update floor count for MFD via Zone Multiplier on M zones
    # Use Zone Multiplier (NOT ZoneGroup) so E+ correctly scales conditioned floor area
    # Zone Multiplier affects BOTH energy AND floor area in E+ output
    if building_type == "mid-rise-apartment":
        m_zone_mult = max(1, num_floors - 2)  # 3→1, 4→2, 5→3
        zones = idf.idfobjects['ZONE']
        for zone in zones:
            if zone.Name.startswith('M '):
                old_mult = zone.Multiplier if hasattr(zone, 'Multiplier') else 1
                zone.Multiplier = m_zone_mult
                print(f"\n  Zone '{zone.Name}': multiplier {old_mult} → {m_zone_mult}")
        # Neutralize ZoneGroup multiplier to 1
        zone_groups = idf.idfobjects['ZONEGROUP']
        for zg in zone_groups:
            if hasattr(zg, 'Zone_List_Multiplier'):
                zg.Zone_List_Multiplier = 1
                print(f"  ZoneGroup '{zg.Name}': multiplier → 1 (neutralized)")
        print(f"  MFD floor config: G(1) + M(×{m_zone_mult}) + T(1) = {num_floors} floors")
    
    # Add output variables
    print(f"\nAdding output variables:")
    add_hourly_output_variables(idf)
    
    # Save the modified IDF
    print(f"\nSaving modified IDF: {output_idf_path}")
    save_idf(idf, output_idf_path)
    
    print(f"\n{'='*60}")
    print("CUSTOM IDF GENERATION COMPLETE")
    print(f"{'='*60}\n")
    
    return output_idf_path


# ============================================================================
# TEST FUNCTION
# ============================================================================

if __name__ == "__main__":
    # Test the module
    print("Testing eppy-based IDF modification...")
    
    # Example usage
    base_idf = "idf_files/1986-1995.idf"
    output_idf = "modified_idf/test_custom.idf"
    
    if os.path.exists(base_idf):
        try:
            generate_custom_idf_eppy(
                base_idf_path=base_idf,
                output_idf_path=output_idf,
                station_name="Stockholm",
                latitude=59.33,
                longitude=18.07,
                elevation=44,
                ground_temps=[5, 3, 2, 3, 6, 10, 14, 16, 15, 12, 9, 7],
                wall_u=0.25,
                attic_u=0.15,
                ground_u=0.20,
                ach=2.5,
                window_type="triple",
                wwr=20,
                energyplus_path=r"C:\EnergyPlusV25-2-0\energyplus.exe"
            )
            print("Test completed successfully!")
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print(f"Base IDF not found: {base_idf}")
