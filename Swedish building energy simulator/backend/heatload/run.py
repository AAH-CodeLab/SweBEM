import subprocess
import shutil
import os

from eppy.modeleditor import IDF
from eppy.runner.run_functions import runIDFs

from multiprocessing import freeze_support


def make_run_options(idf, output_path):
    idfversion = idf.idfobjects['version'][0].Version_Identifier.split('.')
    idfversion.extend([0] * (3 - len(idfversion)))
    idfversionstr = '-'.join([str(item) for item in idfversion])
    run_options = {
        'ep_version': idfversionstr,
        'output_directory': str(output_path),
        'verbose': 'q',
        'readvars':True,
        'expandobjects':True
        }
    return run_options

def IDF_serial(idf_files, epw_file, output_paths):
    """
    Run EnergyPlus simulations for a list of IDF files against a single EPW weather file.

    Iterates over the provided IDF files and corresponding output paths, initialises
    an :class:`IDF` object for each, builds run options via :func:`make_run_options`,
    and executes the simulation.

    Parameters
    ----------
    idf_files : list[Path]
        Paths to the IDF files to simulate.
    epw_file : Path
        Path to the EPW weather file applied to every simulation.
    output_paths : list[Path]
        Output directories corresponding to each entry in ``idf_files``.
        Must be the same length as ``idf_files``.
    
    Returns
    -------
    None
        Simulation outputs are written to the respective directories in
        *output_paths*.
    """
    for idf_file, output_path in zip(idf_files, output_paths):
        idf_obj = IDF(idf_file, epw_file)
        run_options = make_run_options(idf_obj, output_path)
        idf_obj.run(**run_options)


def IDF_parallel(idf_files, epw_file, output_paths, num_CPUs=2):
    """
    Simulate multiple IDF files in parallel.

    Builds a run list by pairing each IDF file with its corresponding EPW file and
    output directory, then dispatches all simulations across a worker pool.

    Parameters
    ----------
    idf_files : iterable of (str or pathlib.Path)
        Ordered collection of paths to EnergyPlus IDF files.
    epw_file : str or pathlib.Path
        Path to the EnergyPlus EPW weather file shared by all runs.
    output_paths : iterable of (str or pathlib.Path)
        Output directories corresponding 1-to-1 with *idf_files*.
        Each directory should exist before calling this function.
    num_CPUs : int, optional
        Number of worker processes to use. Defaults to ``2``.
        Set to ``-1`` or ``os.cpu_count()`` to use all available cores.

    Returns
    -------
    None
        Simulation outputs are written to the respective directories in
        *output_paths*.
    """
    freeze_support() # important for multiprocessing, blocks each worker from re-executing script from scratch making an infinite loop.
    runs = []
    for idf_file, output_path in zip(idf_files, output_paths):
        idf_obj = IDF(idf_file, epw_file)
        run_options = make_run_options(idf_obj, output_path)
        runs.append([idf_obj, run_options])
    runIDFs(runs, num_CPUs)

def energyplus_matl(idf_file_path, epw_file_path, output_path, eplus_path):
    cl_st = (f'"{eplus_path}\\EnergyPlus" '
        + '--readvars '
        + f'--output-directory "{output_path}" '
        + f'--weather "{epw_file_path}" '
        + f'"{idf_file_path}"'
        )

    result = subprocess.run(
        cl_st,
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(result.stdout)
    return result
    

# def energyplus(idf_path, epw_path, output_path, sql_path, energy_plus_path):
#     if output_path.exists():
#         shutil.rmtree(output_path)
#     output_path.mkdir(parents=True)
#     cmd = [energy_plus_path, "-w", str(epw_path), "-d", str(output_path), "-r", str(idf_path)]
#     try:
#         result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
#         # sql_path = output_dir / "eplusout.sql"
#         if sql_path.exists():
#             return output_path
#         # Print EnergyPlus error file if available
#         err_path = output_path / "eplusout.err"
#         if err_path.exists():
#             err_text = err_path.read_text(encoding="utf-8", errors="ignore")
#             # Print last 60 lines of error file
#             lines = err_text.strip().splitlines()
#             print("\n=== EnergyPlus Error Output ===")
#             print("\n".join(lines[-60:]))
#             print("=== End Error Output ===\n")
#         else:
#             print(f"EnergyPlus stdout: {result.stdout[-2000:]}")
#             print(f"EnergyPlus stderr: {result.stderr[-2000:]}")
#         return None
#     except subprocess.TimeoutExpired:
#         print("EnergyPlus simulation timed out after 600 seconds")
#         return None
#     except Exception as e:
#         print(f"EnergyPlus failed: {e}")
#         return None