# Cloud Computing IBM Cloud Earthquake Dataset

A runnable Flask project for exploring live USGS earthquake data with a CSV fallback (`all_month.csv`).

This repository now runs locally without IBM DB2 dependencies and provides a web UI for common earthquake analytics tasks.

## Features

The app supports:

1. **Magnitude threshold search** – count/list earthquakes above a given magnitude.
2. **Magnitude + date range search** – filter earthquakes by magnitude band and date interval.
3. **Distance search** – find earthquakes within a radius (km) from a latitude/longitude point.
4. **Day vs night count** – estimate local time from longitude and split earthquake counts.
5. **Grid-based clustering** – count earthquakes per latitude/longitude slab region.

## Project structure

- `main.py` – Flask app and analytics logic.
- `all_month.csv` – source earthquake dataset.
- `templates/` – HTML pages for input and result views.
- `requirements.txt` – Python dependencies.
- `Procfile` / `manifest.yml` – deployment metadata from original project.

## Requirements

- Python 3.10+ (works on modern Python 3 versions)
- pip

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally

```bash
python main.py
```

App runs at:

- `http://127.0.0.1:5000`

You can also set a custom port:

```bash
PORT=8080 python main.py
```

## Endpoints

- `GET /` – dashboard with all forms.
- `POST /countall` – magnitude threshold query.
- `POST /getrange` – magnitude/date range query.
- `POST /getdistance` – distance query.
- `POST /night` – day/night split.
- `POST /clustring` – slab/grid clustering.

## Notes on reconstruction

The original code referenced unavailable IBM Cloud DB credentials and mixed database drivers (`pyodbc`, `ibm_db`) which made it non-runnable as-is. The app now attempts to load the USGS live "all month" GeoJSON feed at startup and falls back to the bundled CSV when live data is unavailable, while preserving the original workflows and routes.

## Quick validation

After starting the app, open `/` and run each form once. You should see table-based results and counts returned by each operation.
