import requests
import zipfile
import re
import io

def find_region_for_station(station_id, station_mappings, regions):
    search_term = station_mappings.get(station_id, station_id)
    for region, cities in regions.items():
        if search_term in cities:
            return region
    return None

def discover_epw_url(station_id, station_mappings, station_filenames, base_url):
    """Get EPW download URL. Uses STATION_FILENAMES for accurate matching."""
    lookup_id = station_mappings.get(station_id, station_id)
    region = find_region_for_station(station_id)
    if not region:
        return None
    
    # Get the filename pattern for this station
    filename = station_filenames.get(lookup_id, lookup_id)
    region_url = f"{base_url}/{region}/"
    
    try:
        response = requests.get(region_url, timeout=30)
        if response.status_code != 200:
            return None
        html = response.text
        all_zips = re.findall(r'href="([^"]+\.zip)"', html)
        
        # First try 2009-2023 data
        for zf in all_zips:
            if filename in zf and "2009-2023" in zf:
                return f"{base_url}/{region}/{zf}"
        
        # Then try any TMYx
        for zf in all_zips:
            if filename in zf and "TMYx" in zf:
                return f"{base_url}/{region}/{zf}"
        
        # Fallback to search term matching
        search_term = lookup_id
        for zf in all_zips:
            if search_term in zf.lower():
                if "2009-2023" in zf:
                    return f"{base_url}/{region}/{zf}"
        for zf in all_zips:
            if search_term in zf.lower() and "TMYx" in zf:
                return f"{base_url}/{region}/{zf}"
        
        return None
    except:
        return None
    

def download_epw(station_id, weather_dir):
    """
    Downloads EPW file from station id and saves in weather_dir. 
    
    Returns path to the EPW file.

    Note that downloading is skipped if EPW file already exists in weather_dir.
    """
    epw_path = weather_dir / f"{station_id}.epw"
    if epw_path.exists():
        return epw_path
    url = discover_epw_url(station_id)
    if not url:
        print(f"Could not find EPW URL for {station_id}")
        return None
    print(f"Downloading EPW for {station_id}...")
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            epw_files = [f for f in zf.namelist() if f.endswith('.epw')]
            if not epw_files:
                return None
            with open(epw_path, 'wb') as f:
                f.write(zf.read(epw_files[0]))
            print(f"✓ Downloaded: {epw_path}")
            return epw_path
    except Exception as e:
        print(f"Error downloading EPW: {e}")
        return None
    


# NOTES: Can this be done more modular?
# def fetch_epw_path(station_id, weather_dir):
#     epw_path = weather_dir / f"{station_id}.epw"
#     if epw_path.exists():
#         return epw_path
#
# def discover_epw_url()..
#
# def download_epw()...