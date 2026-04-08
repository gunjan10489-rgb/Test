"""
Grocery Price Comparator — FastAPI REST Backend
================================================
Exposes all grocery tools as HTTP endpoints so the mobile app
(and any other client) can call them.

Run:
    grocery-api                          # via installed entry point
    uvicorn grocery_price_comparator.api:app --reload   # dev mode

Endpoints:
    GET  /                     health check
    GET  /items                list offline database items
    POST /nearby-stores        stores near a postal code (Flipp)
    POST /compare              live price comparison (Flipp)
    POST /compare-local        offline price comparison
    POST /smart-advise         AI agent (requires ANTHROPIC_API_KEY)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .flipp_api import get_flyers, fetch_prices_for_list, build_store_totals
from .comparator import compare_prices, get_available_items
from .agent import run_grocery_agent

app = FastAPI(
    title="Grocery Price Comparator",
    description="Compare grocery prices across local stores using live Flipp data and AI.",
    version="1.0.0",
)

# Allow requests from the Expo mobile app (any origin in dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PostalRequest(BaseModel):
    postal_code: str


class CompareRequest(BaseModel):
    postal_code: str
    items: list[str]


class AdvisorRequest(BaseModel):
    postal_code: str
    request: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return {"status": "ok", "service": "Grocery Price Comparator API"}


@app.get("/items")
def list_items():
    """Return all items available in the offline local database."""
    return {"items": sorted(get_available_items())}


@app.post("/nearby-stores")
def nearby_stores(req: PostalRequest):
    """Return stores with active Flipp flyers near a postal/ZIP code."""
    try:
        flyers = get_flyers(req.postal_code)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Flipp API error: {exc}")

    merchants = sorted({f.get("merchant_name", "Unknown") for f in flyers})
    return {
        "postal_code": req.postal_code,
        "stores": merchants,
        "count": len(merchants),
    }


@app.post("/compare")
def compare_live(req: CompareRequest):
    """
    Compare grocery prices using live Flipp flyer data.
    Returns store totals ranked cheapest first.
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="items list cannot be empty")

    normalized = [i.strip().lower() for i in req.items]

    try:
        prices_by_item = fetch_prices_for_list(normalized, req.postal_code)
        store_totals = build_store_totals(prices_by_item, normalized)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Flipp API error: {exc}")

    if not store_totals:
        raise HTTPException(
            status_code=404,
            detail="No prices found on Flipp for this location. Try /compare-local.",
        )

    # Build per-item cheapest map
    per_item_cheapest = {}
    for item in normalized:
        offers = prices_by_item.get(item, [])
        per_item_cheapest[item] = offers[0] if offers else None

    return {
        "source": "flipp_live",
        "postal_code": req.postal_code,
        "items": normalized,
        "store_totals": store_totals,
        "cheapest": store_totals[0],
        "per_item_cheapest": per_item_cheapest,
    }


@app.post("/compare-local")
def compare_local(req: CompareRequest):
    """
    Compare grocery prices using the offline local database.
    No internet required for the price data itself.
    """
    if not req.items:
        raise HTTPException(status_code=400, detail="items list cannot be empty")

    normalized = [i.strip().lower() for i in req.items]
    result = compare_prices(normalized)

    return {
        "source": "local_database",
        "items": normalized,
        "store_totals": result["results"],
        "cheapest": result["cheapest"],
        "not_found": result["not_found_anywhere"],
    }


@app.post("/smart-advise")
def smart_advise(req: AdvisorRequest):
    """
    AI-powered grocery advisor. Understands natural language,
    figures out what items you need, fetches prices, recommends
    the cheapest store. Requires ANTHROPIC_API_KEY env var.
    """
    if not req.postal_code.strip():
        raise HTTPException(status_code=400, detail="postal_code is required")
    if not req.request.strip():
        raise HTTPException(status_code=400, detail="request is required")

    response = run_grocery_agent(req.postal_code.strip(), req.request.strip())
    return {
        "postal_code": req.postal_code,
        "request": req.request,
        "recommendation": response,
    }


def main():
    import uvicorn
    uvicorn.run("grocery_price_comparator.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
