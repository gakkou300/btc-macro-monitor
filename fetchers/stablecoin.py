import os
import time
import logging
import requests
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
# NOTE: Coinglass endpoint for exchange BTC reserves.
# Verify at https://docs.coinglass.com if response format changes.
COINGLASS_BASE = "https://open-api.coinglass.com/public/v2"

STABLECOINS: dict[str, dict] = {
    "usdt": {
        "id": "tether",
        "name": "USDT供給量",
        "symbol": "USDT",
        "url": "https://www.coingecko.com/en/coins/tether",
    },
    "usdc": {
        "id": "usd-coin",
        "name": "USDC供給量",
        "symbol": "USDC",
        "url": "https://www.coingecko.com/en/coins/usd-coin",
    },
}


def fetch_stablecoin(key: str) -> dict:
    """
    Fetch stablecoin circulating supply from CoinGecko.

    Args:
        key: 'usdt' or 'usdc'

    Returns:
        dict with: key, name, symbol, value (float), url, timestamp
    """
    info = STABLECOINS[key]
    headers = {}
    api_key = os.environ.get("COINGECKO_API_KEY")
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    resp = requests.get(
        f"{COINGECKO_BASE}/coins/{info['id']}",
        params={
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    supply = float(data["market_data"]["circulating_supply"])

    return {
        "key": key,
        "name": info["name"],
        "symbol": info["symbol"],
        "value": supply,
        "url": info["url"],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def fetch_btc_exchange_holdings() -> dict:
    """
    Fetch total BTC holdings across exchanges via Coinglass API.
    Sums balance across all listed exchanges.

    Returns:
        dict with: key, name, value (total BTC float), url, timestamp
    """
    api_key = os.environ["COINGLASS_API_KEY"]
    resp = requests.get(
        f"{COINGLASS_BASE}/indicator/exchange_list_BTC",
        headers={"coinglassSecret": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != "0":
        raise ValueError(f"Coinglass API error: {data.get('msg', 'unknown error')}")

    exchange_list = data.get("data", [])
    total_btc = sum(
        float(ex["balance"])
        for ex in exchange_list
        if ex.get("balance") is not None
    )

    return {
        "key": "btc_exchange",
        "name": "取引所BTC保有量",
        "symbol": "BTC",
        "value": total_btc,
        "url": "https://www.coinglass.com/BitcoinTotalBalance",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
