#!/usr/bin/env python3
"""
Sobol Sensitivity Analysis — Hotel, Lund, Sweden
====================================================================
Follows the same structure as sobol_sensitivity_sfh_v2.py.
Does NOT modify api_server.py, eppy_custom_simulation.py, or the
simulation cache. All output files use the _mfd suffix.

BUILDING TYPE:
    Hotel
    ASHRAE prototype: 6 floors, 11,873 m² total
    Wall construction: steel frame + mineral wool insulation
    Window: double-glazed (SimpleGlazingSystem)

PARAMETERS (7 continuous — ventilation type excluded as categorical):
    1. Wall U-value        (W/m²K) : 0.20 – 0.58
       Source: MFD IDF table (before-1961 = 0.58, 1996-2005 = 0.20)
    2. Attic U-value       (W/m²K) : 0.13 – 0.36
       Source: MFD IDF table (before-1961 = 0.36, 1996-2005 = 0.13)
    3. Ground Slab U-value (W/m²K) : 0.22 – 0.36
       Source: MFD IDF table (before-1961 = 0.36, 1996-2005 = 0.22)
    4. Window U-value      (W/m²K) : 1.20 – 2.80
       Source: IDF table gives [1.80, 2.22]; widened to [1.20, 2.80]
       to cover the full glazing spectrum (triple to single) for
       sensitivity analysis purposes.
    5. SHGC                (-)     : 0.40 – 0.81
       Source: tool glazing model (triple=0.40, single=0.81).
       Varies independently of Window U-value (same approach as SFH v2).
    6. ACH                 (h⁻¹)  : 0.02 – 0.15
       Source: IDF prototype range is [0.04, 0.05] — widened to
       [0.02, 0.15] to cover realistic MFD infiltration variation and
       allow meaningful sensitivity quantification.
    7. WWR                 (%)     : 15 – 30
       Source: tool parameter range for MFD (base WWR = 20%).
       Passed as float directly to generate_custom_idf_eppy (not
       rounded to int) to preserve Saltelli sample precision.

FIXED:
    - Location        : Lund (Climate Zone III)
    - Building type   : mid-rise-apartment
    - Floor area      : 3,135 m² (prototype default)
    - Floors          : 4 (prototype default)
    - Ventilation type: mechanical-exhaust-hr (fixed — categorical)

OUTPUT FILES (saved in backend folder):
    sobol_results_hotel.csv     — raw results (18,432 rows)
    sobol_indices_hotel.csv     — S1 and ST indices with 95% CI
    sobol_indices_hotel.xlsx    — formatted Excel
    sobol_bar_chart_hotel.png   — S1 vs ST bar chart

RUN:
    python sobol_sensitivity_hotel.py
    python sobol_sensitivity_hotel.py --n 2048 --workers 16 --resume
"""

import os
import sys
import csv
import shutil
import hashlib
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# ── SALib ─────────────────────────────────────────────────────────────────────
try:
    from SALib.sample import saltelli
    from SALib.analyze import sobol
    import numpy as np
except ImportError:
    print("❌ SALib not installed. Run: pip install SALib")
    sys.exit(1)

# ── Path setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── Imports from existing backend (read-only) ─────────────────────────────────
from api_server import (
    run_energyplus,
    parse_annual_results,
    parse_hourly_results,
    download_epw,
    calculate_ground_temps_and_location,
    ENERGYPLUS_PATH,
    IDF_DIR,
    WEATHER_DIR,
    OUTPUT_DIR,
    MODIFIED_IDF_DIR,
    CUSTOM_IDF_TEMPLATES,
)
from eppy_custom_simulation import (
    generate_custom_idf_eppy,
    set_idd_path,
    EPPY_AVAILABLE,
)

# ── Configuration ─────────────────────────────────────────────────────────────
WEATHER_STATION  = "lund"
BUILDING_TYPE    = "hotel"
FLOOR_AREA       = 11873.0   # m² — prototype default (6 floors, 11,873 m² total)
NUM_FLOORS       = 6        # prototype default
VENTILATION_TYPE = "mechanical-exhaust-hr"  # fixed — categorical, excluded from Sobol

