"""
Snapdeal scraper — used as fallback when Amazon/Flipkart fail.
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
    "Referer": "https://www.snapdeal.com/",
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

BASE_URL = "https://www.snapdeal.com"


def _http_get(url: str) -> requests.Response:
    """Direct request to Snapdeal; parsed with BeautifulSoup."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp


def scrape_snapdeal_product(snapdeal_url_or_pid: str, asin_for_key: str) -> dict:
    """
    Scrape a Snapdeal product by full URL or by pid (e.g. 626304069296).
    URL format: https://www.snapdeal.com/product/<slug>/<pid> or /product/<slug>/<pid>?lang=en
    Returns dict with same keys as Amazon scraper; uses asin_for_key so pipeline stays keyed by ASIN.
    """
    pid, slug = _parse_snapdeal_input(snapdeal_url_or_pid)
    if not pid:
        raise ValueError(f"Could not parse Snapdeal product ID from: {snapdeal_url_or_pid}")

    if slug:
        product_url = f"{BASE_URL}/product/{slug}/{pid}"
    else:
        # Snapdeal requires slug in URL; use generic slug (may 404 if product needs real slug)
        product_url = f"{BASE_URL}/product/p/{pid}"

    product_data = _fetch_snapdeal_product_page(product_url, pid)
    reviews = _fetch_snapdeal_reviews(pid, slug or "product", product_url)
    sentiments = [TextBlob(r).sentiment.polarity for r in reviews if r] if reviews else []
    avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0

    return {
        "asin": asin_for_key,
        "name": product_data.get("name", f"Snapdeal {pid}"),
        "price": product_data.get("price", 0.0),
        "rating": product_data.get("rating", 0.0),
        "reviews": reviews,
        "avg_sentiment": avg_sentiment,
        "review_count": len(reviews),
        "review_spike": len(reviews),
        "scraped_at": time.time(),
    }


def _parse_snapdeal_input(url_or_pid: str) -> tuple:
    """Return (pid, slug) from full URL or (pid, '') from raw pid."""
    s = (url_or_pid or "").strip()
    if not s:
        return ("", "")
    if s.startswith("http"):
        # https://www.snapdeal.com/product/<slug>/<pid> or /product/<slug>/<pid>?...
        m = re.search(r"snapdeal\.com/product/([^/]+)/([0-9]+)", s)
        if m:
            return (m.group(2), m.group(1))
        m = re.search(r"/product/[^/]+/([0-9]+)", s)
        if m:
            return (m.group(1), "")
    if re.match(r"^[0-9]+$", s):
        return (s, "")
    return ("", "")


def _fetch_snapdeal_product_page(url: str, pid: str) -> dict:
    """Parse product name, price, rating from Snapdeal PDP with BeautifulSoup."""
    resp = _http_get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    name = f"Product {pid}"
    for sel in [
        "h1[itemprop='name']",
        "h1.pdp-e-i-head",
        "h1",
        "[class*='pdp-title']",
        "[class*='product-title']",
        ".product-desc",
    ]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            name = el.get_text(strip=True)[:200]
            break

    price = 0.0
    for sel in [
        "span[itemprop='price']",
        "span.pdp-final-price",
        "[class*='paybl']",
        "[class*='pdp-price']",
        ".product-price",
        "span[class*='price']",
    ]:
        for el in soup.select(sel):
            raw = el.get_text(strip=True).replace(",", "").replace("₹", "").replace("Rs.", "").strip()
            try:
                val = float(re.sub(r"[^\d.]", "", raw) or "0")
                if val > 0:
                    price = val
                    break
            except ValueError:
                continue
        if price > 0:
            break

    rating = 0.0
    for sel in [
        "span[itemprop='ratingValue']",
        "[class*='rating']",
        ".pdp-rating",
        "div.sd-icon-star",
    ]:
        for el in soup.select(sel):
            raw = el.get_text(strip=True)
            try:
                val = float(re.sub(r"[^\d.]", "", raw) or "0")
                if 0 <= val <= 5:
                    rating = val
                    break
            except ValueError:
                continue
        if rating > 0:
            break

    time.sleep(random.uniform(1.5, 3.0))
    return {"name": name, "price": price, "rating": rating}


def _fetch_snapdeal_reviews(pid: str, slug: str, product_url: str, pages: int = 2) -> list:
    """Fetch review text from Snapdeal reviews page(s) using BeautifulSoup."""
    reviews = []
    # Reviews URL: /product/<slug>/<pid>/reviews
    base_review_url = f"{BASE_URL}/product/{slug}/{pid}/reviews"
    for page in range(1, pages + 1):
        url = f"{base_review_url}?page={page}&sortBy=RECENCY" if page > 1 else base_review_url
        try:
            resp = _http_get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Snapdeal review body: user-review, review-text, or similar
            for selector in [
                "div.user-review",
                "div[class*='review-text']",
                "div[class*='reviewDesc']",
                "p.review-desc",
                "div.review-desc",
                "[class*='user-review']",
                "div[itemprop='reviewBody']",
            ]:
                for el in soup.select(selector):
                    text = el.get_text(strip=True)
                    if len(text) > 25 and text not in reviews:
                        reviews.append(text)
                if reviews:
                    break
            # Fallback: any div with substantial text that looks like a review
            if not reviews and page == 1:
                for div in soup.select("div[class]"):
                    t = div.get_text(strip=True)
                    if 50 < len(t) < 800 and t not in reviews:
                        reviews.append(t)
            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            print(f"[SNAPDEAL] Review page {page} failed: {e}")
            break
    return reviews[:50]
