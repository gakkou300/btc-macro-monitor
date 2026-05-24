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
import detector
import summarizer
import notifier


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


def main() -> None:
    logger.info("=== BTC Monitor start ===")
    run_fred("cpi")
    run_fred("nfp")
    run_fomc()
    logger.info("=== BTC Monitor done ===")


if __name__ == "__main__":
    main()