# ── Sobol problem — 7 continuous parameters ───────────────────────────────────
PROBLEM = {
    'num_vars': 7,
    'names': [
        'wall_u',
        'attic_u',
        'ground_u',
        'window_u',
        'shgc',
        'ach',
        'wwr',
    ],
    'bounds': [
        [0.23, 1.10],    # Wall U-value (W/m²K) — from Hotel IDF table
        [0.14, 0.76],    # Attic U-value (W/m²K) — from Hotel IDF table
        [0.19, 0.52],    # Ground Slab U-value (W/m²K) — from Hotel IDF table
        [1.50, 3.14],    # Window U-value (W/m²K) — from Hotel IDF table
        [0.40, 0.81],    # SHGC — tool glazing model (triple=0.40, single=0.81)
        [0.05, 0.30],    # ACH (h⁻¹) — widened from IDF range [0.11, 0.15]
        [15.0, 40.0],    # WWR (%) — tool parameter range for Hotel (base=27%)
    ],
}

PARAM_LABELS = {
    'wall_u':   'Wall U-value',
    'attic_u':  'Attic U-value',
    'ground_u': 'Ground Slab U-value',
    'window_u': 'Window U-value',
    'shgc':     'SHGC',
    'ach':      'ACH',
    'wwr':      'WWR',
}

# ── Output files ──────────────────────────────────────────────────────────────
OUTPUT_CSV   = BASE_DIR / "sobol_results_hotel.csv"
INDICES_CSV  = BASE_DIR / "sobol_indices_hotel.csv"
INDICES_XLSX = BASE_DIR / "sobol_indices_hotel.xlsx"
SENS_OUT_DIR = OUTPUT_DIR / "sobol_hotel"

RESULT_FIELDS = [
    "run_id", "status",
    "wall_u", "attic_u", "ground_u", "window_u", "shgc", "ach", "wwr",
    "heating_kwh", "cooling_kwh", "total_kwh", "eui_kwh_m2",
    "peak_heating_kw", "peak_cooling_kw", "floor_area_m2",
    "error",
]

# ── Run hash ──────────────────────────────────────────────────────────────────
def get_run_hash(params):
    key = "_".join([
        f"{params['wall_u']:.6f}",
        f"{params['attic_u']:.6f}",
        f"{params['ground_u']:.6f}",
        f"{params['window_u']:.6f}",
        f"{params['shgc']:.6f}",
        f"{params['ach']:.6f}",
        f"{params['wwr']:.4f}",
    ])
    return hashlib.md5(key.encode()).hexdigest()[:12]

