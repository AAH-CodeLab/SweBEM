import prep_weather_files
import prep_building_files
import run_energyplus
import paths
from paths import OUTPUT_DIR

def calc_heatload(building_type, construction_period, weather_station):
    weather_file = prep_weather_files.main(weather_station)
    idf_file = prep_building_files.main(
        weather_file,
        building_type, 
        construction_period, 
        weather_station,
        )
    output_path = paths.set_output_path(building_type, construction_period, weather_station, OUTPUT_DIR)
    results = run_energyplus.main(idf_file, weather_file, output_path)
    annual_heating = results['heating'] # kWh
    
    return annual_heating

if __name__ == "__main__":
    calc_heatload(
        building_type='single-family-house',
        construction_period='1961-1975',
        weather_station='lund',
    )

