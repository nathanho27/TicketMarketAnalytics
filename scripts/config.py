"""Shared settings for collection and conversion.

Every script imports from here, so cities, dates and folders are defined once.
"""
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOG_DIR = PROJECT_ROOT / "logs"

# The 25 largest U.S. cities by Census Vintage 2025 population estimates
# (SUB-EST2025, incorporated places). Each search point is the city hall
# address geocoded with the Census Geocoder on 2026-11-10 (Nashville: 100 James
# Robertson Pkwy next to the Metro Courthouse; Boston: 1 City Hall Ave, about
# 0.3 mi from City Hall Plaza). LA and NYC keep the pilot's City Hall points.
# "states" lists the states whose census tracts fall inside the 25-mile circle;
# a venue listed elsewhere gets a data-quality flag.
CITIES = {
    "new_york": {"name": "New York", "lat": 40.7127, "lon": -74.0059, "states": ["NY", "NJ"]},
    "los_angeles": {"name": "Los Angeles", "lat": 34.0537, "lon": -118.2428, "states": ["CA"]},
    "chicago": {"name": "Chicago", "lat": 41.8834, "lon": -87.6323, "states": ["IL", "IN"]},
    "houston": {"name": "Houston", "lat": 29.7607, "lon": -95.3695, "states": ["TX"]},
    "phoenix": {"name": "Phoenix", "lat": 33.4483, "lon": -112.0764, "states": ["AZ"]},
    "philadelphia": {"name": "Philadelphia", "lat": 39.9533, "lon": -75.1634, "states": ["PA", "NJ", "DE"]},
    "san_antonio": {"name": "San Antonio", "lat": 29.4248, "lon": -98.4947, "states": ["TX"]},
    "san_diego": {"name": "San Diego", "lat": 32.7168, "lon": -117.1628, "states": ["CA"]},
    "dallas": {"name": "Dallas", "lat": 32.7767, "lon": -96.7958, "states": ["TX"]},
    "fort_worth": {"name": "Fort Worth", "lat": 32.7484, "lon": -97.3303, "states": ["TX"]},
    "jacksonville": {"name": "Jacksonville", "lat": 30.3297, "lon": -81.6588, "states": ["FL"]},
    "austin": {"name": "Austin", "lat": 30.2650, "lon": -97.7467, "states": ["TX"]},
    "san_jose": {"name": "San Jose", "lat": 37.3382, "lon": -121.8862, "states": ["CA"]},
    "charlotte": {"name": "Charlotte", "lat": 35.2220, "lon": -80.8392, "states": ["NC", "SC"]},
    "columbus": {"name": "Columbus", "lat": 39.9621, "lon": -83.0025, "states": ["OH"]},
    "indianapolis": {"name": "Indianapolis", "lat": 39.7671, "lon": -86.1544, "states": ["IN"]},
    "san_francisco": {"name": "San Francisco", "lat": 37.7785, "lon": -122.4183, "states": ["CA"]},
    "seattle": {"name": "Seattle", "lat": 47.6033, "lon": -122.3303, "states": ["WA"]},
    "denver": {"name": "Denver", "lat": 39.7390, "lon": -104.9903, "states": ["CO"]},
    "nashville": {"name": "Nashville", "lat": 36.1682, "lon": -86.7775, "states": ["TN"]},
    "oklahoma_city": {"name": "Oklahoma City", "lat": 35.4686, "lon": -97.5212, "states": ["OK"]},
    "washington": {"name": "Washington", "lat": 38.8954, "lon": -77.0302, "states": ["DC", "MD", "VA"]},
    "el_paso": {"name": "El Paso", "lat": 31.7613, "lon": -106.4852, "states": ["TX", "NM"]},
    "las_vegas": {"name": "Las Vegas", "lat": 36.1671, "lon": -115.1493, "states": ["NV"]},
    "boston": {"name": "Boston", "lat": 42.3578, "lon": -71.0592, "states": ["MA"]},
}
RADIUS_MILES = 25
COUNTRY_CODE = "US"  # keeps Mexican venues near El Paso and San Diego out

# Event window for the full collection (local event dates, inclusive).
EVENT_START_DATE = date(2026, 11, 12)
EVENT_END_DATE = date(2027, 1, 31)

# Pilot settings (2026-11-02 LA/NYC test), kept so the pilot and probes still run.
TEST_CITIES = {k: CITIES[k] for k in ("los_angeles", "new_york")}
TEST_START_DATE = date(2026, 11, 6)
TEST_END_DATE = date(2026, 11, 10)

# Ticketmaster segment IDs (from the Discovery API classifications endpoint).
TICKETMASTER_SEGMENTS = {
    "music": "KZFzniwnSyZfZ7v7nJ",
    "sports": "KZFzniwnSyZfZ7v7nE",
}


def date_windows(start, end, days=7):
    """Split start..end (inclusive) into consecutive windows of up to `days` days."""
    windows, current = [], start
    while current <= end:
        last = min(current + timedelta(days=days - 1), end)
        windows.append((current, last))
        current = last + timedelta(days=1)
    return windows


def test_dates():
    """Return every date from TEST_START_DATE to TEST_END_DATE, inclusive (pilot)."""
    days = (TEST_END_DATE - TEST_START_DATE).days
    return [TEST_START_DATE + timedelta(days=i) for i in range(days + 1)]
