# SweBEM

SweBEM is a web tool for simulating the annual and hourly energy use of Swedish buildings with [EnergyPlus](https://energyplus.net). It is developed at Lund University within the GEOTHERMICA project THE CHANGE.

> **Local use only.** The backend has no authentication or rate limiting and is not hardened for public hosting. Run it on your own machine and do not expose it to the internet.

## Features

- Three simulation modes: preconfigured archetypes, real-time simulation with custom parameters, and batch simulation of building stocks
- Eight building typologies: single-family house, mid-rise apartment, office, hotel, school, hospital, retail and warehouse
- Construction periods from before 1961 to after 2000
- 56 Swedish weather stations
- Annual end-use results and hourly heating and cooling power, exportable to CSV and Excel

## Repository structure

| Folder | Contents |
|---|---|
| `Backend/` | FastAPI server (`api_server.py`) that adapts the building models with eppy (`eppy_custom_simulation.py`), runs EnergyPlus and caches results in SQLite |
| `Backend/idf_files/` | EnergyPlus building models per typology and construction period |
| `Frontend/` | Next.js (React) user interface |
| `../SweBEM_report_261119.pdf` | Report describing the building models |

## Requirements

- [EnergyPlus 26.2](https://energyplus.net/downloads)
- Python 3.10 or later
- Node.js 18.17 or later

## Getting started

### 1. Backend

```bash
cd Backend
pip install -r requirements.txt
python api_server.py
```

The API runs at `http://127.0.0.1:8000`. Weather files are downloaded automatically from Climate.OneBuilding.Org the first time a station is used, and results are cached in `Backend/simulation_cache.db`. Cache entries are specific to the installed EnergyPlus version; entries created before version-aware caching will not be reused.

EnergyPlus 26.2.0 is expected at `C:\EnergyPlusV26-2-0\energyplus.exe`. If it is installed elsewhere, set the `ENERGYPLUS_PATH` environment variable before starting the server:

On Windows, `start.bat` checks this executable before starting the servers and displays a warning if it is missing.

```powershell
# Windows (PowerShell)
$env:ENERGYPLUS_PATH = "D:\EnergyPlusV26-2-0\energyplus.exe"
```

```bash
# Linux / macOS
export ENERGYPLUS_PATH=/usr/local/EnergyPlus-26-2-0/energyplus
```

### 2. Frontend

```bash
cd Frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend connects to `http://localhost:8000` by default. To use another address, create `Frontend/.env.local` containing `NEXT_PUBLIC_API_URL=<backend address>`.

## Data sources

- **Building models** (`Backend/idf_files/`): the origin of the models and how they were adapted to Swedish construction periods are described in the accompanying report, [`SweBEM_report_261119.pdf`](../SweBEM_report_261119.pdf).
- **Weather data:** TMYx weather files from [Climate.OneBuilding.Org](https://climate.onebuilding.org). They are downloaded at runtime and are not included in this repository.
- **Map:** county outlines from the free SVG map of Sweden by [Simplemaps](https://simplemaps.com/svg/country/se).
- **Simulation engine:** [EnergyPlus](https://energyplus.net) (U.S. Department of Energy), scripted with [eppy](https://github.com/santoshphilip/eppy).

## Funding

SweBEM was developed within two projects:

- **The CHANGE**, funded through the GEOTHERMICA and JPP Smart Energy Systems Joint Call 2021 (Swedish Energy Agency, project P2022-01051).
- **COOLGEOHEAT II**, funded by Interreg Öresund-Kattegat-Skagerrak.

## Authors

- Jitendra Pavan Jakkula, Lund University
- Akram Abdul Hamid, Lund University

## How to cite

Use the "Cite this repository" button on GitHub, or see [`CITATION.cff`](../CITATION.cff).

## License

Released under the BSD 3-Clause License. See [`LICENSE`](LICENSE). The report is published separately under CC BY-NC-ND 4.0.
