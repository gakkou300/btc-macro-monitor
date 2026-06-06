import argparse
import logging
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from fetchers.fred import fetch_fred_series, SERIES as FRED_SERIES
from fetchers.fomc import fetch_latest_fomc
from fetchers.market import fetch_market, TICKERS as MARKET_TICKERS
from fetchers.sec import fetch_sec_filings
from fetchers.stablecoin import fetch_stablecoin, STABLECOINS
from fetchers.coinmetrics import fetch_exchange_supply, fetch_exchange_netflow
from fetchers.glassnode import (
    fetch_fear_greed, fetch_funding_rate,
    get_fear_greed_zone,
)
import detector
import summarizer
import notifier

MARKET_KEYS = ["dxy", "us10y", "nasdaq", "vix"]
STABLECOIN_KEYS = ["usdt", "usdc"]
LIQUIDITY_KEYS = ["m2sl", "walcl"]


# ── Phase 1: FRED ─────────────────────────────────────────────────────────────

def run_fred(key: str) -> None:
    try:
        data = fetch_fred_series(key)
        if detector.is_new_fred(key, data):
            logger.info(f"[{key.upper()}] New data: {data['date']} / {data['value']}")
            result = summarizer.summarize(data)
            notifier.notify(data["name"], result, data["url"], data["date"])
            detector.update_fred(key, data)
        else:
            logger.info(f"[{key.upper()}] No new data (latest: {data['date']})")
    except Exception as e:
        logger.error(f"[{key.upper()}] Error: {e}")
        try:
            notifier.notify_error(FRED_SERIES[key]["name"])
        except Exception:
            pass


# ── Phase 1: FOMC ─────────────────────────────────────────────────────────────

def run_fomc() -> None:
    try:
        data = fetch_latest_fomc()
        if data is None:
            logger.warning("[FOMC] No documents found on calendar page")
            return
        if detector.is_new_fomc(data):
            logger.info(f"[FOMC] New document: {data['url']}")
            result = summarizer.summarize(data)
            notifier.notify(data["name"], result, data["url"], data["date"])
            detector.update_fomc(data)
        else:
            logger.info(f"[FOMC] No new document (latest: {data['date']})")
    except Exception as e:
        logger.error(f"[FOMC] Error: {e}")
        try:
            notifier.notify_error("FOMC議事録/声明文")
        except Exception:
            pass


# ── Phase 2: Market ───────────────────────────────────────────────────────────

def run_market(key: str) -> None:
    try:
        data = fetch_market(key)
        result = detector.check_market_change(key, data["value"])

        if not result["changed"]:
            logger.info(
                f"[{key.upper()}] No significant change "
                f"(value: {data['value']:.4f}, change: {result['change_pct']:+.2f}%)"
            )
            return

        logger.info(
            f"[{key.upper()}] Significant change: "
            f"{result['change_pct']:+.2f}% (value: {data['value']:.4f})"
        )
        data["prev_value"] = result["prev_value"]
        data["change_pct"] = result["change_pct"]
        data["change_abs"] = result["change_abs"]

        indicator_name = data["name"]
        if key == "vix" and result["priority"]:
            indicator_name = f"🚨 {indicator_name}（急騰警戒）"

        summary = summarizer.summarize(data)
        notifier.notify(indicator_name, summary, data["url"], data["timestamp"])
        detector.update_market(key, data["value"])

    except Exception as e:
        logger.error(f"[{key.upper()}] Error: {e}")
        try:
            notifier.notify_error(MARKET_TICKERS[key]["name"])
        except Exception:
            pass


# ── Phase 3: SEC ──────────────────────────────────────────────────────────────

def run_sec() -> None:
    try:
        filings = fetch_sec_filings()
        new_filings = detector.get_unseen_sec_filings(filings)

        if not new_filings:
            logger.info(f"[SEC] No new filings ({len(filings)} checked)")
            return

        logger.info(f"[SEC] {len(new_filings)} new filing(s) found")
        for filing in new_filings:
            try:
                summary = summarizer.summarize(filing)
            except Exception as e:
                logger.warning(f"[SEC] Summarizer failed for {filing['title']}: {e}")
                summary = None
            notifier.notify_sec(filing, summary)

        detector.update_sec(new_filings)

    except Exception as e:
        logger.error(f"[SEC] Error: {e}")
        try:
            notifier.notify_error("SEC EDGAR")
        except Exception:
            pass


# ── Phase 3: Stablecoin & BTC exchange holdings ───────────────────────────────

def run_stablecoin() -> None:
    # USDT / USDC via CoinGecko
    for key in STABLECOIN_KEYS:
        try:
            data = fetch_stablecoin(key)
            result = detector.check_stablecoin_change(key, data["value"])

            if result["changed"]:
                logger.info(f"[{key.upper()}] Supply change: {result['change_pct']:+.2f}%")
                notifier.notify_change(
                    data["name"],
                    data["value"],
                    result["prev_value"],
                    result["change_pct"],
                    data["timestamp"],
                    unit=data["symbol"],
                )
                detector.update_stablecoin(key, data["value"])
            else:
                logger.info(
                    f"[{key.upper()}] No significant change ({result['change_pct']:+.2f}%)"
                )
        except Exception as e:
            logger.error(f"[{key.upper()}] Error: {e}")
            try:
                notifier.notify_error(STABLECOINS[key]["name"])
            except Exception:
                pass
        time.sleep(2)  # CoinGecko free-tier rate limit

    # BTC exchange holdings via CoinMetrics Community（無料・キー不要）
    try:
        data = fetch_exchange_supply()
        result = detector.check_btc_exchange_change(data["value"])

        if result["changed"]:
            logger.info(f"[BTC_EXCHANGE] Holdings change: {result['change_pct']:+.2f}%")
            notifier.notify_change(
                data["name"],
                data["value"],
                result["prev_value"],
                result["change_pct"],
                data["timestamp"],
                unit="BTC",
            )
            detector.update_stablecoin("btc_exchange", data["value"])
        else:
            logger.info(
                f"[BTC_EXCHANGE] No significant change ({result['change_pct']:+.2f}%)"
            )
    except Exception as e:
        logger.error(f"[BTC_EXCHANGE] Error: {e}")
        try:
            notifier.notify_error("取引所BTC保有量")
        except Exception:
            pass


