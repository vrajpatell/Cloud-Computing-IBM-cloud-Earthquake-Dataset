from __future__ import annotations

import csv
import datetime as dt
import json
import math
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from flask import Flask, render_template, request

app = Flask(__name__)
PORT = int(os.getenv("PORT", 5000))
DATA_FILE = Path(__file__).with_name("all_month.csv")
USGS_ALL_MONTH_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
)


def _to_float(value: str | None, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except ValueError:
        return default


def _parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%m/%d/%Y").date()


def _parse_time(value: str) -> dt.time:
    return dt.datetime.strptime(value, "%H:%M:%S").time()


def load_earthquakes() -> list[dict[str, Any]]:
    try:
        return load_live_earthquakes()
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return load_csv_earthquakes()


def load_live_earthquakes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with urlopen(USGS_ALL_MONTH_URL, timeout=15) as response:
        payload = json.load(response)

    features = payload.get("features", [])
    for feature in features:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [0.0, 0.0, 0.0])
        if len(coordinates) < 3:
            coordinates = [0.0, 0.0, 0.0]

        event_time = dt.datetime.fromtimestamp(
            _to_float(properties.get("time")) / 1000,
            tz=dt.timezone.utc,
        )
        rows.append(
            {
                "ID": feature.get("id", ""),
                "DATE": event_time.date(),
                "TIME": event_time.time().replace(tzinfo=None),
                "LATITUDE": _to_float(coordinates[1]),
                "LONGITUDE": _to_float(coordinates[0]),
                "DEPTH": _to_float(coordinates[2]),
                "MAG": _to_float(properties.get("mag")),
                "PLACE": properties.get("place", ""),
            }
        )
    return rows


def load_csv_earthquakes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with DATA_FILE.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for raw in reader:
            rows.append(
                {
                    "ID": raw.get("id", ""),
                    "DATE": _parse_date(raw.get("date", "1/1/1970")),
                    "TIME": _parse_time(raw.get("time", "00:00:00")),
                    "LATITUDE": _to_float(raw.get("latitude")),
                    "LONGITUDE": _to_float(raw.get("longitude")),
                    "DEPTH": _to_float(raw.get("depth")),
                    "MAG": _to_float(raw.get("mag")),
                    "PLACE": raw.get("place", ""),
                }
            )
    return rows


EARTHQUAKES = load_earthquakes()


@app.route("/")
def index():
    return render_template("form.html", total=len(EARTHQUAKES))


@app.route("/countall", methods=["GET", "POST"])
def countall():
    if request.method == "POST":
        min_mag = _to_float(request.form.get("mag"), 0.0)
        rows = [row for row in EARTHQUAKES if row["MAG"] > min_mag]
        return render_template("cresult.html", rows=rows, count=len(rows))
    return render_template("form.html", total=len(EARTHQUAKES))


@app.route("/getrange", methods=["POST"])
def getrange():
    uppermag = _to_float(request.form.get("uppermag"))
    lowermag = _to_float(request.form.get("lowermag"))
    startdate = dt.datetime.strptime(request.form["startdate"], "%Y-%m-%d").date()
    enddate = dt.datetime.strptime(request.form["enddate"], "%Y-%m-%d").date()

    rows = [
        row
        for row in EARTHQUAKES
        if lowermag <= row["MAG"] <= uppermag and startdate <= row["DATE"] <= enddate
    ]
    return render_template("rangeresult.html", rows=rows, count=len(rows))


@app.route("/getdistance", methods=["POST"])
def getdistance():
    lati = _to_float(request.form.get("lati"))
    longi = _to_float(request.form.get("longi"))
    max_distance_km = _to_float(request.form.get("dis"))

    radius = 6371.0
    nearby: list[dict[str, Any]] = []
    for row in EARTHQUAKES:
        dlat = math.radians(row["LATITUDE"] - lati)
        dlon = math.radians(row["LONGITUDE"] - longi)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lati))
            * math.cos(math.radians(row["LATITUDE"]))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = radius * c
        if distance < max_distance_km:
            nearby.append(row)

    return render_template("distance.html", r1=nearby, count=len(nearby))


@app.route("/night", methods=["POST"])
def night():
    min_mag = _to_float(request.form.get("magni"), 0.0)
    rows = [row for row in EARTHQUAKES if row["MAG"] > min_mag]

    day_count = 0
    night_count = 0
    for row in rows:
        tdiff = int(row["LONGITUDE"] * 24 / 360)
        local_dt = dt.datetime.combine(row["DATE"], row["TIME"]) - dt.timedelta(hours=tdiff)
        if local_dt.time().hour < 8 or local_dt.time().hour > 20:
            night_count += 1
        else:
            day_count += 1

    return render_template("daynight.html", N=night_count, D=day_count)


@app.route("/clustring", methods=["POST"])
def clustring():
    lati1 = int(_to_float(request.form.get("lati1")))
    long1 = int(_to_float(request.form.get("long1")))
    lati2 = int(_to_float(request.form.get("lati2")))
    long2 = int(_to_float(request.form.get("long2")))
    kcul = max(int(_to_float(request.form.get("kcul"), 1.0)), 1)

    lat_step = -kcul if lati1 > lati2 else kcul
    lon_step = -kcul if long1 > long2 else kcul

    latrange: list[int] = []
    lonrange: list[int] = []
    countl: list[int] = []

    for lat in range(lati1, lati2, lat_step):
        for lon in range(long1, long2, lon_step):
            next_lat = lat + lat_step
            next_lon = lon + lon_step
            lat_low, lat_high = sorted((lat, next_lat))
            lon_low, lon_high = sorted((lon, next_lon))

            count = sum(
                1
                for row in EARTHQUAKES
                if lat_low <= row["LATITUDE"] <= lat_high
                and lon_low <= row["LONGITUDE"] <= lon_high
            )
            latrange.append(lat)
            lonrange.append(lon)
            countl.append(count)

    return render_template(
        "clustering.html",
        lengthcounter=len(latrange),
        latrange=latrange,
        lonrange=lonrange,
        countl=countl,
        counter=sum(countl),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