# ── Single simulation ─────────────────────────────────────────────────────────
def run_single(combo):
    """
    Run one EnergyPlus simulation for a Sobol sample point.

    Steps:
        1. Select base IDF for mechanical-exhaust-hr ventilation (MFD)
        2. Generate modified IDF via eppy (wall, attic, slab, ACH, WWR)
        3. Override window U-value and SHGC independently via eppy
        4. Run EnergyPlus
        5. Parse and return results

    WWR is passed as float (not rounded to int) to preserve Saltelli
    sample precision. generate_custom_idf_eppy handles float WWR via
    vertex scaling internally.

    Does NOT write to simulation_cache.db.
    Does NOT modify api_server.py or eppy_custom_simulation.py.
    """
    run_id = combo["run_id"]
    params = {k: combo[k] for k in PROBLEM['names']}
    run_hash = get_run_hash(params)

    try:
        # Step 1: Base IDF
        type_templates = CUSTOM_IDF_TEMPLATES.get(
            BUILDING_TYPE, CUSTOM_IDF_TEMPLATES["single-family-house"])
        idf_template  = type_templates[VENTILATION_TYPE]
        base_idf_path = IDF_DIR / idf_template

        if not base_idf_path.exists():
            return {**combo, "status": "error",
                    "error": f"IDF not found: {idf_template}"}

        # Step 2: EPW
        epw_path = download_epw(WEATHER_STATION)
        if not epw_path:
            return {**combo, "status": "error", "error": "EPW download failed"}

        ground_temps, lat, lon, elev = calculate_ground_temps_and_location(epw_path)

        # Step 3: Generate modified IDF via eppy
        # window_type="double" is a placeholder — overridden below
        custom_idf_path = MODIFIED_IDF_DIR / f"sobol_hotel_{run_hash}.idf"

        generate_custom_idf_eppy(
            base_idf_path    = str(base_idf_path),
            output_idf_path  = str(custom_idf_path),
            station_name     = WEATHER_STATION,
            latitude         = lat,
            longitude        = lon,
            elevation        = elev,
            ground_temps     = ground_temps,
            wall_u           = params['wall_u'],
            attic_u          = params['attic_u'],
            ground_u         = params['ground_u'],
            ach              = params['ach'],
            window_type      = "double",      # placeholder — overridden below
            wwr              = params['wwr'], # float — vertex scaling handles it
            heated_floor_area= FLOOR_AREA,
            num_floors       = NUM_FLOORS,
            building_type    = BUILDING_TYPE,
            energyplus_path  = ENERGYPLUS_PATH,
            ventilation_type = VENTILATION_TYPE,
        )

        # Step 3b: Override window U-value and SHGC independently
        from eppy.modeleditor import IDF as EppyIDF
        set_idd_path(ENERGYPLUS_PATH)
        idf = EppyIDF(str(custom_idf_path))
        glazing = idf.idfobjects["WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM"]
        for mat in glazing:
            mat.UFactor = float(params['window_u'])
            mat.Solar_Heat_Gain_Coefficient = round(float(params['shgc']), 4)
        idf.saveas(str(custom_idf_path))
        print(f"  Step 3b override: Window U={params['window_u']:.4f} W/m²K, "
              f"SHGC={params['shgc']:.4f}")

        # Step 4: Run EnergyPlus
        sim_output_dir = SENS_OUT_DIR / f"run_{run_hash}"
        sim_result = run_energyplus(custom_idf_path, epw_path, sim_output_dir)

        if not sim_result:
            return {**combo, "status": "error",
                    "error": "EnergyPlus simulation failed"}

        # Step 5: Parse results
        sql_path = sim_output_dir / "eplusout.sql"
        annual   = parse_annual_results(sql_path)
        hourly   = parse_hourly_results(sql_path)

        if not annual:
            return {**combo, "status": "error",
                    "error": "Could not parse annual results"}

        if hourly:
            annual["peak_heating_kw"] = max(hourly["heating_power_kw"]) if hourly["heating_power_kw"] else 0
            annual["peak_cooling_kw"] = max(hourly["cooling_power_kw"]) if hourly["cooling_power_kw"] else 0

        # Cleanup
        try:
            shutil.rmtree(sim_output_dir)
        except Exception:
            pass
        try:
            custom_idf_path.unlink()
        except Exception:
            pass

        return {
            "run_id":          run_id,
            "status":          "ok",
            "wall_u":          params['wall_u'],
            "attic_u":         params['attic_u'],
            "ground_u":        params['ground_u'],
            "window_u":        params['window_u'],
            "shgc":            params['shgc'],
            "ach":             params['ach'],
            "wwr":             params['wwr'],
            "heating_kwh":     annual.get("heating", 0),
            "cooling_kwh":     annual.get("cooling", 0),
            "total_kwh":       annual.get("total", 0),
            "eui_kwh_m2":      annual.get("eui", 0),
            "peak_heating_kw": annual.get("peak_heating_kw", 0),
            "peak_cooling_kw": annual.get("peak_cooling_kw", 0),
            "floor_area_m2":   annual.get("floor_area", FLOOR_AREA),
        }

    except Exception as e:
        return {
            **combo,
            "status": "error",
            "error":  f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
        }

