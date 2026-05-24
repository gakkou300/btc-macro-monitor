import os
import logging
import requests

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES = {
    "cpi": {
        "id": "CPIAUCSL",
        "name": "CPI (消費者物価指数)",
        "url": "https://fred.stlouisfed.org/series/CPIAUCSL",
    },
    "nfp": {
        "id": "PAYEMS",
        "name": "NFP (非農業部門雇用者数)",
        "url": "https://fred.stlouisfed.org/series/PAYEMS",
    },
}


def fetch_fred_series(key: str) -> dict:
    """
    Fetch the latest observation for a FRED series.

    Args:
        key: 'cpi' or 'nfp'

    Returns:
        dict with keys: key, name, date, value, url
    """
    info = SERIES[key]
    params = {
        "series_id": info["id"],
        "api_key": os.environ["FRED_API_KEY"],
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    resp = requests.get(FRED_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    observations = data.get("observations", [])
    if not observations:
        raise ValueError(f"No observations returned for {info['id']}")

    obs = observations[0]
    return {
        "key": key,
        "name": info["name"],
        "date": obs["date"],
        "value": obs["value"],
        "url": info["url"],
    }
