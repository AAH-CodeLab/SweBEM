# SweBEM

**A tool for predicting heating and cooling loads in the Swedish building stock, based on building typologies.**

SweBEM is a web-based tool that returns hourly heating and cooling load profiles, peak loads, and annual energy use for typical Swedish buildings. It combines EnergyPlus archetype models of eight building typologies with weather data for 56 locations in Sweden. The tool was developed at the Division of Building Physics, Lund University, to support early-stage design of geothermal 5th-generation district heating and cooling (5GDHC) networks, where building loads are needed before detailed building data are available.

This repository contains the source code of the tool and the EnergyPlus archetype models (IDF files).

> **Local use only.** The backend has no authentication or rate limiting and is not hardened for public hosting. Do not expose it to the internet.

## Report

The method, the archetype definitions, all input data, and the comparison against national statistics are documented in:

> Jakkula, J., & Abdul Hamid, A. (2026). *SweBEM – Tool for Predicting Heating and Cooling Loads in the Swedish Building Stock: A Building Typology-Based Approach* (Report TVBH-3073). Division of Building Physics, Lund University.
> [Record in the Lund University research portal](https://portal.research.lu.se/sv/publications/swebem-tool-for-predicting-heating-and-cooling-loads-in-the-swedi/) · [PDF](https://lucris.lub.lu.se/ws/portalfiles/portal/270156249/SweBEM_report_261119.pdf)

## What the tool does

SweBEM has three simulation modes:

- **Pre-configured** – choose a building typology, a construction period, and a location, and get the results for the corresponding archetype.
- **Real-time customization** – start from an archetype and change envelope U-values, window type, window-to-wall ratio, infiltration, ventilation system, number of floors, and heated floor area. The model is modified and simulated on demand.
- **Batch** – define several buildings and simulate them in one run.

Results:

- hourly heating and cooling load profiles (8760 h)
- peak heating and cooling loads
- annual energy use by end use, and energy use intensity (EUI)

## Building typologies

The stock is represented by 34 archetype models:

| Typology | Construction periods |
|---|---|
| Single-family house | before 1961, 1961–1975, 1976–1985, 1986–1995, 1996–2005 |
| Multi-family building | before 1961, 1961–1975, 1976–1985, 1986–1995, 1996–2005 |
| Office | before 1961, 1961–1975, 1976–1985, 1986–1995, 1996–2005 |
| Hotel | before 1961, 1961–1975, 1976–1985, 1986–1995, 1996–2005 |
| School | before 1961, 1961–1970, 1971–1980, 1981–1990, 1991–2000, after 2000 |
| Hospital | before 1961, 1961–1970, 1971–1980, 1981–1990, 1991–2000, after 2000 |
| Retail | after 2000 |
| Warehouse | after 2000 |

Ventilation is modeled as natural ventilation (NV), mechanical exhaust ventilation (MEV), balanced ventilation without heat recovery (BV), or mechanical ventilation with heat recovery (MVHR). Envelope properties, ventilation rates, internal loads, and schedules for each archetype are listed in the report.

Weather data are typical meteorological years (TMYx) from [climate.onebuilding.org](https://climate.onebuilding.org) for 56 locations covering the four Swedish climate zones. The files are downloaded automatically the first time a location is used.

## Repository structure

```
SweBEM_No_Login/
  Backend/
    api_server.py               FastAPI server: runs EnergyPlus, parses results, caches them in SQLite
    eppy_custom_simulation.py   Modifies archetype IDF files for real-time customization
    idf_files/                  EnergyPlus archetype models, one folder per typology
  Frontend/
    app/                        Next.js pages
    components/                 Simulation steps, map and result views
    lib/                        API client and climate data
  start.bat                     Windows launcher
SweBEM_report_261119.pdf        Report describing the building models
```

## Getting started

### Requirements

- [EnergyPlus](https://energyplus.net) 26.2.0
- Python 3.10 or later
- Node.js 18.17 or later

### Backend

From the repository root:

```bash
cd SweBEM_No_Login/Backend
pip install -r requirements.txt
python api_server.py
```

The default executable is `C:\EnergyPlusV26-2-0\energyplus.exe`. If EnergyPlus is installed elsewhere, set the `ENERGYPLUS_PATH` environment variable to its executable before starting the server. On Windows, `SweBEM_No_Login/start.bat` checks the executable and starts both servers.

The API runs at `http://localhost:8000`. Open that address in a browser to check that the server is running and that EnergyPlus was found.

### Frontend

In a separate terminal, from the repository root:

```bash
cd SweBEM_No_Login/Frontend
npm install
npm run dev
```

The user interface runs at `http://localhost:3000`.

The frontend connects to `http://localhost:8000` by default. To use another backend address, set `NEXT_PUBLIC_API_URL` in `SweBEM_No_Login/Frontend/.env.local`. No login is required. Simulation results are cached locally by the backend in `SweBEM_No_Login/Backend/simulation_cache.db` and are specific to the EnergyPlus version.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Server status |
| `POST` | `/simulate` | Simulate an archetype (pre-configured mode) |
| `POST` | `/simulate/custom` | Simulate a customized building (real-time customization) |
| `GET` | `/cache/stats` | List cached simulations |

To clear the cache, stop the backend and delete `SweBEM_No_Login/Backend/simulation_cache.db`.

Example:

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"weatherStation": "lund", "constructionPeriod": "1976-1985", "buildingType": "single-family-house"}'
```

The response contains annual results (`annual`), hourly heating and cooling power in kW (`hourly`), and a flag that tells whether the result came from the cache (`cached`).

## Scope and limitations

- The archetypes represent typical buildings of a typology and construction period, not individual buildings. The tool is intended for early-stage studies at district level.
- Heating and cooling are calculated with ideal-loads air systems. The results are therefore thermal loads, not the energy use of a specific heating or cooling system.
- The comparison against Swedish district heating statistics in the report is indicative. The models are not calibrated against measured data for individual buildings.

See the report for assumptions and a full discussion of limitations.

## How to cite

If you use SweBEM, please cite the report:

```bibtex
@techreport{jakkula2026swebem,
  author      = {Jakkula, Jitendra and Abdul Hamid, Akram},
  title       = {{SweBEM} -- Tool for Predicting Heating and Cooling Loads in the {Swedish} Building Stock: A Building Typology-Based Approach},
  institution = {Division of Building Physics, Lund University},
  number      = {TVBH-3073},
  year        = {2026},
  address     = {Lund, Sweden},
  url         = {https://portal.research.lu.se/sv/publications/swebem-tool-for-predicting-heating-and-cooling-loads-in-the-swedi/}
}
```

## Authors

- Jitendra Jakkula – Division of Building Physics, Lund University
- Akram Abdul Hamid – Division of Building Physics, Lund University ([ORCID](https://orcid.org/0000-0002-1596-0210))

Questions and feedback: please open an issue in this repository.

## Funding

SweBEM was developed within two projects:

- **The CHANGE**, funded through the GEOTHERMICA and JPP Smart Energy Systems Joint Call 2021 (Swedish Energy Agency, project P2022-01051)
- **COOLGEOHEAT II**, funded by Interreg Öresund-Kattegat-Skagerrak

## License

The code is released under the [MIT License](LICENSE).

The report is published separately under CC BY-NC-ND 4.0. That license applies to the report only, not to the code in this repository.