# ── CSV helpers ───────────────────────────────────────────────────────────────
def load_completed_run_ids(csv_path):
    completed = set()
    if not csv_path.exists():
        return completed
    with open(csv_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if parts and parts[0].isdigit():
                completed.add(int(parts[0]))
    return completed

def append_result_to_csv(result, csv_path, write_header=False):
    mode = "w" if write_header else "a"
    with open(csv_path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow({k: result.get(k, "") for k in RESULT_FIELDS})

# ── Sobol index computation ───────────────────────────────────────────────────
def compute_sobol_indices(csv_path, param_values, metrics):
    results = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'ok':
                results[int(row['run_id'])] = row

    indices = {}
    for metric_key, metric_label in metrics.items():
        Y = []
        missing = []
        for i in range(len(param_values)):
            run_id = i + 1
            if run_id in results:
                try:
                    Y.append(float(results[run_id][metric_key]))
                except (ValueError, KeyError):
                    Y.append(np.nan)
                    missing.append(run_id)
            else:
                Y.append(np.nan)
                missing.append(run_id)

        Y = np.array(Y)
        if missing:
            print(f"  WARNING: {len(missing)} missing/failed runs for "
                  f"{metric_label}. Replacing with mean.")
            mean_val = np.nanmean(Y)
            Y = np.where(np.isnan(Y), mean_val, Y)

        Si = sobol.analyze(PROBLEM, Y, calc_second_order=False,
                           print_to_console=False)
        indices[metric_key] = {
            'S1':      Si['S1'],
            'S1_conf': Si['S1_conf'],
            'ST':      Si['ST'],
            'ST_conf': Si['ST_conf'],
        }
        print(f"\n  {metric_label}:")
        for j, name in enumerate(PROBLEM['names']):
            print(f"    {PARAM_LABELS[name]:<22}: "
                  f"S1={Si['S1'][j]:.4f} ±{Si['S1_conf'][j]:.4f}  "
                  f"ST={Si['ST'][j]:.4f} ±{Si['ST_conf'][j]:.4f}")

    return indices

# ── Save indices CSV ──────────────────────────────────────────────────────────
def save_indices_csv(indices, metrics, csv_path):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Parameter', 'S1', 'S1_conf_95',
                         'ST', 'ST_conf_95', 'Interaction_ST_minus_S1'])
        for metric_key, metric_label in metrics.items():
            idx = indices[metric_key]
            for j, pk in enumerate(PROBLEM['names']):
                s1    = round(float(idx['S1'][j]), 4)
                s1c   = round(float(idx['S1_conf'][j]), 4)
                st    = round(float(idx['ST'][j]), 4)
                stc   = round(float(idx['ST_conf'][j]), 4)
                inter = round(max(0, st - s1), 4)
                writer.writerow([metric_label, PARAM_LABELS[pk],
                                 s1, s1c, st, stc, inter])
    print(f"✓ Indices CSV saved: {csv_path}")

