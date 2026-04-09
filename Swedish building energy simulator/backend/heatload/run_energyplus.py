import run, paths, rpt
from paths import ENERGYPLUS_PATH

def main(idf_file_path, epw_file_path, output_path):
    result = run.energyplus_matl(idf_file_path, epw_file_path, output_path, ENERGYPLUS_PATH)
    sql_path = paths.set_sql_path(output_path)
    result = rpt.parse_annual_results(sql_path)
    return result