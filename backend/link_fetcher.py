# link_fetcher.py – Live official government link scraper

"""Utility to fetch official .gov.in links for a given bureaucratic process.

The function first checks a curated map of known links (fast, offline). If the
topic is not found it falls back to a DuckDuckGo search limited to Indian
government domains. Results are cached in-memory for the lifetime of the
process to avoid repeated network calls.
"""

import re
from functools import lru_cache
from typing import List, Dict

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

# Curated fallback links for the most common processes
KNOWN_LINKS: Dict[str, List[Dict[str, str]]] = {
    "passport": [
        {"title": "Passport Seva Online Portal", "url": "https://www.passportindia.gov.in/AppOnlineProject/welcomeLink"},
        {"title": "Download Passport Application Form‑1", "url": "https://www.passportindia.gov.in/AppOnlineProject/pdf/GEP_Booklet.pdf"},
        {"title": "Appointment Booking — Passport Seva", "url": "https://portal2.passportindia.gov.in/AppOnlineProject/online/redirectToLandingPage"},
    ],
    "birth_certificate": [
        {"title": "CRVSUP – Civil Registration System", "url": "https://crvsup.nhp.gov.in/"},
        {"title": "e‑District Portal", "url": "https://edistrict.gov.in/"},
    ],
    # Add more curated topics as required
}

# Regex to ensure we only return "official" government domains
_GOV_DOMAINS = re.compile(r"(gov\.in|nic\.in|india\.gov\.in|uidai\.gov|parivahan\.gov|mca\.gov)", re.IGNORECASE)

@lru_cache(maxsize=128)
def get_official_links(topic: str) -> List[Dict[str, str]]:
    """Return a list of ``{"title": ..., "url": ...}`` dicts.

    1. Look up the *topic* in ``KNOWN_LINKS`` (case‑insensitive, partial match).
    2. If not found, perform a DuckDuckGo search limited to Indian government
       sites. Returns up to 3 results.
    """
    topic_lower = topic.lower()

    # 1️⃣ Curated map lookup
    for key, links in KNOWN_LINKS.items():
        if key in topic_lower or any(word in topic_lower for word in key.split("_")):
            return links

    # 2️⃣ DuckDuckGo fallback (requires internet)
    if DDGS_AVAILABLE:
        try:
            results: List[Dict[str, str]] = []
            query = f"{topic} official India government portal site:gov.in OR site:nic.in"
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    href = r.get("href", "")
                    if _GOV_DOMAINS.search(href):
                        results.append({"title": r.get("title", href), "url": href})
                    if len(results) >= 3:
                        break
            if results:
                return results
        except Exception as e:
            print(f"[LinkFetcher DDG Error] {e}")

    # 3️⃣ Generic fallback – static suggestions
    return [
        {"title": f"Search on India.gov.in for {topic}", "url": f"https://www.india.gov.in/topics/{topic.replace(' ', '-')}"},
        {"title": "DigiLocker – Official Documents", "url": "https://www.digilocker.gov.in/"},
        {"title": "Umang App – All Government Services", "url": "https://web.umang.gov.in/"},
    ]
