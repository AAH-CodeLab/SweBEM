import argparse
import epw
from paths import WEATHER_DIR

def main(station_id: str):
    weather_file = epw.download_epw(station_id, WEATHER_DIR)
    return weather_file
    
if __name__ == "__main__":
    main("lund")
