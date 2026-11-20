"""
rerun_failed_hospital.py
────────────────────────────────────────────────────────────────────────────
Reruns only the failed simulations in sobol_results_hospital.csv (status='error'
or all-zero output rows), using the same Saltelli sample matrix as the original
run to preserve run_id mapping. Updates the CSV in place, then recomputes Sobol
indices and regenerates the bar chart.

Usage (from backend folder, alongside sobol_sensitivity_hospital.py):
    python rerun_failed_hospital.py

Expected runtime: ~22 minutes for 76 failed runs at 16 workers.
"""

import csv, sys, time, shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from SALib.sample import saltelli

# Import everything from the main hospital script
sys.path.insert(0, str(Path(__file__).parent))
from sobol_sensitivity_hospital import (
    PROBLEM, PARAM_LABELS,
    BASE_DIR, OUTPUT_CSV, INDICES_CSV, INDICES_XLSX, RESULT_FIELDS,
    run_single,
    compute_sobol_indices, save_indices_csv,
    export_indices_to_excel, plot_sobol_bar,
)

N        = 512   # must match original run
WORKERS  = 16

# METRICS dict is defined inside main() in the original script,
# so we redefine it here identically.
METRICS = {
    'heating_kwh':     'Annual Heating (kWh)',
    'cooling_kwh':     'Annual Cooling (kWh)',
    'eui_kwh_m2':      'EUI (kWh/m²)',
    'peak_heating_kw': 'Peak Heating (kW)',
    'peak_cooling_kw': 'Peak Cooling (kW)',
}


# ── Helper: detect silent failures (status='ok' but all outputs zero) ─────────
def is_zero_row(row):
    try:
        return (float(row['heating_kwh'])     == 0.0 and
                float(row['cooling_kwh'])     == 0.0 and
                float(row['peak_heating_kw']) == 0.0)
    except (ValueError, KeyError, TypeError):
        return False


