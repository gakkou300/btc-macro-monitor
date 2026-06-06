import os
import logging
import requests

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# FRED から取得する全系列。
# "unit" は数値変化通知（Phase 3 の流動性指標）でのみ使用する任意フィールド。
SERIES: dict[str, dict] = {
    # ── Phase 1: マクロ経済 ──
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
    "unrate": {
        "id": "UNRATE",
        "name": "失業率",
        "url": "https://fred.stlouisfed.org/series/UNRATE",
    },
    "icsa": {
        "id": "ICSA",
        "name": "新規失業保険申請件数",
        "url": "https://fred.stlouisfed.org/series/ICSA",
    },
    # ── Phase 3: 流動性 ──
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


def fetch_fred_series(key: str) -> dict:
    """
    Fetch the latest observation for any FRED series.

    Args:
        key: one of 'cpi', 'nfp', 'unrate', 'icsa', 'm2sl', 'walcl'

    Returns:
        dict with keys: key, name, unit, date, value (float), url
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
    # FRED returns "." for missing values — treat as an error rather than crashing.
    try:
        value = float(obs["value"])
    except (ValueError, TypeError):
        raise ValueError(f"FRED returned non-numeric value '{obs['value']}' for {info['id']}")

    return {
        "key": key,
        "name": info["name"],
        "unit": info.get("unit"),
        "date": obs["date"],
        "value": value,
        "url": info["url"],
    }
