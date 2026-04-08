"""
Grocery Price Comparator — MCP Server
======================================
Exposes grocery price comparison as MCP tools so Claude (or any
MCP-compatible AI) can call them directly in conversation.

Run via entry point:   grocery-mcp
Or directly:           python -m grocery_price_comparator.server

Claude Desktop config  (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "grocery": {
          "command": "grocery-mcp",
          "env": {"ANTHROPIC_API_KEY": "sk-ant-..."}
        }
      }
    }
"""

from mcp.server.fastmcp import FastMCP
from .flipp_api import get_flyers, fetch_prices_for_list, build_store_totals
from .comparator import compare_prices, get_available_items, get_per_item_cheapest
from .agent import run_grocery_agent

mcp = FastMCP("Grocery Price Comparator")


@mcp.tool()
def get_nearby_stores(postal_code: str) -> str:
    """
    List grocery stores that have active flyers near a given postal or ZIP code.

    Args:
        postal_code: The user's postal code or ZIP code (e.g. "10001" or "M5V 3L9").
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


@mcp.tool()
def search_grocery_prices(postal_code: str, items: list[str]) -> str:
    """
    Fetch live flyer prices for a list of grocery items near a postal/ZIP code.

    Args:
        postal_code: The user's postal code or ZIP code.
        items: List of grocery item names (e.g. ["milk", "bread", "eggs"]).
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
            for offer in offers[:3]:
                lines.append(f"  {item.title():<24} {offer['merchant']:<28} ${offer['price']:>7.2f}")
        else:
            lines.append(f"  {item.title():<24} {'Not found on Flipp':<28}")
    return "\n".join(lines)


@mcp.tool()
def get_cheapest_store(postal_code: str, items: list[str]) -> str:
    """
    Compare total grocery bill across stores using live Flipp data and return
    the store with the minimum total bill.

    Args:
        postal_code: The user's postal code or ZIP code.
        items: List of grocery item names (e.g. ["milk", "bread", "eggs"]).
    """
    if not items:
        return "No items provided. Please supply a list of grocery items."

    normalized = [item.strip().lower() for item in items]

    try:
        prices_by_item = fetch_prices_for_list(normalized, postal_code)
        store_totals = build_store_totals(prices_by_item, normalized)
    except Exception as exc:
        return f"Error fetching live prices: {exc}\nUse get_cheapest_store_local instead."

    if not store_totals:
        return "No live prices found. Use get_cheapest_store_local for offline prices."

    cheapest = store_totals[0]
    lines = [f"Price comparison near '{postal_code}':\n"]
    lines.append(f"{'#':<4} {'Store':<30} {'Total':>10}  Missing items")
    lines.append("-" * 65)
    for rank, sd in enumerate(store_totals, 1):
        missing = ", ".join(sd["missing"]) if sd["missing"] else "none"
        marker = "  <-- CHEAPEST" if rank == 1 else ""
        lines.append(f"  {rank:<3} {sd['store']:<30} ${sd['total']:>8.2f}  {missing}{marker}")
    lines.append("-" * 65)
    lines.append(f"\nWINNER: {cheapest['store']}")
    lines.append(f"Your estimated total bill: ${cheapest['total']:.2f}\n")
    lines.append(f"  {'Item':<26} {'Price':>8}")
    lines.append("  " + "-" * 36)
    for item in normalized:
        price = cheapest["found"].get(item)
        lines.append(f"  {item.title():<26} ${price:>7.2f}" if price else f"  {item.title():<26}  NOT IN FLYER")
    lines.append("  " + "-" * 36)
    lines.append(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}")
    return "\n".join(lines)


@mcp.tool()
def get_cheapest_store_local(items: list[str]) -> str:
    """
    Compare total grocery bill using the built-in offline price database.
    No internet required. Use when Flipp API is unavailable.

    Available items: milk, bread, eggs, butter, cheese, chicken, beef, rice,
    pasta, tomato sauce, apples, bananas, oranges, potatoes, onions, carrots,
    spinach, yogurt, orange juice, coffee, sugar, salt, olive oil, cereal, chips.

    Args:
        items: List of grocery item names to compare.
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
    lines.append(f"{'#':<4} {'Store':<22} {'Location':<16} {'Total':>9}  Missing")
    lines.append("-" * 65)
    for rank, r in enumerate(results, 1):
        missing = ", ".join(r["missing_items"]) if r["missing_items"] else "none"
        marker = "  <-- CHEAPEST" if rank == 1 else ""
        lines.append(f"  {rank:<3} {r['store']:<22} {r['location']:<16} ${r['total']:>8.2f}  {missing}{marker}")
    lines.append("-" * 65)
    lines.append(f"\nWINNER: {cheapest['store']} ({cheapest['location']})")
    lines.append(f"Your estimated total bill: ${cheapest['total']:.2f}\n")
    lines.append(f"  {'Item':<26} {'Price':>8}")
    lines.append("  " + "-" * 36)
    for item in normalized:
        price = cheapest["found_items"].get(item)
        lines.append(f"  {item.title():<26} ${price:>7.2f}" if price else f"  {item.title():<26}  NOT AVAILABLE")
    lines.append("  " + "-" * 36)
    lines.append(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}")
    return "\n".join(lines)


@mcp.tool()
def list_available_items() -> str:
    """List all grocery items available in the local price database."""
    items = sorted(get_available_items())
    lines = ["Items available in the local grocery database:\n"]
    for i, item in enumerate(items, 1):
        lines.append(f"  {i:2}. {item.title()}")
    lines.append(f"\nTotal: {len(items)} items")
    return "\n".join(lines)


@mcp.tool()
def smart_grocery_advisor(postal_code: str, request: str) -> str:
    """
    AI-powered grocery shopping advisor. Uses an internal Claude agent to
    understand your natural language request, figure out what items you need,
    fetch live prices, and give personalised money-saving recommendations.

    No need to list items — just describe what you need in plain English:
      - "ingredients for spaghetti bolognese for 4 people"
      - "weekly breakfast and lunch staples"
      - "BBQ party food for 10 guests"

    Requires ANTHROPIC_API_KEY environment variable.

    Args:
        postal_code: Your postal or ZIP code (e.g. "10001" or "M5V 3L9").
        request: Natural language description of what you want to buy.
    """
    if not postal_code.strip():
        return "Please provide your postal or ZIP code."
    if not request.strip():
        return "Please describe what you want to buy."
    return run_grocery_agent(postal_code.strip(), request.strip())


def main():
    mcp.run()


if __name__ == "__main__":
    main()
