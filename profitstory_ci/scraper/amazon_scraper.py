import os
import time
import random
import json
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob  # type: ignore[reportMissingImports]

try:
    from .flipkart_scraper import scrape_flipkart_product
except ImportError:
    try:
        from scraper.flipkart_scraper import scrape_flipkart_product
    except ImportError:
        scrape_flipkart_product = None
try:
    from .snapdeal_scraper import scrape_snapdeal_product
except ImportError:
    try:
        from scraper.snapdeal_scraper import scrape_snapdeal_product
    except ImportError:
        scrape_snapdeal_product = None

BASE_URL = "https://www.amazon.in"

# Realistic Chrome-like headers for direct Amazon.in scraping (bypasses basic bot checks)
AMAZON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Referer": "https://www.amazon.in/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Sec-Ch-Ua": '"Chromium";v="133", "Not-A.Brand";v="8", "Google Chrome";v="133"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Cache-Control": "max-age=0",
}

# Legacy headers for ScraperAPI/RapidAPI or other services
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.amazon.in/",
    "DNT": "1",
}

# Scraping: RapidAPI (preferred) or ScraperAPI; no direct requests to Amazon/Flipkart
RAPIDAPI_KEY = (os.environ.get("RAPIDAPI_KEY") or "").strip()
RAPIDAPI_AMAZON_HOST = (
    os.environ.get("RAPIDAPI_AMAZON_HOST") or "real-time-amazon-data.p.rapidapi.com"
).strip()
AMAZON_COUNTRY = (os.environ.get("AMAZON_COUNTRY") or "IN").strip().upper()  # IN for amazon.in
SCRAPERAPI_KEY = (os.environ.get("SCRAPERAPI_KEY") or "").strip()

MOCK_PRODUCTS = {
    "B0CXYZ123": {
        "asin": "B0CXYZ123",
        "name": "Premium Earphones",
        "price": 999.0,
        "rating": 4.6,
        "cost": 550.0,
        "reviews": [
            "Amazing quality!",
            "Great sound and very durable.",
            "Really good for the price."
        ],
        "avg_sentiment": 0.85,
        "review_count": 12,
        "review_spike": 2,
        "scraped_at": time.time()
    },
    "B0CDEF456": {
        "asin": "B0CDEF456",
        "name": "XYZ Budget Earphones",
        "price": 699.0,
        "rating": 3.1,
        "reviews": [
            "Sound dies after 2 weeks, very disappointed",
            "The sound dies completely after a month of use",
            "Worst quality, sound dies within days",
            "Left ear stopped working",
            "Broken defective product",
            "The wire is flimsy and breaks easily",
            "Quality issues sound problems",
            "It was good for a week then died",
            "Terrible sound quality after a while",
            "Do not buy, defective",
            "Audio driver failure out of nowhere",
            "Poor quality not durable at all",
            "Cannot hear anything after a few days",
            "Right side died completely",
            "Waste of money, completely broken"
        ] * 3, # Multiply to simulate 45 reviews
        "avg_sentiment": -0.68,
        "review_count": 45,
        "review_spike": 45,
        "scraped_at": time.time()
    },
    "B0ABCD789": {
        "asin": "B0ABCD789",
        "name": "SoundMax Pro",
        "price": 1199.0,
        "rating": 4.2,
        "reviews": ["Good sound", "A bit expensive but okay"],
        "avg_sentiment": 0.40,
        "review_count": 25,
        "review_spike": 5,
        "scraped_at": time.time()
    }
}

def _generate_mock(asin: str) -> dict:
    return {
        "asin": asin,
        "name": f"Mock Product {asin}",
        "price": random.uniform(500, 2000),
        "rating": round(random.uniform(2.5, 4.8), 1),
        "reviews": ["Mock review 1", "Mock review 2"],
        "avg_sentiment": random.uniform(-1, 1),
        "review_count": 2,
        "review_spike": 0,
        "scraped_at": time.time()
    }

