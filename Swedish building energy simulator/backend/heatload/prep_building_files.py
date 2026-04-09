import idf
import paths
from paths import CONFIG_PATH, IDF_DIR, MODIFIED_IDF_DIR

def main(epw_file, building_type, construction_period, weather_station):
    config = paths.load_config(CONFIG_PATH)
    ground_temps, lat, lon, elev = idf.calculate_ground_temps_and_location(epw_file)
    idf_path = idf.get_idf_path(config, building_type, construction_period, IDF_DIR)
    idf_content = idf.read_idf_file(idf_path)
    modified_idf_path = idf.get_modified_idf_path(building_type, construction_period, weather_station, MODIFIED_IDF_DIR)
    idf.modify_idf(idf_content, modified_idf_path, weather_station, lat, lon, elev, ground_temps)
    return modified_idf_path
