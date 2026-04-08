"""
grocery-price-comparator
========================
Compare grocery prices across local stores using live Flipp flyer data,
with an optional AI-powered shopping advisor (powered by Claude).

Quick start
-----------
    # As a CLI
    grocery-compare

    # As an MCP server (for Claude Desktop)
    grocery-mcp

    # As a library
    from grocery_price_comparator import run_grocery_agent, compare_prices

    result = run_grocery_agent("10001", "ingredients for pasta night")
    print(result)
"""

from .comparator import compare_prices, get_available_items, get_per_item_cheapest
from .flipp_api import fetch_prices_for_list, build_store_totals, get_flyers
from .agent import run_grocery_agent

__version__ = "1.0.0"
__all__ = [
    "compare_prices",
    "get_available_items",
    "get_per_item_cheapest",
    "fetch_prices_for_list",
    "build_store_totals",
    "get_flyers",
    "run_grocery_agent",
]