_FALLBACK_PRODUCTS_CACHE = None


def _load_fallback_products() -> dict | None:
    """Load dummy Flipkart/Snapdeal product + competitors from JSON (used when Amazon fails and no env fallback URL)."""
    global _FALLBACK_PRODUCTS_CACHE
    if _FALLBACK_PRODUCTS_CACHE is not None:
        return _FALLBACK_PRODUCTS_CACHE
    for base in (os.path.dirname(__file__), os.path.join(os.path.dirname(__file__), "..")):
        path = os.path.join(os.path.abspath(base), "fallback_products.json")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    _FALLBACK_PRODUCTS_CACHE = json.load(f)
                return _FALLBACK_PRODUCTS_CACHE
            except Exception as e:
                print(f"[SCRAPER] Failed to load fallback_products.json: {e}")
                break
    _FALLBACK_PRODUCTS_CACHE = {}
    return _FALLBACK_PRODUCTS_CACHE


def _dummy_fallback_from_json(asin: str) -> dict | None:
    """Return pipeline-shaped dict from fallback_products.json. JSON can be array of items (each with flipkart/snapdeal) or dict. Uses fsn (Flipkart) / pid (Snapdeal) from JSON and includes them in metadata for input/display."""
    raw = _load_fallback_products()
    if not raw:
        return None
    # Support array format: [ { "id", "flipkart", "snapdeal" }, ... ]
    if isinstance(raw, list) and len(raw) > 0:
        data = random.choice(raw)
    elif isinstance(raw, dict) and ("flipkart" in raw or "snapdeal" in raw):
        data = raw
    else:
        return None
    platform = random.choice(["flipkart", "snapdeal"])
    section = data.get(platform) if isinstance(data, dict) else None
    if not section or not isinstance(section, dict):
        return None
    product = section.get("product")
    competitors = section.get("competitors") or []
    if not product or not isinstance(product, dict):
        return None
    if not competitors or random.random() < 1.0 / (1 + len(competitors)):
        entry = product
    else:
        entry = random.choice(competitors)
    reviews = entry.get("reviews") or []
    sentiments = [TextBlob(r).sentiment.polarity for r in reviews if r] if reviews else []
    avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0
    name = entry.get("name") or f"Product {asin}"
    price = float(entry.get("price", 0))
    rating = float(entry.get("rating", 0))
    # FSN (Flipkart) or pid (Snapdeal) for display / input replacement
    fallback_source_id = entry.get("fsn") if platform == "flipkart" else entry.get("pid")
    if fallback_source_id is not None:
        fallback_source_id = str(fallback_source_id)
    print(f"[SCRAPER] Using dummy {platform} fallback for {asin}: {name[:50]}... (id={fallback_source_id}, {len(reviews)} reviews)")
    result = {
        "asin": asin,
        "name": name,
        "price": price,
        "rating": rating,
        "reviews": reviews,
        "avg_sentiment": avg_sentiment,
        "review_count": len(reviews),
        "review_spike": len(reviews),
        "scraped_at": time.time(),
    }
    if fallback_source_id:
        result["fallback_platform"] = platform
        result["fallback_source_id"] = fallback_source_id
    return result


def _is_amazon_block_page(html: str) -> bool:
    """True if response looks like a captcha/robot check page."""
    lower = html.lower()
    return (
        "robot check" in lower
        or "captcha" in lower
        or "enter the characters you see" in lower
        or "sorry, we just need to make sure you're not a robot" in lower
    )


def _extract_reviews_from_pdp(soup: BeautifulSoup) -> list[str]:
    """Extract review snippets from the product page (PDP). Amazon often shows a few on the main page."""
    reviews = []
    seen = set()
    # PDP review snippets: same data-hook and classes as review list page
    for sel in (
        'span[data-hook="review-body"] span',
        'div[data-hook="review-body"]',
        "#reviewsMedley span[data-hook='review-body']",
        "#reviewsMedley .review-text-content span",
        ".review-text-content",
        "[data-hook='review-body']",
    ):
        for el in soup.select(sel):
            text = el.get_text(strip=True)
            if len(text) > 25 and text not in seen:
                seen.add(text)
                reviews.append(text)
        if reviews:
            break
    return reviews[:20]  # limit to a few from PDP


