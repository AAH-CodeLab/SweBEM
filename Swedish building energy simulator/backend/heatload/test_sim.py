import sys
from pathlib import Path
import subprocess

sys.path.insert(0, str(Path(__file__).parent))
# from . import heatload
# from . import epw
from . import idf
# from . import viz
from . import paths
from . import run
from paths import CONFIG_PATH, IDF_DIR, MODIFIED_IDF_DIR, OUTPUT_DIR, ENERGYPLUS_PATH


weather_station = 'lund'
epw_filepath = r"C:\Users\MATL\Documents\Repo\thechange-fast_load_estimator\Swedish building energy simulator\backend\data\weather_files\lund.epw"

config = paths.load_config(CONFIG_PATH)
sim = config["test_simulation_single"]
weather_station      = sim["weather_station"]
building_type        = sim["building_type"]
construction_periods = sim["construction_periods"]

idf_files, output_paths, sql_paths = idf.prepare_idfs(
                                                        config, building_type, construction_periods, 
                                                        weather_station, epw_filepath,
                                                        IDF_DIR, MODIFIED_IDF_DIR, OUTPUT_DIR
                                                        )

for idf_file, output_path in zip(idf_files, output_paths):
    result = run.run_energyplus(idf_file, epw_filepath, output_path, ENERGYPLUS_PATH)

print('---ARGS---\n',result.args)
print('---RETURNCODE---\n',result.returncode, '(SUCCESS)' if result.returncode==0 else '(FAIL)')
print('---STDOUT---\n',result.stdout.decode())
print('---STDERR---\n',result.stderr.decode())

# results = heatload(
#     weather_station      = sim["weather_station"],
#     building_type        = sim["building_type"],
#     construction_periods = sim["construction_periods"],
#     n_CPUs               = sim["n_CPUs"],
#     eplus_path           = ENERGYPLUS_PATH,
# )

# print(type(results))
# print(results.keys())
# nested = results['1996-2005']
# print(list(nested.keys()))
# print(nested['annual'])
# print(results['1996-2005']['annual']['heating'])

