"""
Grocery Agent — Internal LLM-powered agent
============================================
Uses the Claude API (claude-opus-4-6) as an internal agent.
Understands natural language requests, normalises grocery items,
fetches live/local prices, and gives personalised recommendations.

Requires:  ANTHROPIC_API_KEY environment variable
"""

import json
import os
import anthropic
from .flipp_api import fetch_prices_for_list, build_store_totals
from .comparator import compare_prices

SYSTEM_PROMPT = """You are an expert grocery shopping assistant with access to
live store price data. Your job is to help users find the cheapest place to buy
their groceries.

When given a shopping request you must:
1. Identify and normalise the grocery items the user needs.
   - Map natural language to simple item names (e.g. "a dozen eggs" → "eggs",
     "whole milk" → "milk", "spaghetti bolognese ingredients" → ["pasta",
     "tomato sauce", "beef", "onions", "cheese"]).
   - Use ONLY items likely to appear in a grocery flyer.

2. Call fetch_live_prices to get real prices from nearby stores.
   - If the live API fails or returns no results, call fetch_local_prices.

3. Analyse the results and deliver a clear, actionable recommendation:
   - State the cheapest single store and total bill.
   - If buying from two stores saves more than 10 % vs. the cheapest single
     store, suggest the split and show the saving.
   - Flag any items that are significantly more expensive (>30 %) at one store.
   - Keep the response concise — bullet points are fine.

Always be friendly, practical, and focused on saving the user money."""

AGENT_TOOLS = [
    {
        "name": "fetch_live_prices",
        "description": (
            "Search the Flipp API for live grocery flyer prices near a postal/ZIP code. "
            "Returns per-store totals and per-item prices. "
            "Use this first; fall back to fetch_local_prices only if this returns no results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Normalised grocery item names (lowercase).",
                },
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
    {
        "name": "fetch_local_prices",
        "description": (
            "Fetch prices from the built-in offline store database (no internet needed). "
            "Covers 5 sample stores and 25 common items. "
            "Use only when fetch_live_prices returns no results."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Grocery item names to look up (lowercase).",
                },
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
]


def _run_fetch_live(items: list[str], postal_code: str) -> str:
    try:
        prices = fetch_prices_for_list(items, postal_code)
        totals = build_store_totals(prices, items)
        if not totals:
            return json.dumps({"error": "No live prices found — Flipp API returned no results."})
        return json.dumps(
            {
                "source": "flipp_live",
                "postal_code": postal_code,
                "store_totals": [
                    {
                        "store": t["store"],
                        "total": t["total"],
                        "found_items": t["found"],
                        "missing_items": t["missing"],
                    }
                    for t in totals
                ],
            },
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": f"Flipp API error: {exc}"})


def _run_fetch_local(items: list[str]) -> str:
    comparison = compare_prices(items)
    return json.dumps(
        {
            "source": "local_database",
            "store_totals": [
                {
                    "store": r["store"],
                    "location": r["location"],
                    "total": r["total"],
                    "found_items": r["found_items"],
                    "missing_items": r["missing_items"],
                }
                for r in comparison["results"]
            ],
            "items_not_found_anywhere": comparison["not_found_anywhere"],
        },
        indent=2,
    )


def _execute_tool(name: str, tool_input: dict, postal_code: str) -> str:
    items = [i.strip().lower() for i in tool_input.get("items", [])]
    if name == "fetch_live_prices":
        return _run_fetch_live(items, postal_code)
    if name == "fetch_local_prices":
        return _run_fetch_local(items)
    return json.dumps({"error": f"Unknown tool: {name}"})


def run_grocery_agent(postal_code: str, user_request: str) -> str:
    """
    Run the internal Claude agent for a grocery shopping request.

    Args:
        postal_code: User's postal or ZIP code.
        user_request: Free-form request, e.g. "ingredients for a BBQ for 6 people".

    Returns:
        Claude's natural-language recommendation with price comparisons.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "ANTHROPIC_API_KEY is not set. "
            "Please set it to use the smart grocery advisor.\n"
            "Tip: export ANTHROPIC_API_KEY='sk-ant-...'"
        )

    client = anthropic.Anthropic(api_key=api_key)

    messages = [
        {
            "role": "user",
            "content": (
                f"My postal/ZIP code is: {postal_code}\n"
                f"Shopping request: {user_request}"
            ),
        }
    ]

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=AGENT_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next(
                (block.text for block in response.content if block.type == "text"),
                "No response generated.",
            )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = _execute_tool(block.name, block.input, postal_code)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Agent stopped unexpectedly. Please try again."
