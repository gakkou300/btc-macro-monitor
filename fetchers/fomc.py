import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.federalreserve.gov"
CALENDAR_URL = f"{BASE_URL}/monetarypolicy/fomccalendars.htm"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BtcMonitor/1.0)"}
CONTENT_MAX_CHARS = 8000


def fetch_latest_fomc() -> dict | None:
    """
    Scrape the FOMC calendar page and return the most recent Minutes or Statement.

    Returns:
        dict with keys: url, date, title, name, content
        None if no documents found.
    """
    resp = requests.get(CALENDAR_URL, timeout=30, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    documents = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        date_str = _extract_date(href)
        if not date_str:
            continue

        if "fomcminutes" in href:
            doc_type = "Minutes"
        elif re.search(r"pressreleases/monetary\d{8}a\.htm", href):
            doc_type = "Statement"
        else:
            continue

        full_url = BASE_URL + href if href.startswith("/") else href
        documents.append({"url": full_url, "date": date_str, "type": doc_type})

    if not documents:
        logger.warning("No FOMC documents found on calendar page")
        return None

    latest = max(documents, key=lambda d: d["date"])
    content = _fetch_content(latest["url"])

    return {
        "url": latest["url"],
        "date": latest["date"],
        "title": f"FOMC {latest['type']} ({latest['date']})",
        "name": "FOMC議事録/声明文",
        "content": content,
    }


def _extract_date(href: str) -> str | None:
    """Extract YYYYMMDD from href and convert to YYYY-MM-DD."""
    m = re.search(r"(\d{8})", href)
    if m:
        raw = m.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return None


def _fetch_content(url: str) -> str | None:
    """Fetch and extract main text content from an FOMC document page."""
    try:
        resp = requests.get(url, timeout=30, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try common content containers used on federalreserve.gov
        for selector in ["#article", ".col-xs-12.col-sm-8", "#leftText", "article", "main"]:
            el = soup.select_one(selector)
            if el:
                return el.get_text(separator="\n", strip=True)[:CONTENT_MAX_CHARS]

        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)[:CONTENT_MAX_CHARS]

        return None
    except Exception as e:
        logger.warning(f"Could not fetch FOMC page content from {url}: {e}")
        return None
