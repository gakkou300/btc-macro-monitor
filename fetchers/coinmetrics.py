import logging
import requests
from datetime import date, timedelta, datetime, timezone

logger = logging.getLogger(__name__)

BASE = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"


def _fetch(metrics: str) -> dict:
    """Fetch the latest BTC metric(s) from CoinMetrics Community API (no key required)."""
    # Go back 3 days to guarantee data exists (flash data may lag 1-2 days)
    end = date.today()
    start = end - timedelta(days=3)
    resp = requests.get(
        BASE,
        params={
            "assets": "btc",
            "metrics": metrics,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"CoinMetrics {metrics} returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
    rows = resp.json().get("data", [])
    if not rows:
        raise ValueError(f"CoinMetrics returned empty data for {metrics}")
    return rows[-1]  # most recent entry


# ── 取引所BTC保有量 ────────────────────────────────────────────────────────────

def fetch_exchange_supply() -> dict:
    """
    Fetch total BTC held on exchanges from CoinMetrics Community API.
    Metric: SplyExNtv (Supply held by exchanges, native units = BTC).

    Returns:
        dict with: key, name, value (BTC float), date, url
    """
    row = _fetch("SplyExNtv")
    value = float(row["SplyExNtv"])
    data_date = row["time"][:10]  # YYYY-MM-DD

    return {
        "key": "btc_exchange",
        "name": "取引所BTC保有量",
        "value": value,
        "data_date": data_date,
        "url": "https://coinmetrics.io/network-data/",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ── 取引所BTC純流入（全取引所合計） ─────────────────────────────────────────────

def fetch_exchange_netflow() -> dict:
    """
    Fetch BTC net flow into all exchanges from CoinMetrics Community API.
    Net flow = FlowInExNtv - FlowOutExNtv (positive = net inflow = bearish signal).

    Returns:
        dict with: key, name, value (BTC float, net inflow), date, url
    """
    row = _fetch("FlowInExNtv,FlowOutExNtv")
    inflow = float(row["FlowInExNtv"])
    outflow = float(row["FlowOutExNtv"])
    net = inflow - outflow
    data_date = row["time"][:10]

    return {
        "key": "etf_flow",          # detector の既存キーを流用
        "name": "取引所BTC純流入（全取引所）",
        "value": net,
        "date": data_date,
        "url": "https://coinmetrics.io/network-data/",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
