"""
Outlier detection and removal for scraped product data.
Cleans price, rating, review_count, and reviews list; logs actions for backend/agent log.
"""
from __future__ import annotations

from typing import Any

# Bounds
PRICE_MIN = 0.0
PRICE_MAX_DEFAULT = 10_000_000.0  # cap single-product price if absurd
RATING_MIN = 0.0
RATING_MAX = 5.0
REVIEW_COUNT_MIN = 0
REVIEW_COUNT_MAX = 500_000
IQR_MULTIPLIER = 1.5  # standard IQR fence


def _safe_float(v: Any, default: float | None = None) -> float | None:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        x = int(v)
        return x if x >= 0 else default
    except (TypeError, ValueError):
        return default


def clean_product_outliers(
    data: dict[str, Any],
    asin: str,
) -> tuple[dict[str, Any], list[tuple[str, Any, Any, str]]]:
    """
    Detect and remove/correct outliers in a single product's scraped data.
    Returns (cleaned_data, changes) where changes are (field, old_value, new_value, action).
    """
    if not data:
        return data, []
    out = dict(data)
    changes: list[tuple[str, Any, Any, str]] = []

    # --- Price ---
    raw_price = out.get("price")
    price = _safe_float(raw_price)
    if price is not None:
        if price < PRICE_MIN:
            out["price"] = None
            changes.append(("price", raw_price, None, "removed (negative)"))
        elif price > PRICE_MAX_DEFAULT:
            out["price"] = PRICE_MAX_DEFAULT
            changes.append(("price", raw_price, PRICE_MAX_DEFAULT, "capped (outlier)"))
    # Leave 0 or missing as-is; downstream can treat as "no price"

    # --- Rating ---
    raw_rating = out.get("rating")
    rating = _safe_float(raw_rating)
    if rating is not None and (rating < RATING_MIN or rating > RATING_MAX):
        clamped = max(RATING_MIN, min(RATING_MAX, rating))
        out["rating"] = clamped
        changes.append(("rating", raw_rating, clamped, "clamped to [0, 5]"))

    # --- Review count ---
    raw_rc = out.get("review_count")
    rc = _safe_int(raw_rc, 0)
    if rc < REVIEW_COUNT_MIN:
        out["review_count"] = REVIEW_COUNT_MIN
        changes.append(("review_count", raw_rc, REVIEW_COUNT_MIN, "corrected (negative)"))
    elif rc > REVIEW_COUNT_MAX:
        out["review_count"] = REVIEW_COUNT_MAX
        changes.append(("review_count", raw_rc, REVIEW_COUNT_MAX, "capped (outlier)"))

    # --- Review spike ---
    raw_spike = out.get("review_spike")
    spike = _safe_int(raw_spike, 0)
    if spike < 0:
        out["review_spike"] = 0
        changes.append(("review_spike", raw_spike, 0, "corrected (negative)"))
    elif spike > REVIEW_COUNT_MAX:
        out["review_spike"] = REVIEW_COUNT_MAX
        changes.append(("review_spike", raw_spike, REVIEW_COUNT_MAX, "capped (outlier)"))

    # --- Reviews list: remove empty and duplicates (by text) ---
    reviews = out.get("reviews") or []
    if isinstance(reviews, list):
        seen: set[str] = set()
        cleaned_reviews: list[str] = []
        for r in reviews:
            if not isinstance(r, str):
                continue
            t = r.strip()
            if len(t) < 3:  # skip empty or too short
                continue
            if t in seen:
                continue
            seen.add(t)
            cleaned_reviews.append(r)
        if len(cleaned_reviews) != len(reviews):
            out["reviews"] = cleaned_reviews
            changes.append(
                (
                    "reviews",
                    len(reviews),
                    len(cleaned_reviews),
                    f"removed {len(reviews) - len(cleaned_reviews)} empty/duplicate",
                )
            )
        # Sync review_count to list length if we trimmed
        if cleaned_reviews and out.get("review_count", 0) != len(cleaned_reviews):
            old_rc = out["review_count"]
            out["review_count"] = len(cleaned_reviews)
            changes.append(("review_count", old_rc, len(cleaned_reviews), "synced to reviews list length"))

    return out, changes


def _iqr_bounds(values: list[float]) -> tuple[float | None, float | None]:
    """Return (lower_bound, upper_bound) for IQR fence; None if not enough data."""
    if not values or len(values) < 2:
        return None, None
    sorted_ = sorted(values)
    n = len(sorted_)
    q1_idx = (n - 1) // 4
    q3_idx = (3 * (n - 1)) // 4
    q1 = sorted_[q1_idx]
    q3 = sorted_[q3_idx]
    iqr = q3 - q1
    if iqr <= 0:
        return None, None
    lower = q1 - IQR_MULTIPLIER * iqr
    upper = q3 + IQR_MULTIPLIER * iqr
    return lower, upper


def clean_cross_asin_price_outliers(
    scraped_data: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[tuple[str, Any, Any, str]]]:
    """
    Across all ASINs, detect price outliers using IQR and cap them to the fence.
    Returns (updated_scraped_data, changes).
    """
    if len(scraped_data) < 2:
        return scraped_data, []

    prices: list[tuple[str, float]] = []
    for asin, data in scraped_data.items():
        p = _safe_float(data.get("price"))
        if p is not None and p > 0:
            prices.append((asin, p))

    if len(prices) < 2:
        return scraped_data, []

    values = [p for _, p in prices]
    lower, upper = _iqr_bounds(values)
    if lower is None or upper is None:
        return scraped_data, []

    out = dict(scraped_data)
    changes: list[tuple[str, str, Any, Any, str]] = []

    for asin, price in prices:
        if price < lower:
            out[asin] = dict(out[asin])
            out[asin]["price"] = round(lower, 2)
            changes.append((asin, "price", price, round(lower, 2), "cross-ASIN IQR lower"))
        elif price > upper:
            out[asin] = dict(out[asin])
            out[asin]["price"] = round(upper, 2)
            changes.append((asin, "price", price, round(upper, 2), "cross-ASIN IQR upper"))

    return out, changes