# ── Excel export ──────────────────────────────────────────────────────────────
def export_indices_to_excel(indices, metrics, xlsx_path):
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()
        header_fill = PatternFill("solid", fgColor="1F3864")
        header_font = Font(color="FFFFFF", bold=True)

        def style_header(ws):
            for cell in ws[1]:
                cell.fill      = header_fill
                cell.font      = header_font
                cell.alignment = Alignment(horizontal="center")

        # Summary sheet
        ws_sum = wb.active
        ws_sum.title = "Summary"
        ws_sum.append([f"Sobol Sensitivity Analysis — Hotel, Lund, Sweden"])
        ws_sum['A1'].font = Font(bold=True, size=13)
        ws_sum.append([f"N = 2048  |  Total simulations = 18,432  |  "
                        f"7 parameters  |  SHGC independent  |  "
                        f"Ventilation fixed at Mech-HR"])
        ws_sum.append([f"Building: Hotel  |  "
                        f"Floor area: {FLOOR_AREA} m²  |  Floors: {NUM_FLOORS}  |  "
                        f"Location: Lund, Sweden"])
        ws_sum.append([])

        metric_short = {
            'heating_kwh':     'Heating',
            'cooling_kwh':     'Cooling',
            'eui_kwh_m2':      'EUI',
            'peak_heating_kw': 'Pk Heat',
            'peak_cooling_kw': 'Pk Cool',
        }
        headers = ['Parameter']
        for mk in metrics:
            headers += [f'{metric_short[mk]} S1', f'{metric_short[mk]} ST']
        ws_sum.append(headers)
        style_header(ws_sum)

        for j, pk in enumerate(PROBLEM['names']):
            row = [PARAM_LABELS[pk]]
            for mk in metrics:
                s1 = round(float(indices[mk]['S1'][j]), 4)
                st = round(float(indices[mk]['ST'][j]), 4)
                row += [s1, st]
            ws_sum.append(row)

        for col in range(1, len(headers) + 1):
            ws_sum.column_dimensions[get_column_letter(col)].width = 14
        ws_sum.column_dimensions['A'].width = 22

        # One sheet per metric
        safe_metric_names = {
            'heating_kwh':     'Annual Heating kWh',
            'cooling_kwh':     'Annual Cooling kWh',
            'eui_kwh_m2':      'EUI kWh per m2',
            'peak_heating_kw': 'Peak Heating kW',
            'peak_cooling_kw': 'Peak Cooling kW',
        }

        for metric_key, metric_label in metrics.items():
            ws = wb.create_sheet(title=safe_metric_names[metric_key])
            ws.append(['Parameter', 'S1', 'S1 Conf ±95%',
                       'ST', 'ST Conf ±95%', 'Interaction (ST-S1)'])
            style_header(ws)

            param_order = sorted(range(len(PROBLEM['names'])),
                                 key=lambda j: indices[metric_key]['ST'][j],
                                 reverse=True)
            for rank, j in enumerate(param_order):
                pk    = PROBLEM['names'][j]
                s1    = round(float(indices[metric_key]['S1'][j]), 4)
                s1c   = round(float(indices[metric_key]['S1_conf'][j]), 4)
                st    = round(float(indices[metric_key]['ST'][j]), 4)
                stc   = round(float(indices[metric_key]['ST_conf'][j]), 4)
                inter = round(max(0.0, st - s1), 4)
                ws.append([PARAM_LABELS[pk], s1, s1c, st, stc, inter])
                if rank < 2:
                    for cell in ws[ws.max_row]:
                        cell.fill = PatternFill("solid", fgColor="D9E1F2")

            for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                ws.column_dimensions[col].width = 20

        wb.save(str(xlsx_path))
        print(f"✓ Excel saved: {xlsx_path}")

    except ImportError:
        print("⚠ openpyxl not installed — skipping Excel export")
    except Exception as e:
        print(f"⚠ Excel export failed: {e}")