def main():
    # ── Step 1: Load existing CSV and identify rows to rerun ──────────────────
    print(f"\n{'='*65}")
    print(f"  RERUN FAILED HOSPITAL SIMULATIONS")
    print(f"{'='*65}")
    print(f"\nLoading existing CSV: {OUTPUT_CSV}")

    if not OUTPUT_CSV.exists():
        print(f"X CSV not found at: {OUTPUT_CSV}")
        sys.exit(1)

    with open(OUTPUT_CSV, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    ok_rows     = [r for r in rows if r['status'] == 'ok']
    failed_rows = [r for r in rows if r['status'] == 'error']
    zero_rows   = [r for r in ok_rows if is_zero_row(r)]

    to_rerun_ids = sorted(
        [int(r['run_id']) for r in failed_rows] +
        [int(r['run_id']) for r in zero_rows]
    )

    print(f"  Total rows                : {total}")
    print(f"  OK rows                   : {len(ok_rows)}")
    print(f"  Failed rows (status=error): {len(failed_rows)}")
    print(f"  Zero-output rows (silent) : {len(zero_rows)}")
    print(f"  Total to rerun            : {len(to_rerun_ids)}")

    if not to_rerun_ids:
        print("\nNo failed runs to rerun. CSV is already clean.")
        return

    # ── Step 2: Regenerate the Saltelli sample matrix ────────────────────────
    print(f"\nRegenerating Saltelli sample matrix (N={N})...")
    param_values = saltelli.sample(PROBLEM, N, calc_second_order=False)

    if len(param_values) != total:
        print(f"X Sample size mismatch: regenerated {len(param_values)} vs CSV {total}")
        print(f"   Did you run the original with N={N}? Check.")
        sys.exit(1)
    print(f"  Matrix matches CSV ({total} sample points)")

    # ── Step 3: Build combos for failed runs ──────────────────────────────────
    combos_to_rerun = []
    for run_id in to_rerun_ids:
        row = param_values[run_id - 1]   # 1-indexed
        combo = {'run_id': run_id}
        for j, name in enumerate(PROBLEM['names']):
            combo[name] = float(row[j])
        combos_to_rerun.append(combo)

    # ── Step 4: Backup the original CSV ───────────────────────────────────────
    backup_path = OUTPUT_CSV.with_suffix('.csv.before_rerun')
    if not backup_path.exists():
        shutil.copy(OUTPUT_CSV, backup_path)
        print(f"\n  Backup created: {backup_path}")

    # ── Step 5: Rerun in parallel ─────────────────────────────────────────────
    est_minutes = len(combos_to_rerun) * 4.5 / WORKERS
    print(f"\nRerunning {len(combos_to_rerun)} simulations with {WORKERS} workers")
    print(f"Estimated time: ~{est_minutes:.0f} minutes\n")

    rerun_results = {}
    t_start = time.time()

    with ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(run_single, combo): combo['run_id']
                   for combo in combos_to_rerun}

        for i, future in enumerate(as_completed(futures), 1):
            run_id = futures[future]
            try:
                result = future.result()
                rerun_results[run_id] = result
                status_str = '+' if result.get('status') == 'ok' else 'X'
                heat = result.get('heating_kwh', 0) or 0
                cool = result.get('cooling_kwh', 0) or 0
                elapsed_min = (time.time() - t_start) / 60
                remaining = elapsed_min * (len(combos_to_rerun) - i) / i if i > 0 else 0
                print(f"  [{i:3d}/{len(combos_to_rerun)}] Run {run_id:4d} {status_str}  "
                      f"Heat={heat:.0f} kWh  Cool={cool:.0f} kWh  "
                      f"ETA: {remaining:.0f} min")
            except Exception as e:
                rerun_results[run_id] = {'run_id': run_id, 'status': 'error',
                                          'error': f"{type(e).__name__}: {e}"}
                print(f"  [{i:3d}/{len(combos_to_rerun)}] Run {run_id:4d} X  ERROR: {e}")

    elapsed_total = (time.time() - t_start) / 60
    print(f"\nRerun complete in {elapsed_total:.1f} min")

    # ── Step 6: Update CSV in place ───────────────────────────────────────────
    print("\nUpdating CSV...")

    rows_by_id = {int(r['run_id']): r for r in rows}
    new_ok = 0
    still_failed = 0

    for run_id, result in rerun_results.items():
        if (result.get('status') == 'ok'
                and float(result.get('heating_kwh', 0) or 0) > 0):
            new_row = {k: result.get(k, '') for k in RESULT_FIELDS}
            rows_by_id[run_id] = new_row
            new_ok += 1
        else:
            still_failed += 1

    print(f"  Newly successful: {new_ok}")
    print(f"  Still failing   : {still_failed}")

    sorted_rows = [rows_by_id[i] for i in sorted(rows_by_id.keys())]
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(sorted_rows)
    print(f"  Updated: {OUTPUT_CSV}")

    # ── Step 7: Recompute Sobol indices ───────────────────────────────────────
    print("\nRecomputing Sobol indices on cleaned data...")
    indices = compute_sobol_indices(OUTPUT_CSV, param_values, METRICS)

    save_indices_csv(indices, METRICS, INDICES_CSV)
    print(f"\n  Indices CSV  : {INDICES_CSV}")

    export_indices_to_excel(indices, METRICS, INDICES_XLSX)
    print(f"  Indices XLSX : {INDICES_XLSX}")

    plot_sobol_bar(indices, METRICS, BASE_DIR)
    print(f"  Bar chart    : {BASE_DIR / 'sobol_bar_chart_hospital.png'}")

    # ── Step 8: Final summary ─────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  FINAL STATS")
    print(f"{'='*65}")
    final_ok     = sum(1 for r in sorted_rows
                       if r['status'] == 'ok' and not is_zero_row(r))
    final_failed = len(sorted_rows) - final_ok
    print(f"  Total              : {len(sorted_rows)}")
    print(f"  Successful         : {final_ok} ({final_ok/len(sorted_rows)*100:.2f}%)")
    print(f"  Failed             : {final_failed} ({final_failed/len(sorted_rows)*100:.2f}%)")
    print(f"{'='*65}\n")


# CRITICAL: Windows multiprocessing requires this guard.
# Without it, child processes re-import the script and recurse infinitely.
if __name__ == '__main__':
    main()