# ── Phase 3: Liquidity (M2 / WALCL) ──────────────────────────────────────────

def run_liquidity() -> None:
    for key in LIQUIDITY_KEYS:
        try:
            data = fetch_fred_series(key)
            result = detector.check_liquidity_change(key, data["date"], data["value"])

            if result["changed"]:
                logger.info(
                    f"[{key.upper()}] New FRED data: {data['date']} / "
                    f"change: {result['change_pct']:+.2f}%"
                )
                notifier.notify_change(
                    data["name"],
                    data["value"],
                    result["prev_value"],
                    result["change_pct"],
                    data["date"],
                    unit=data["unit"],
                )
                detector.update_liquidity(key, data["date"], data["value"])
            else:
                logger.info(
                    f"[{key.upper()}] No new data or change too small (latest: {data['date']})"
                )
        except Exception as e:
            logger.error(f"[{key.upper()}] Error: {e}")
            try:
                notifier.notify_error(FRED_SERIES[key]["name"])
            except Exception:
                pass


# ── Phase 4: Glassnode on-chain ───────────────────────────────────────────────

def run_glassnode() -> None:
    # --- Fear & Greed Index ---
    try:
        data = fetch_fear_greed()
        result = detector.check_fear_greed_change(data["value"], data["zone"])

        if result["changed"]:
            logger.info(
                f"[FEAR_GREED] Zone change: {result['prev_zone']} → {data['zone']} "
                f"(value: {data['value']:.0f})"
            )
            # Enrich data with prev zone label for summarizer
            _, prev_zone_label = get_fear_greed_zone(result["prev_value"] or 0)
            data["prev_zone_label"] = prev_zone_label
            summary = summarizer.summarize(data)
            notifier.notify(data["name"], summary, data["url"], data["date"])

        detector.update_fear_greed(data["value"], data["zone"], data["date"])

        if not result["changed"]:
            logger.info(
                f"[FEAR_GREED] No zone change ({data['zone']}, value: {data['value']:.0f})"
            )
    except Exception as e:
        logger.error(f"[FEAR_GREED] Error: {e}")
        try:
            notifier.notify_error("恐怖&強欲指数")
        except Exception:
            pass

    # --- 取引所BTC純流入（CoinMetrics Community） ---
    try:
        data = fetch_exchange_netflow()
        result = detector.check_etf_flow_change(data["date"])

        if result["changed"]:
            logger.info(
                f"[EXCHANGE_FLOW] New daily data: {data['date']} / {data['value']:+,.2f} BTC"
            )
            summary = summarizer.summarize(data)
            notifier.notify(data["name"], summary, data["url"], data["date"])
            detector.update_etf_flow(data["date"], data["value"])
        else:
            logger.info(f"[EXCHANGE_FLOW] No new data (latest: {data['date']})")
    except Exception as e:
        logger.error(f"[EXCHANGE_FLOW] Error: {e}")
        try:
            notifier.notify_error("取引所BTC純流入")
        except Exception:
            pass

    # --- Funding Rate (Perpetual) ---
    try:
        data = fetch_funding_rate()
        result = detector.check_funding_rate_change(data["value"])

        if result["changed"]:
            logger.info(
                f"[FUNDING_RATE] Significant change: {result['prev_value']:+.6f} → "
                f"{data['value']:+.6f}"
            )
            data["prev_value"] = result["prev_value"]
            data["sign_changed"] = result.get("sign_changed", False)
            data["threshold_crossed"] = result.get("threshold_crossed", False)
            summary = summarizer.summarize(data)
            notifier.notify(data["name"], summary, data["url"], data["date"])

        detector.update_funding_rate(data["value"])

        if not result["changed"]:
            logger.info(
                f"[FUNDING_RATE] No significant change (value: {data['value']:+.6f})"
            )
    except Exception as e:
        logger.error(f"[FUNDING_RATE] Error: {e}")
        try:
            notifier.notify_error("BTCパーペチュアルFunding Rate")
        except Exception:
            pass


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="BTC Macro Monitor")
    parser.add_argument(
        "--mode",
        default="monitor",
        choices=["monitor", "sec", "stablecoin", "liquidity", "glassnode"],
        help="Which indicator group to run (default: monitor = Phase 1+2)",
    )
    args = parser.parse_args()

    logger.info(f"=== BTC Monitor start (mode: {args.mode}) ===")

    if args.mode == "monitor":
        run_fred("cpi")
        run_fred("nfp")
        run_fred("unrate")
        run_fred("icsa")
        run_fomc()
        for key in MARKET_KEYS:
            run_market(key)
    elif args.mode == "sec":
        run_sec()
    elif args.mode == "stablecoin":
        run_stablecoin()
    elif args.mode == "liquidity":
        run_liquidity()
    elif args.mode == "glassnode":
        run_glassnode()

    logger.info("=== BTC Monitor done ===")


if __name__ == "__main__":
    main()
