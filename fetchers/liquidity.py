import os
import logging
import requests

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES: dict[str, dict] = {
    "m2sl": {
        "id": "M2SL",
        "name": "M2マネーサプライ",
        "unit": "十億ドル",
        "url": "https://fred.stlouisfed.org/series/M2SL",
    },
    "walcl": {
        "id": "WALCL",
        "name": "FRBバランスシート",
        "unit": "百万ドル",
        "url": "https://fred.stlouisfed.org/series/WALCL",
    },
}


def fetch_liquidity(key: str) -> dict:
    """
    Fetch the latest FRED liquidity indicator (M2SL or WALCL).

    Args:
        key: 'm2sl' or 'walcl'

    Returns:
        dict with: key, name, unit, date, value (float), url
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
    observations = resp.json().get("observations", [])

    if not observations:
        raise ValueError(f"No observations returned for {info['id']}")

    obs = observations[0]
    return {
        "key": key,
        "name": info["name"],
        "unit": info["unit"],
        "date": obs["date"],
        "value": float(obs["value"]),
        "url": info["url"],
    }
