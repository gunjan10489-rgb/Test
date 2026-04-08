"""
Grocery Price Comparator — MCP Server
======================================
Exposes grocery price comparison as MCP tools so Claude (or any
MCP-compatible AI) can call them directly in conversation.

Usage:
    Install deps:   pip install mcp
    Run server:     python grocery_mcp_server.py

Claude Desktop config  (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "grocery": {
          "command": "python",
          "args": ["/absolute/path/to/grocery_mcp_server.py"]
        }
      }
    }

Then just tell Claude:
    "Compare prices for milk, eggs, and bread near postal code 10001"
"""

import json
from mcp.server.fastmcp import FastMCP
from flipp_api import get_flyers, fetch_prices_for_list, build_store_totals
from grocery_comparator import compare_prices, get_available_items, get_per_item_cheapest

mcp = FastMCP("Grocery Price Comparator")


# ---------------------------------------------------------------------------
# Tool 1: Get nearby stores
# ---------------------------------------------------------------------------

@mcp.tool()
def get_nearby_stores(postal_code: str) -> str:
    """
    List grocery stores that have active flyers near a given postal or ZIP code.

    Args:
        postal_code: The user's postal code or ZIP code (e.g. "10001" or "M5V 3L9").

    Returns:
        A formatted list of store names available near the given location.
    """
    try:
        flyers = get_flyers(postal_code)
    except Exception as exc:
        return f"Could not reach Flipp API: {exc}\nNo live store data available for '{postal_code}'."

    if not flyers:
        return f"No active flyers found near '{postal_code}'."

    merchants = sorted({f.get("merchant_name", "Unknown") for f in flyers})
    lines = [f"Stores with active flyers near '{postal_code}':\n"]
    for i, name in enumerate(merchants, 1):
        lines.append(f"  {i}. {name}")
    lines.append(f"\nTotal: {len(merchants)} store(s) found.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: Search prices for a grocery list
# ---------------------------------------------------------------------------

@mcp.tool()
def search_grocery_prices(postal_code: str, items: list[str]) -> str:
    """
    Fetch live flyer prices for a list of grocery items near a postal/ZIP code,
    using the Flipp API. Returns the cheapest price per item per store.

    Args:
        postal_code: The user's postal code or ZIP code.
        items: List of grocery item names to search (e.g. ["milk", "bread", "eggs"]).

    Returns:
        A formatted table showing the cheapest price for each item at each store.
    """
    if not items:
        return "No items provided. Please supply a list of grocery items."

    normalized = [item.strip().lower() for item in items]

    try:
        prices_by_item = fetch_prices_for_list(normalized, postal_code)
    except Exception as exc:
        return f"Error fetching prices from Flipp: {exc}"

    if not any(prices_by_item.values()):
        return (
            "No live prices found on Flipp for your area.\n"
            "Tip: Try get_cheapest_store_local for prices from the built-in database."
        )

    lines = [f"Live Flipp prices near '{postal_code}':\n"]
    lines.append(f"{'Item':<26} {'Store':<28} {'Price':>8}")
    lines.append("-" * 64)

    for item in normalized:
        offers = prices_by_item.get(item, [])
        if offers:
            for offer in offers[:3]:  # top 3 cheapest per item
                lines.append(
                    f"  {item.title():<24} {offer['merchant']:<28} ${offer['price']:>7.2f}"
                )
        else:
            lines.append(f"  {item.title():<24} {'Not found on Flipp':<28}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: Get cheapest store (live Flipp data)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_cheapest_store(postal_code: str, items: list[str]) -> str:
    """
    Compare total grocery bill across all stores near a postal/ZIP code using
    live Flipp flyer data, and return the store with the minimum total bill.

    Args:
        postal_code: The user's postal code or ZIP code.
        items: List of grocery item names (e.g. ["milk", "bread", "eggs"]).

    Returns:
        The store with the lowest total bill, itemised breakdown, and a ranked
        comparison table of all stores.
    """
    if not items:
        return "No items provided. Please supply a list of grocery items."

    normalized = [item.strip().lower() for item in items]

    try:
        prices_by_item = fetch_prices_for_list(normalized, postal_code)
        store_totals = build_store_totals(prices_by_item, normalized)
    except Exception as exc:
        return (
            f"Error fetching live prices: {exc}\n"
            "Falling back to local database — use get_cheapest_store_local instead."
        )

    if not store_totals:
        return (
            "No live prices found on Flipp for your area.\n"
            "Use get_cheapest_store_local for prices from the built-in database."
        )

    cheapest = store_totals[0]

    lines = [f"Price comparison near '{postal_code}':\n"]

    # Ranked table
    lines.append(f"{'#':<4} {'Store':<30} {'Total':>10}  Missing items")
    lines.append("-" * 65)
    for rank, sd in enumerate(store_totals, 1):
        missing = ", ".join(sd["missing"]) if sd["missing"] else "none"
        marker = "  <-- CHEAPEST" if rank == 1 else ""
        lines.append(f"  {rank:<3} {sd['store']:<30} ${sd['total']:>8.2f}  {missing}{marker}")
    lines.append("-" * 65)

    # Winner summary
    lines.append(f"\nWINNER: {cheapest['store']}")
    lines.append(f"Your estimated total bill: ${cheapest['total']:.2f}\n")
    lines.append(f"Itemised breakdown at {cheapest['store']}:")
    lines.append(f"  {'Item':<26} {'Price':>8}")
    lines.append("  " + "-" * 36)
    for item in normalized:
        price = cheapest["found"].get(item)
        if price is not None:
            lines.append(f"  {item.title():<26} ${price:>7.2f}")
        else:
            lines.append(f"  {item.title():<26}  NOT IN FLYER")
    lines.append("  " + "-" * 36)
    lines.append(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4: Get cheapest store (local fallback database)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_cheapest_store_local(items: list[str]) -> str:
    """
    Compare total grocery bill across stores using the built-in local price
    database (no internet required). Returns the store with the lowest total.

    Use this when the Flipp API is unavailable or you want instant results.
    Available items: milk, bread, eggs, butter, cheese, chicken, beef, rice,
    pasta, tomato sauce, apples, bananas, oranges, potatoes, onions, carrots,
    spinach, yogurt, orange juice, coffee, sugar, salt, olive oil, cereal, chips.

    Args:
        items: List of grocery item names to compare.

    Returns:
        Ranked store comparison and itemised breakdown at the cheapest store.
    """
    if not items:
        return "No items provided. Please supply a list of grocery items."

    normalized = [item.strip().lower() for item in items]
    comparison = compare_prices(normalized)
    results = comparison["results"]
    cheapest = comparison["cheapest"]
    not_found = comparison["not_found_anywhere"]

    lines = []
    if not_found:
        lines.append(f"Items not in local database: {', '.join(i.title() for i in not_found)}\n")

    # Ranked table
    lines.append(f"{'#':<4} {'Store':<22} {'Location':<16} {'Total':>9}  Missing")
    lines.append("-" * 65)
    for rank, r in enumerate(results, 1):
        missing = ", ".join(r["missing_items"]) if r["missing_items"] else "none"
        marker = "  <-- CHEAPEST" if rank == 1 else ""
        lines.append(
            f"  {rank:<3} {r['store']:<22} {r['location']:<16} ${r['total']:>8.2f}  {missing}{marker}"
        )
    lines.append("-" * 65)

    lines.append(f"\nWINNER: {cheapest['store']} ({cheapest['location']})")
    lines.append(f"Your estimated total bill: ${cheapest['total']:.2f}\n")
    lines.append(f"Itemised breakdown at {cheapest['store']}:")
    lines.append(f"  {'Item':<26} {'Price':>8}")
    lines.append("  " + "-" * 36)
    for item in normalized:
        price = cheapest["found_items"].get(item)
        if price is not None:
            lines.append(f"  {item.title():<26} ${price:>7.2f}")
        else:
            lines.append(f"  {item.title():<26}  NOT AVAILABLE")
    lines.append("  " + "-" * 36)
    lines.append(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 5: List available items in local database
# ---------------------------------------------------------------------------

@mcp.tool()
def list_available_items() -> str:
    """
    List all grocery items available in the local price database.
    Useful to know what items are supported before calling get_cheapest_store_local.

    Returns:
        Alphabetical list of all available item names.
    """
    items = sorted(get_available_items())
    lines = ["Items available in the local grocery database:\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"  {i:2}. {item.title()}")
    lines.append(f"\nTotal: {len(items)} items")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
