import json
import os
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "stores_data.json")


def load_stores() -> list[dict]:
    """Load store price data from the bundled JSON file."""
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data["stores"]


def get_available_items() -> set[str]:
    """Return all items available across all stores."""
    stores = load_stores()
    items = set()
    for store in stores:
        items.update(store["prices"].keys())
    return items


def compare_prices(grocery_list: list[str]) -> dict:
    """
    Compare total price of grocery_list across all stores.

    Returns a dict with:
      - results: list of {store, location, total, found_items, missing_items}
        sorted by total (ascending)
      - cheapest: the store entry with the minimum total
      - not_found_anywhere: items not found in any store
    """
    stores = load_stores()
    normalized_list = [item.strip().lower() for item in grocery_list]

    all_store_items = set()
    for store in stores:
        all_store_items.update(k.lower() for k in store["prices"])
    not_found_anywhere = [item for item in normalized_list if item not in all_store_items]

    results = []
    for store in stores:
        prices = {k.lower(): v for k, v in store["prices"].items()}
        total = 0.0
        found_items = {}
        missing_items = []

        for item in normalized_list:
            if item in prices:
                found_items[item] = prices[item]
                total += prices[item]
            else:
                missing_items.append(item)

        results.append({
            "store": store["name"],
            "location": store["location"],
            "total": round(total, 2),
            "found_items": found_items,
            "missing_items": missing_items,
        })

    results.sort(key=lambda x: x["total"])
    cheapest = results[0] if results else None

    return {
        "results": results,
        "cheapest": cheapest,
        "not_found_anywhere": not_found_anywhere,
    }


def get_per_item_cheapest(grocery_list: list[str]) -> dict[str, Optional[dict]]:
    """
    For each item, find which store sells it cheapest.
    Returns {item: {store, location, price}} or {item: None} if not found.
    """
    stores = load_stores()
    result = {}

    for item in grocery_list:
        item_lower = item.strip().lower()
        best = None
        for store in stores:
            prices = {k.lower(): v for k, v in store["prices"].items()}
            if item_lower in prices:
                if best is None or prices[item_lower] < best["price"]:
                    best = {
                        "store": store["name"],
                        "location": store["location"],
                        "price": prices[item_lower],
                    }
        result[item_lower] = best

    return result