# ── Bar chart ─────────────────────────────────────────────────────────────────
def plot_sobol_bar(indices, metrics, out_dir):
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches

        plt.rcParams.update({
            'font.family':       'Liberation Serif',
            'axes.spines.top':   False,
            'axes.spines.right': False,
            'figure.dpi':        150,
        })

        METRIC_COLORS = {
            'heating_kwh':     '#C0392B',
            'cooling_kwh':     '#1A6FA8',
            'eui_kwh_m2':      '#1E7A4E',
            'peak_heating_kw': '#E67E22',
            'peak_cooling_kw': '#8E44AD',
        }
        METRIC_NAMES = {
            'heating_kwh':     'Annual Heating',
            'cooling_kwh':     'Annual Cooling',
            'eui_kwh_m2':      'EUI',
            'peak_heating_kw': 'Peak Heating',
            'peak_cooling_kw': 'Peak Cooling',
        }

        param_names = [PARAM_LABELS[pk] for pk in PROBLEM['names']]
        n_params    = len(param_names)
        n_metrics   = len(metrics)

        fig, axes = plt.subplots(1, n_metrics, figsize=(20, 6.5), sharey=True)
        plt.subplots_adjust(left=0.13, right=0.98, top=0.87,
                            bottom=0.12, wspace=0.25)

        for j, (metric_key, metric_label) in enumerate(metrics.items()):
            ax    = axes[j]
            idx   = indices[metric_key]
            color = METRIC_COLORS.get(metric_key, '#555555')
            y_pos = np.arange(n_params)

            ax.barh(y_pos + 0.18, idx['S1'], height=0.33,
                    color=color, alpha=0.88)
            ax.barh(y_pos - 0.18, idx['ST'], height=0.33,
                    color=color, alpha=0.38)
            ax.errorbar(idx['S1'], y_pos + 0.18,
                        xerr=idx['S1_conf'], fmt='none',
                        color='#333333', capsize=3, linewidth=1)
            ax.errorbar(idx['ST'], y_pos - 0.18,
                        xerr=idx['ST_conf'], fmt='none',
                        color='#333333', capsize=3, linewidth=1)

            ax.set_title(METRIC_NAMES.get(metric_key, metric_label),
                         fontsize=11, fontweight='bold', pad=8)
            ax.set_xlim(0, 1.05)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.tick_params(axis='x', labelsize=9)
            ax.axvline(0, color='#cccccc', linewidth=0.8)
            ax.set_xlabel('Sensitivity Index', fontsize=10)

            if j == 0:
                ax.set_yticks(y_pos)
                ax.set_yticklabels(param_names, fontsize=10)

        fig.suptitle(
            'Sobol Sensitivity Analysis — S1 and ST Indices\n'
            'Hotel  |  Lund, Sweden  |  7 parameters  |  '
            'N = 2,048  |  18,432 simulations  |  '
            'Ventilation fixed at Mech-HR  |  '
            'Error bars: 95% Confidence Intervals',
            fontsize=11, fontweight='bold')

        patch_s1 = mpatches.Patch(color='#555555', alpha=0.88,
                                   label='S1 — direct effect only')
        patch_st = mpatches.Patch(color='#555555', alpha=0.38,
                                   label='ST — direct + interaction effects')
        fig.legend(handles=[patch_s1, patch_st], fontsize=9,
                   loc='lower center', ncol=2,
                   bbox_to_anchor=(0.5, 0.00), framealpha=0.9)

        fname = Path(out_dir) / 'sobol_bar_chart_hotel.png'
        plt.savefig(fname, dpi=200, bbox_inches='tight')
        plt.close()
        print(f"✓ Bar chart saved: {fname}")

    except ImportError:
        print("⚠ matplotlib not installed — skipping chart")
    except Exception as e:
        print(f"⚠ Chart failed: {e}")
        traceback.print_exc()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Sobol Sensitivity Analysis — Hotel, Lund"
    )
    parser.add_argument('--n', type=int, default=2048,
                        help='Saltelli N (default: 2048 → 18,432 sims)')
    parser.add_argument('--workers', type=int, default=16,
                        help='Parallel EnergyPlus workers (default: 16)')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from existing CSV')
    args = parser.parse_args()

    if not EPPY_AVAILABLE:
        print("❌ eppy not installed. Run: pip install eppy")
        sys.exit(1)
    if not Path(ENERGYPLUS_PATH).exists():
        print(f"❌ EnergyPlus not found at: {ENERGYPLUS_PATH}")
        sys.exit(1)

    SENS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    MODIFIED_IDF_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"  SOBOL SENSITIVITY ANALYSIS — HOTEL, LUND")
    print(f"{'='*65}")
    print(f"  Building type : {BUILDING_TYPE}")
    print(f"  Floor area    : {FLOOR_AREA} m²  ({NUM_FLOORS} floors)")
    print(f"  Parameters    : {PROBLEM['num_vars']}")
    print(f"  N             : {args.n}")
    print(f"  Total sims    : {args.n * (PROBLEM['num_vars'] + 2)}")
    print(f"  Workers       : {args.workers}")
    print(f"  Ventilation   : {VENTILATION_TYPE} (fixed)")
    print(f"  Output CSV    : {OUTPUT_CSV}")
    print(f"{'='*65}\n")

    # Generate Saltelli sample matrix
    param_values = saltelli.sample(PROBLEM, args.n, calc_second_order=False)
    total = len(param_values)
    print(f"  Generated {total} Saltelli sample points\n")

    # Build combo list
    combinations = []
    for i, row in enumerate(param_values):
        combo = {'run_id': i + 1}
        for j, name in enumerate(PROBLEM['names']):
            combo[name] = float(row[j])
        combinations.append(combo)

    # Resume
    completed_ids = set()
    write_header  = True
    if args.resume and OUTPUT_CSV.exists():
        completed_ids = load_completed_run_ids(OUTPUT_CSV)
        write_header  = False
        print(f"  Resuming — {len(completed_ids)} runs already completed\n")

    pending = [c for c in combinations if c['run_id'] not in completed_ids]
    print(f"  Runs to execute: {len(pending)}\n")

    if write_header:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS,
                                    extrasaction="ignore")
            writer.writeheader()

    completed  = len(completed_ids)
    failed     = 0
    start_time = datetime.now()

    if pending:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run_single, combo): combo
                       for combo in pending}
            for future in as_completed(futures):
                result = future.result()
                completed += 1
                status = result.get("status", "error")

                if status == "error":
                    failed += 1
                    print(f"  [{completed}/{total}] Run "
                          f"{result.get('run_id')} FAILED: "
                          f"{str(result.get('error', ''))[:80]}")
                else:
                    elapsed      = (datetime.now() - start_time).total_seconds()
                    done_so_far  = completed - len(completed_ids)
                    rate         = done_so_far / elapsed if elapsed > 0 else 1
                    remaining    = (total - completed) / rate if rate > 0 else 0
                    print(f"  [{completed}/{total}] "
                          f"Run {result.get('run_id'):>5} ✓  "
                          f"Heat={result.get('heating_kwh', 0):>8.1f} kWh  "
                          f"Cool={result.get('cooling_kwh', 0):>7.1f} kWh  "
                          f"ETA: {remaining/60:.0f} min")

                append_result_to_csv(result, OUTPUT_CSV, write_header=False)

        print(f"\n{'='*65}")
        print(f"  SIMULATIONS COMPLETE — {completed} runs, {failed} failed")
        print(f"  Duration: {datetime.now() - start_time}")
        print(f"{'='*65}\n")

    # Compute Sobol indices
    print("Computing Sobol indices...")
    METRICS = {
        'heating_kwh':     'Annual Heating (kWh)',
        'cooling_kwh':     'Annual Cooling (kWh)',
        'eui_kwh_m2':      'EUI (kWh/m²)',
        'peak_heating_kw': 'Peak Heating (kW)',
        'peak_cooling_kw': 'Peak Cooling (kW)',
    }

    indices = compute_sobol_indices(OUTPUT_CSV, param_values, METRICS)
    save_indices_csv(indices, METRICS, INDICES_CSV)
    export_indices_to_excel(indices, METRICS, INDICES_XLSX)
    plot_sobol_bar(indices, METRICS, BASE_DIR)

    print(f"\n✓ Raw results  : {OUTPUT_CSV}")
    print(f"✓ Indices CSV  : {INDICES_CSV}")
    print(f"✓ Indices XLSX : {INDICES_XLSX}")
    print(f"✓ Bar chart    : {BASE_DIR / 'sobol_bar_chart_hotel.png'}\n")


if __name__ == "__main__":
    main()
