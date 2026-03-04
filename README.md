# README

## Current repo structure

    Swedish building energy simulator/
    ├── backend/
    │   ├── api_server.py
    │   ├── eppy_custom_simulation.py
    │   ├── idf_files/
    │   │   ├── hospital/
    │   │   ├── hotel/
    │   │   ├── mfd/
    │   │   ├── office/
    │   │   ├── school/
    │   │   └── sfh/
    │   ├── modified_idf/
    │   ├── output/
    │   │   ├── custom_5e6d9b0bc60eeae62d3a98a68db00827/
    │   │   ├── custom_753b8d3accfd33aa1f2f647742b9923d/
    │   │   ├── custom_7e997c5bd2874be32c6e854988335c00/
    │   │   ├── custom_81dae5b4c4ca79cb3d243f7211671083/
    │   │   ├── custom_8ece2e9d71a9dd61bac1a0d70651a702/
    │   │   ├── custom_df3bc36f64077a7f2dc9b02844e9f7eb/
    │   │   ├── custom_ff4e964fa7fb7e58e1aceb0d950c5d22/
    │   │   ├── hotel_1961-1975_lund/
    │   │   ├── hotel_1986-1995_lund/
    │   │   ├── mid-rise-apartment_1961-1975_lund/
    │   │   ├── mid-rise-apartment_1976-1985_lund/
    │   │   ├── mid-rise-apartment_1986-1995_lund/
    │   │   ├── mid-rise-apartment_1996-2005_lund/
    │   │   ├── office_1961-1975_lund/
    │   │   ├── office_1986-1995_lund/
    │   │   ├── school_1981-1990_lund/
    │   │   ├── single-family-house_1976-1985_lund/
    │   │   ├── single-family-house_1986-1995_lund/
    │   │   └── single-family-house_1996-2005_lund/
    │   ├── simulation_cache.db
    │   └── weather_files/
    │   │   └── lund.epw
    ├── frontend_work/
    │   ├── .gitignore
    │   ├── app/
    │   │   ├── auth/
    │   │   │   └── callback/
    │   │   ├── dashboard-preview/
    │   │   ├── globals.css
    │   │   ├── login/
    │   │   └── simulator/
    │   ├── components/
    │   ├── lib/
    │   ├── next.config.js
    │   ├── postcss.config.js
    └── └── tailwind.config.js




* `backend/`
  * `api_server.py` Contains all the functionality for the api server
  * `eppy_custom_simulation.py`
  * `idf_files/`: .idf files for the different building types 
    * `hospital/`
    * `hotel/`
    * `mfd/`
    * `office/`
    * `school/`
    * `sfh/`
  * `modified_idf/`
  * `output/`: Different output examples

  * `simulation_cache.db`
  * `weather_files/`
    * `lund.epw`
* `frontend_work/`
  * `app/`
    * `auth/`
      * `callback/`
    * `dashboard-preview/`
    * `globals.css`
    * `login/`
    * `simulator/`
  * `components/`
  * `lib/`
  * `next.config.js`
  * `postcss.config.js`
  * `tailwind.config.js`



## Recommended layout (to be revised)

    swedish-building-energy-simulator/
    ├── README.md
    ├── .gitignore
    ├── docs/
    ├── scripts/
    ├── configs/
    │   ├── usecase_a/
    │   │   ├── backend.yaml
    │   │   └── frontend.yaml
    │   └── usecase_b/
    │       ├── backend.yaml
    │       └── frontend.yaml
    ├── apps/
    │   ├── api/                      # backend entrypoint + "product" wiring
    │   │   ├── pyproject.toml
    │   │   ├── src/
    │   │   │   └── api_app/
    │   │   │       ├── main.py        # creates FastAPI/Flask app, loads config
    │   │   │       ├── routes/
    │   │   │       │   ├── common.py
    │   │   │       │   ├── usecase_a.py
    │   │   │       │   └── usecase_b.py
    │   │   │       └── settings.py    # config parsing (env + yaml)
    │   │   └── tests/
    │   └── web/                      # Next.js app
    │       ├── package.json
    │       ├── app/
    │       │   ├── (common)/
    │       │   ├── usecase-a/
    │       │   └── usecase-b/
    │       └── ...
    ├── packages/
    │   └── simcore/                  # shared domain logic (Python)
    │       ├── pyproject.toml
    │       └── src/simcore/
    │           ├── idf/
    │           ├── weather/
    │           ├── runner/
    │           ├── caching/
    │           ├── results/
    │           └── __init__.py
    ├── assets/                       # versioned, stable inputs only
    │   ├── idf_templates/
    │   │   ├── hospital/
    │   │   └── ...
    │   └── weather/
    │       └── lund.epw
    ├── var/                          # NOT versioned (generated/runtime)
    │   ├── output/
    │   ├── cache/
    │   └── modified_idf/
    └── .github/workflows/