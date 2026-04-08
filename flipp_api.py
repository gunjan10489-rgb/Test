"""
Flipp API client
================
Uses the Flipp public search API to fetch live flyer prices
for grocery items near a given postal / ZIP code.
"""

import time
import urllib.parse
import urllib.request
import json
from typing import Optional

BASE_URL = "https://backflipp.wishabi.com/flipp"


def _get(url: str) -> dict:
    """Minimal HTTP GET with a browser-like User-Agent header."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def get_flyers(postal_code: str, locale: str = "en-US") -> list[dict]:
    """
    Return a list of flyers available near postal_code.
    Each dict contains at minimum: id, merchant_name, merchant_id.
    """
    params = urllib.parse.urlencode({"locale": locale, "postal_code": postal_code})
    url = f"{BASE_URL}/flyers?{params}"
    data = _get(url)
    return data.get("flyers", [])


def search_item(
    query: str,
    postal_code: str,
    locale: str = "en-US",
) -> list[dict]:
    """
    Search Flipp for a grocery item near postal_code.

    Returns a list of matching items, each with keys:
      name, current_price, pre_price_text, merchant_name,
      flyer_id, category, image_url (may be None)
    """
    params = urllib.parse.urlencode(
        {"locale": locale, "postal_code": postal_code, "q": query}
    )
    url = f"{BASE_URL}/items/search?{params}"
    try:
        data = _get(url)
    except Exception:
        return []
    return data.get("items", [])


def _parse_price(item: dict) -> Optional[float]:
    """Extract a usable float price from a Flipp item dict."""
    price = item.get("current_price")
    if price is not None:
        try:
            return float(price)
        except (TypeError, ValueError):
            pass
    # Sometimes price is embedded in display_name or price_text
    for key in ("sale_price", "was_price", "price"):
        val = item.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


def fetch_prices_for_list(
    grocery_list: list[str],
    postal_code: str,
    locale: str = "en-US",
    delay: float = 0.4,
) -> dict[str, list[dict]]:
    """
    For each item in grocery_list, query Flipp and collect the
    cheapest offer per merchant.

    Returns:
      {
        "milk": [
          {"merchant": "Walmart", "price": 2.99, "name": "2% Milk 4L"},
          ...
        ],
        ...
      }
    Only items with a valid price are included.
    """
    results: dict[str, list[dict]] = {}

    for item in grocery_list:
        raw_items = search_item(item, postal_code, locale)

        # Group by merchant, keep only the cheapest offer per merchant
        merchant_best: dict[str, dict] = {}
        for flipp_item in raw_items:
            merchant = flipp_item.get("merchant_name") or flipp_item.get("merchant", "")
            if not merchant:
                continue
            price = _parse_price(flipp_item)
            if price is None or price <= 0:
                continue

            if merchant not in merchant_best or price < merchant_best[merchant]["price"]:
                merchant_best[merchant] = {
                    "merchant": merchant,
                    "price": price,
                    "name": flipp_item.get("name", item),
                }

        results[item] = sorted(merchant_best.values(), key=lambda x: x["price"])
        time.sleep(delay)  # be polite to the API

    return results


def build_store_totals(
    prices_by_item: dict[str, list[dict]],
    grocery_list: list[str],
) -> list[dict]:
    """
    Given per-item cheapest prices per merchant, compute what the
    total bill would be if you bought *everything* at each store.

    Only stores that carry at least one item are included.
    Items missing from a store are noted but not added to the total.

    Returns a list of store dicts sorted by total (ascending):
      [
        {
          "store": "Walmart",
          "total": 18.45,
          "found": {"milk": 2.99, "bread": 1.49, ...},
          "missing": ["eggs"],
        },
        ...
      ]
    """
    # Collect all merchant names
    all_merchants: set[str] = set()
    for offers in prices_by_item.values():
        for o in offers:
            all_merchants.add(o["merchant"])

    store_data: dict[str, dict] = {
        m: {"store": m, "total": 0.0, "found": {}, "missing": []}
        for m in all_merchants
    }

    for item in grocery_list:
        offers = prices_by_item.get(item, [])
        price_map = {o["merchant"]: o["price"] for o in offers}

        for merchant in all_merchants:
            if merchant in price_map:
                store_data[merchant]["found"][item] = price_map[merchant]
                store_data[merchant]["total"] += price_map[merchant]
            else:
                store_data[merchant]["missing"].append(item)

    # Round totals
    for sd in store_data.values():
        sd["total"] = round(sd["total"], 2)

    return sorted(store_data.values(), key=lambda x: x["total"])
