import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from fetchers.fred import fetch_fred_series
from fetchers.fomc import fetch_latest_fomc
from fetchers.market import fetch_market, TICKERS as MARKET_TICKERS
import detector
import summarizer
import notifier

MARKET_KEYS = ["dxy", "us10y", "nasdaq", "vix"]


# ── Phase 1: FRED ─────────────────────────────────────────────────────────────

def run_fred(key: str) -> None:
    name_map = {
        "cpi": "CPI (消費者物価指数)",
        "nfp": "NFP (非農業部門雇用者数)",
    }
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
            notifier.notify_error(name_map[key])
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
            f"[{key.upper()}] Significant change detected: "
            f"{result['change_pct']:+.2f}% (value: {data['value']:.4f})"
        )

        # Pass change context to summarizer
        data["prev_value"] = result["prev_value"]
        data["change_pct"] = result["change_pct"]
        data["change_abs"] = result["change_abs"]

        # VIX priority alert
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


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("=== BTC Monitor start ===")

    # Phase 1
    run_fred("cpi")
    run_fred("nfp")
    run_fomc()

    # Phase 2
    for key in MARKET_KEYS:
        run_market(key)

    logger.info("=== BTC Monitor done ===")


if __name__ == "__main__":
    main()