def _fetch_amazon_in_direct(asin: str) -> dict | None:
    """
    Scrape Amazon.in product + reviews using direct requests, session, and BeautifulSoup.
    Uses realistic Chrome headers to bypass basic bot checks. Returns pipeline shape or None on failure.
    """
    url = f"{BASE_URL}/dp/{asin.strip()}"
    session = requests.Session()
    try:
        time.sleep(random.uniform(2.0, 3.5))  # longer initial delay to reduce first-request block
        response = session.get(url, headers=AMAZON_HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"[SCRAPER] Direct Amazon.in returned {response.status_code} for {asin}")
            return None
        if _is_amazon_block_page(response.text):
            print(f"[SCRAPER] Direct Amazon.in: captcha/block page for {asin}")
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        # Product title
        title_tag = soup.find("span", id="productTitle") or soup.find("h1", id="title")
        name = title_tag.get_text(strip=True) if title_tag else f"Product {asin}"

        # Price (whole + fraction or a-offscreen)
        price = 0.0
        whole = soup.find("span", class_="a-price-whole")
        fraction = soup.find("span", class_="a-price-fraction")
        if whole and fraction:
            raw = f"{whole.get_text(strip=True)}.{fraction.get_text(strip=True)}"
        else:
            offscreen = soup.find("span", class_="a-offscreen")
            raw = offscreen.get_text(strip=True).replace("₹", "").strip() if offscreen else ""
        if raw:
            try:
                price = float(raw.replace(",", ""))
            except ValueError:
                pass

        # Rating (e.g. "4.5 out of 5")
        rating = 0.0
        rating_tag = soup.find("span", class_="a-icon-alt")
        if rating_tag:
            txt = rating_tag.get_text(strip=True)
            try:
                rating = float(txt.split()[0])
            except (ValueError, IndexError):
                pass

        time.sleep(random.uniform(1.5, 3.0))
        # Try review snippets on the product page first (often present even when review list page is blocked)
        reviews = _extract_reviews_from_pdp(soup)
        if not reviews:
            reviews = _fetch_reviews_direct(session, asin)
        if not reviews:
            fallback = MOCK_PRODUCTS.get(asin, _generate_mock(asin))
            reviews = fallback["reviews"]
            print(f"[SCRAPER] No reviews for {asin}; using {len(reviews)} fallback reviews for embedding.")
        sentiments = [TextBlob(r).sentiment.polarity for r in reviews if r] if reviews else []
        avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0
        return {
            "asin": asin,
            "name": name,
            "price": price,
            "rating": rating,
            "reviews": reviews,
            "avg_sentiment": avg_sentiment,
            "review_count": len(reviews),
            "review_spike": len(reviews),
            "scraped_at": time.time(),
        }
    except Exception as e:
        print(f"[SCRAPER] Direct Amazon.in failed for {asin}: {e}")
        return None


