"""
Flipkart scraper — used as fallback when Amazon blocks.
Uses direct requests + BeautifulSoup only (no ScraperAPI).
Returns same shape as Amazon: name, price, rating, reviews, avg_sentiment, etc.
"""
import time
import random
import re
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob  # type: ignore[reportMissingImports]

# Chrome-like headers for direct scraping
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.flipkart.com/",
    "Connection": "keep-alive",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Sec-Ch-Ua": '"Chromium";v="133", "Not-A.Brand";v="8", "Google Chrome";v="133"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}

BASE_URL = "https://www.flipkart.com"


def _http_get(url: str) -> requests.Response:
    """Direct request to Flipkart; parsed with BeautifulSoup."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp


def scrape_flipkart_product(flipkart_url_or_pid: str, asin_for_key: str) -> dict:
    """
    Scrape a Flipkart product by full URL or by pid (e.g. itm4a0093df4a3d7).
    Returns dict with same keys as Amazon scraper; uses asin_for_key so pipeline stays keyed by ASIN.
    """
    pid, slug = _parse_flipkart_input(flipkart_url_or_pid)
    if not pid:
        raise ValueError(f"Could not parse Flipkart ID from: {flipkart_url_or_pid}")

    product_url = f"{BASE_URL}/{slug}/p/{pid}" if slug else f"{BASE_URL}/p/{pid}"
    product_data = _fetch_flipkart_product_page(product_url, pid)
    reviews = _fetch_flipkart_reviews(pid, slug or pid)
    sentiments = [TextBlob(r).sentiment.polarity for r in reviews if r] if reviews else []
    avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0

    return {
        "asin": asin_for_key,
        "name": product_data.get("name", f"Flipkart {pid}"),
        "price": product_data.get("price", 0.0),
        "rating": product_data.get("rating", 0.0),
        "reviews": reviews,
        "avg_sentiment": avg_sentiment,
        "review_count": len(reviews),
        "review_spike": len(reviews),
        "scraped_at": time.time(),
    }


def _parse_flipkart_input(url_or_pid: str) -> tuple:
    """Return (pid, slug) from full URL or (pid, '') from raw pid."""
    s = (url_or_pid or "").strip()
    if not s:
        return ("", "")
    if s.startswith("http"):
        m = re.search(r"flipkart\.com/([^/]+)/p/([a-zA-Z0-9]+)", s)
        if m:
            return (m.group(2), m.group(1))
        m = re.search(r"/p/([a-zA-Z0-9]+)", s)
        if m:
            return (m.group(1), "")
    if re.match(r"^[a-zA-Z0-9]+$", s):
        return (s, "")
    return ("", "")


def _fetch_flipkart_product_page(url: str, pid: str) -> dict:
    resp = _http_get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    name = f"Product {pid}"
    for sel in ["h1", "span.B_NuCI", ".yhB1nd", "span[class*='product']"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            name = el.get_text(strip=True)[:200]
            break

    price = 0.0
    for sel in ["div._30jeq3", "div._16Jk6d", "[class*=_30jeq3]", ".Nx9bqj"]:
        el = soup.select_one(sel)
        if el:
            raw = el.get_text(strip=True).replace(",", "").replace("₹", "").strip()
            try:
                price = float(re.sub(r"[^\d.]", "", raw) or "0")
                break
            except ValueError:
                continue

    rating = 0.0
    for sel in ["div._3LWZlK", "span._3LWZlK", "[class*='_3LWZlK']", "div[class*='rating']"]:
        el = soup.select_one(sel)
        if el:
            raw = el.get_text(strip=True)
            try:
                rating = float(re.sub(r"[^\d.]", "", raw) or "0")
                if 0 <= rating <= 5:
                    break
            except ValueError:
                continue

    time.sleep(random.uniform(1.5, 3.0))
    return {"name": name, "price": price, "rating": rating}


def _fetch_flipkart_reviews(pid: str, slug: str, pages: int = 2) -> list:
    reviews = []
    # Flipkart: /slug/product-reviews/pid or /product-reviews/pid
    base_review_path = f"{slug}/product-reviews/{pid}" if slug else f"product-reviews/{pid}"
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/{base_review_path}?page={page}&sortOrder=MOST_RECENT"
        try:
            resp = _http_get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Flipkart review body classes (site updates these; try multiple)
            for selector in ["div.t-ZTKy", "div.qwjRop", "div._2-N8zT", "div[class*='t-ZTKy']", "div[class*='review']"]:
                for el in soup.select(selector):
                    text = el.get_text(strip=True)
                    if len(text) > 25 and text not in reviews:
                        reviews.append(text)
                if reviews:
                    break
            if not reviews and page == 1:
                for div in soup.select("div[class]"):
                    t = div.get_text(strip=True)
                    if 50 < len(t) < 800 and t not in reviews:
                        reviews.append(t)
            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            print(f"[FLIPKART] Review page {page} failed: {e}")
            break
    return reviews[:50]
