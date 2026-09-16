"""
Resilient public-API client with fallback caching.

Enriches a ticket's `product_id` with live product data. If the request fails
(network down, timeout, non-200), falls back to the last successful response
cached on disk, so the pipeline degrades gracefully instead of crashing.

Course tie-in: Module 2 · Lesson 2 (Public APIs and Resilient Integration)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

import requests

CACHE_PATH = Path(__file__).resolve().parents[2] / "data" / "api_cache.json"
DEFAULT_BASE_URL = os.environ.get("PRODUCT_API_BASE_URL", "https://fakestoreapi.com")
MAX_RETRIES = 2
TIMEOUT_SECONDS = 5


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))


def fetch_product(product_id: str, base_url: str = DEFAULT_BASE_URL) -> Optional[dict]:
    """Fetch product data by id, with retries and a disk-cache fallback.

    Returns a dict with at least `id`, `title`, and `price` on success (live
    or cached), or None if the product truly cannot be resolved.
    """
    if not product_id:
        return None

    cache = _load_cache()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(f"{base_url}/products/{product_id}", timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            data = resp.json()
            cache[str(product_id)] = data
            _save_cache(cache)
            return data
        except (requests.RequestException, ValueError):
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * attempt)  # simple backoff
                continue

    # All live attempts failed — fall back to cache.
    cached = cache.get(str(product_id))
    if cached is not None:
        cached = {**cached, "_source": "cache"}
        return cached

    return None


def enrich_ticket(ticket, base_url: str = DEFAULT_BASE_URL) -> None:
    """Mutates `ticket.enrichment` in place with whatever product data we can get."""
    product = fetch_product(ticket.product_id, base_url=base_url) if ticket.product_id else None
    ticket.enrichment["product"] = product
    ticket.enrichment["enrichment_status"] = (
        "not_applicable" if ticket.product_id is None
        else "live" if product and product.get("_source") != "cache"
        else "cached" if product
        else "unavailable"
    )


if __name__ == "__main__":
    print(fetch_product("1"))