def _fetch_reviews_direct(session: requests.Session, asin: str, pages: int = 3) -> list[str]:
    """Fetch review text from Amazon.in product-reviews pages using same session + BeautifulSoup."""
    reviews = []
    seen = set()
    for page_num in range(1, pages + 1):
        url = f"{BASE_URL}/product-reviews/{asin}?sortBy=recent&reviewerType=all_reviews&pageNumber={page_num}"
        try:
            time.sleep(random.uniform(2.0, 4.0))
            resp = session.get(url, headers=AMAZON_HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            if _is_amazon_block_page(resp.text):
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            # Try multiple selectors; Amazon changes markup and uses different structures
            candidates = []
            candidates.extend(soup.select('span[data-hook="review-body"] span'))
            if not candidates:
                candidates.extend(soup.select('div[data-hook="review-body"]'))
            if not candidates:
                candidates.extend(soup.select("div.review-text-content span"))
            if not candidates:
                candidates.extend(soup.select(".review-text-content"))
            if not candidates:
                candidates.extend(soup.select(".review-text"))
            if not candidates:
                # Review list container: get text from each review item
                for li in soup.select("#cm-cr-dp-review-list li"):
                    body = li.select_one('[data-hook="review-body"]') or li.select_one(".review-text")
                    if body:
                        candidates.append(body)
            for el in candidates:
                text = el.get_text(strip=True)
                if len(text) > 20 and text not in seen:
                    seen.add(text)
                    reviews.append(text)
            if not reviews and page_num == 1:
                break
        except Exception as e:
            print(f"[SCRAPER] Review page {page_num} failed for {asin}: {e}")
            break
    return reviews[:50]


def scrape_amazon(asin: str) -> dict:
    """
    Scrape product data from Amazon. Tries: (1) Direct Amazon.in + BeautifulSoup,
    (2) RapidAPI, (3) ScraperAPI; then Flipkart/Snapdeal fallbacks or mock.
    """
    # 1) Direct Amazon.in with session + Chrome-like headers + BeautifulSoup
    try:
        print(f"[SCRAPER] Scraping Amazon.in (direct) for {asin}...")
        data = _fetch_amazon_in_direct(asin)
        if data:
            print(f"[SCRAPER] Direct Amazon.in OK: {data.get('name', '')[:50]}... ({len(data.get('reviews', []))} reviews)")
            return data
    except Exception as e:
        print(f"[SCRAPER] Direct Amazon.in failed: {e}")
    # 2) RapidAPI Real-Time Amazon Data
    if RAPIDAPI_KEY:
        try:
            print(f"[SCRAPER] Scraping via RapidAPI for {asin}...")
            product_data = _fetch_product_via_rapidapi(asin)
            reviews = _fetch_reviews_via_rapidapi(asin)
            if not reviews:
                fallback = MOCK_PRODUCTS.get(asin, _generate_mock(asin))
                reviews = fallback["reviews"]
                print(f"[SCRAPER] No reviews for {asin}; using {len(reviews)} fallback reviews for embedding.")
            sentiments = [TextBlob(r).sentiment.polarity for r in reviews if r] if reviews else []
            avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0
            return {
                **product_data,
                "reviews": reviews,
                "avg_sentiment": avg_sentiment,
                "review_count": len(reviews),
                "review_spike": len(reviews),
                "scraped_at": time.time(),
            }
        except Exception as e:
            print(f"[SCRAPER] RapidAPI failed for {asin}: {e}. Falling back to ScraperAPI or fallbacks.")
    # 3) ScraperAPI (if key set)
    if SCRAPERAPI_KEY:
        try:
            print(f"[SCRAPER] Scraping via ScraperAPI for {asin}...")
            product_data = _fetch_product_page(asin)
            reviews = _fetch_reviews(asin)
            if not reviews:
                fallback = MOCK_PRODUCTS.get(asin, _generate_mock(asin))
                reviews = fallback["reviews"]
                print(f"[SCRAPER] No reviews for {asin}; using {len(reviews)} fallback reviews for embedding.")
            sentiments = [TextBlob(r).sentiment.polarity for r in reviews if r] if reviews else []
            avg_sentiment = round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0
            return {
                **product_data,
                "reviews": reviews,
                "avg_sentiment": avg_sentiment,
                "review_count": len(reviews),
                "review_spike": len(reviews),
                "scraped_at": time.time(),
            }
        except Exception as e:
            print(f"[SCRAPER] ScraperAPI failed for {asin}: {e}.")
    # 4) Flipkart / Snapdeal / mock
    flipkart_url = os.environ.get("FLIPKART_FALLBACK_URL", "").strip()
    flipkart_pid = os.environ.get("FLIPKART_FALLBACK_PID", "").strip()
    flipkart_input = flipkart_url or flipkart_pid
    if flipkart_input and scrape_flipkart_product:
        try:
            print(f"[SCRAPER] Trying Flipkart fallback for {asin}...")
            data = scrape_flipkart_product(flipkart_input, asin_for_key=asin)
            print(f"[SCRAPER] Flipkart fallback OK: {data.get('name', '')[:50]}... ({len(data.get('reviews', []))} reviews)")
            return data
        except Exception as fk_err:
            print(f"[SCRAPER] Flipkart fallback failed: {fk_err}.")
    snapdeal_url = os.environ.get("SNAPDEAL_FALLBACK_URL", "").strip()
    snapdeal_pid = os.environ.get("SNAPDEAL_FALLBACK_PID", "").strip()
    snapdeal_input = snapdeal_url or snapdeal_pid
    if snapdeal_input and scrape_snapdeal_product:
        try:
            print(f"[SCRAPER] Trying Snapdeal fallback for {asin}...")
            data = scrape_snapdeal_product(snapdeal_input, asin_for_key=asin)
            print(f"[SCRAPER] Snapdeal fallback OK: {data.get('name', '')[:50]}... ({len(data.get('reviews', []))} reviews)")
            return data
        except Exception as sd_err:
            print(f"[SCRAPER] Snapdeal fallback failed: {sd_err}.")
    # 5) Dummy Flipkart/Snapdeal from JSON (product + competitors with reviews)
    data = _dummy_fallback_from_json(asin)
    if data:
        return data
    print("[SCRAPER] Using mock data.")
    return MOCK_PRODUCTS.get(asin, _generate_mock(asin))


def scrape_product(platform: str, platform_id: str) -> dict:
    """
    Route to the correct scraper based on platform.
    platform: amazon | flipkart | snapdeal
    """
    platform = (platform or "amazon").strip().lower()
    if platform == "amazon":
        return scrape_amazon(platform_id)
    if platform == "flipkart" and scrape_flipkart_product:
        # Flipkart scraper expects url or pid and asin_for_key (we use platform_id as key)
        return scrape_flipkart_product(platform_id, asin_for_key=platform_id)
    if platform == "snapdeal" and scrape_snapdeal_product:
        return scrape_snapdeal_product(platform_id, asin_for_key=platform_id)
    # Default to Amazon
    return scrape_amazon(platform_id)


def _rapidapi_get(path: str, params: dict) -> dict:
    """Call RapidAPI Real-Time Amazon Data. Returns JSON.
    On 403 with country=IN, retries with country=US (many plans only support US).
    """
    url = f"https://{RAPIDAPI_AMAZON_HOST}{path}"
    headers = {
        "x-rapidapi-host": RAPIDAPI_AMAZON_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        if e.response.status_code == 403 and params.get("country") and params.get("country") != "US":
            # Many RapidAPI Amazon APIs only allow country=US; retry with US
            params_us = {**params, "country": "US"}
            print(f"[SCRAPER] RapidAPI 403 for country={params.get('country')}; retrying with country=US.")
            resp = requests.get(url, headers=headers, params=params_us, timeout=30)
            resp.raise_for_status()
            return resp.json()
        raise


def _fetch_product_via_rapidapi(asin: str) -> dict:
    """Fetch product name, price, rating from RapidAPI Product Details."""
    # Endpoint: GET product-details (asin, country)
    data = _rapidapi_get("/product-details", {"asin": asin, "country": AMAZON_COUNTRY})
    # Real-Time Amazon Data returns: product_title, product_price, product_star_rating
    product = data.get("data", data)
    if not isinstance(product, dict):
        product = data
    title = (
        product.get("product_title")
        or product.get("title")
        or product.get("name")
        or f"Product {asin}"
    )
    rating = 0.0
    r = (
        product.get("product_star_rating")
        or product.get("rating")
        or product.get("stars")
        or product.get("average_rating")
    )
    if r is not None:
        try:
            rating = float(r)
        except (TypeError, ValueError):
            pass
    price = 0.0
    p = (
        product.get("product_price")
        or product.get("price")
        or product.get("current_price")
    )
    if p is not None:
        try:
            price = float(p) if isinstance(p, (int, float)) else float(str(p).replace(",", "").replace("₹", "").replace("$", "").strip())
        except (TypeError, ValueError):
            pass
    if price == 0.0 and isinstance(product.get("buybox_winner"), dict):
        buybox = product["buybox_winner"]
        try:
            price = float(buybox.get("price", {}).get("value", 0) or buybox.get("price", 0))
        except (TypeError, ValueError, KeyError):
            pass
    return {"asin": asin, "name": title, "price": price, "rating": rating}


def _fetch_reviews_via_rapidapi(asin: str) -> list[str]:
    """Fetch review text list from RapidAPI Top Product Reviews."""
    data = _rapidapi_get(
        "/top-product-reviews", {"asin": asin, "country": AMAZON_COUNTRY}
    )
    reviews = []
    # data.reviews or data.data.reviews or similar
    rev_list = data.get("data", data)
    if isinstance(rev_list, dict):
        rev_list = rev_list.get("reviews", rev_list.get("top_reviews", []))
    if not isinstance(rev_list, list):
        rev_list = data.get("reviews", [])
    for r in rev_list:
        if not isinstance(r, dict):
            continue
        text = (
            r.get("review")
            or r.get("body")
            or r.get("review_body")
            or r.get("text")
            or r.get("content")
        )
        if text and len(str(text).strip()) > 20:
            reviews.append(str(text).strip())
    return reviews[:50]


def _http_get(url: str) -> requests.Response:
    """
    All requests go through ScraperAPI only (no direct Amazon/Flipkart requests).
    """
    params = {
        "api_key": SCRAPERAPI_KEY,
        "url": url,
        "keep_headers": "true",
    }
    resp = requests.get("https://api.scraperapi.com", params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp


def _fetch_product_page(asin: str) -> dict:
    url = f"{BASE_URL}/dp/{asin}"
    resp = _http_get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    price_el = soup.select_one("span.a-price-whole") or soup.select_one("span.a-offscreen")
    price_text = price_el.get_text(strip=True).replace(",", "").replace("₹", "").strip() if price_el else "0"
    try:
        price = float(price_text) if price_text else 0.0
    except ValueError:
        price = 0.0

    rating_el = soup.select_one("span.a-icon-alt") or soup.select_one("div[data-hook='average-star-rating'] span")
    rating = float(rating_el.get_text().split()[0]) if rating_el else 0.0

    name_el = soup.select_one("span#productTitle") or soup.select_one("h1 span#productTitle")
    name = name_el.get_text(strip=True) if name_el else f"Product {asin}"

    time.sleep(random.uniform(1.5, 3.0))
    return {"asin": asin, "name": name, "price": price, "rating": rating}


def _fetch_reviews(asin: str, pages: int = 3) -> list[str]:
    reviews = []
    for page_num in range(1, pages + 1):
        url = (
            f"{BASE_URL}/product-reviews/{asin}"
            f"?sortBy=recent&reviewerType=all_reviews&pageNumber={page_num}"
        )
        try:
            resp = _http_get(url)
            soup = BeautifulSoup(resp.text, "html.parser")
            review_els = soup.select('span[data-hook="review-body"] span')
            if not review_els:
                review_els = soup.select("div.review-text-content span")
            page_reviews = [
                el.get_text(strip=True)
                for el in review_els
                if len(el.get_text(strip=True)) > 20
            ]
            reviews.extend(page_reviews)
            if not page_reviews:
                break
            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            print(f"[SCRAPER] Review page {page_num} failed for {asin}: {e}")
            break
    return reviews[:50]
