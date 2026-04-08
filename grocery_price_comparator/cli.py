"""
Grocery Price Comparator — Interactive CLI
==========================================
Run via entry point:  grocery-compare
Or directly:          python -m grocery_price_comparator.cli
"""

from .flipp_api import fetch_prices_for_list, build_store_totals, get_flyers
from .comparator import compare_prices, get_available_items, get_per_item_cheapest

SEPARATOR = "-" * 65


def print_header():
    print("\n" + "=" * 65)
    print("        GROCERY PRICE COMPARATOR  (powered by Flipp)")
    print("=" * 65)


def ask_postal_code() -> str:
    print("\nPlease enter your postal code or ZIP code.")
    print("  Examples:  M5V 3L9  (Canada)  |  10001  (USA)\n")
    while True:
        code = input("  Your pin / postal code: ").strip()
        if code:
            return code
        print("  Code cannot be empty. Please try again.")


def get_grocery_list_from_user() -> list[str]:
    print("\nEnter your grocery list (one item per line).")
    print("Type 'done' when finished.\n")
    grocery_list: list[str] = []
    while True:
        raw = input("  Item: ").strip()
        if not raw:
            continue
        if raw.lower() == "done":
            if not grocery_list:
                print("  List is empty — add at least one item first.")
                continue
            break
        grocery_list.append(raw.lower())
        print(f"    -> Added: {raw.title()}")
    return grocery_list


def display_stores_preview(postal_code: str):
    print(f"\n  Fetching store flyers near '{postal_code}' ...")
    try:
        flyers = get_flyers(postal_code)
    except Exception as exc:
        print(f"  Could not reach Flipp: {exc}")
        return
    if not flyers:
        print("  No flyers found for this location.")
        return
    merchants = sorted({f.get("merchant_name", "Unknown") for f in flyers})
    print(f"\n  Found {len(merchants)} store(s) with active flyers near you:")
    for m in merchants:
        print(f"    - {m}")
    print()


def display_results(store_totals: list[dict], grocery_list: list[str], prices_by_item: dict):
    if not store_totals:
        print("\n  No matching products were found on Flipp for your area.")
        return
    cheapest = store_totals[0]
    print(f"\n{SEPARATOR}")
    print("  TOTAL BILL COMPARISON  (stores that carry at least one item)")
    print(SEPARATOR)
    print(f"  {'#':<4} {'Store':<28} {'Total':>9}  {'Missing items'}")
    print("  " + "-" * 61)
    for rank, sd in enumerate(store_totals, 1):
        missing_label = ", ".join(i.title() for i in sd["missing"]) if sd["missing"] else "none"
        marker = " <-- CHEAPEST" if rank == 1 else ""
        print(f"  {rank:<4} {sd['store']:<28} ${sd['total']:>8.2f}  {missing_label}{marker}")
    print(SEPARATOR)
    print(f"\n  WINNER: {cheapest['store']}")
    print(f"  Your estimated total bill: ${cheapest['total']:.2f}\n")
    print(f"  {'Item':<26} {'Price':>8}")
    print("  " + "-" * 36)
    for item in grocery_list:
        price = cheapest["found"].get(item)
        print(f"  {item.title():<26} ${price:>7.2f}" if price else f"  {item.title():<26}  NOT IN FLYER")
    print("  " + "-" * 36)
    print(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}\n")
    print(f"{SEPARATOR}")
    print("  CHEAPEST STORE PER ITEM")
    print(SEPARATOR)
    print(f"  {'Item':<26} {'Best Store':<28} {'Price':>8}")
    print("  " + "-" * 65)
    for item in grocery_list:
        offers = prices_by_item.get(item, [])
        if offers:
            best = offers[0]
            print(f"  {item.title():<26} {best['merchant']:<28} ${best['price']:>7.2f}")
        else:
            print(f"  {item.title():<26} {'Not found on Flipp':<28}")
    print(SEPARATOR + "\n")


def display_local_fallback(comparison: dict, grocery_list: list[str]):
    results = comparison["results"]
    cheapest = comparison["cheapest"]
    not_found = comparison["not_found_anywhere"]
    print("  [Using local sample data — connect to internet for live Flipp prices]\n")
    if not_found:
        print(f"  Items not in local DB: {', '.join(i.title() for i in not_found)}\n")
    print(f"{SEPARATOR}")
    print("  TOTAL BILL COMPARISON  (local store database)")
    print(SEPARATOR)
    print(f"  {'#':<4} {'Store':<22} {'Location':<15} {'Total':>9}  {'Missing'}")
    print("  " + "-" * 60)
    for rank, r in enumerate(results, 1):
        missing_label = ", ".join(i.title() for i in r["missing_items"]) if r["missing_items"] else "none"
        marker = " <-- CHEAPEST" if rank == 1 else ""
        print(f"  {rank:<4} {r['store']:<22} {r['location']:<15} ${r['total']:>8.2f}  {missing_label}{marker}")
    print(SEPARATOR)
    print(f"\n  WINNER: {cheapest['store']} ({cheapest['location']})")
    print(f"  Your estimated total bill: ${cheapest['total']:.2f}\n")
    print(f"  {'Item':<26} {'Price':>8}")
    print("  " + "-" * 36)
    for item in grocery_list:
        price = cheapest["found_items"].get(item)
        print(f"  {item.title():<26} ${price:>7.2f}" if price else f"  {item.title():<26}  NOT AVAILABLE")
    print("  " + "-" * 36)
    print(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}\n")
    per_item = get_per_item_cheapest(grocery_list)
    print(f"{SEPARATOR}")
    print("  CHEAPEST STORE PER ITEM  (local data)")
    print(SEPARATOR)
    print(f"  {'Item':<26} {'Store':<22} {'Price':>8}")
    print("  " + "-" * 60)
    for item in grocery_list:
        info = per_item.get(item)
        print(f"  {item.title():<26} {info['store']:<22} ${info['price']:>7.2f}" if info else f"  {item.title():<26} {'Not in local database':<22}")
    print(SEPARATOR + "\n")


def main():
    print_header()
    postal_code = ask_postal_code()
    display_stores_preview(postal_code)

    while True:
        print("Options:")
        print("  1. Enter grocery list and compare prices")
        print("  2. Change postal / pin code")
        print("  3. Exit")
        choice = input("\nChoose an option (1-3): ").strip()

        if choice == "1":
            grocery_list = get_grocery_list_from_user()
            print(f"\n  Fetching live prices for {len(grocery_list)} item(s) near '{postal_code}' ...")
            print("  (This may take a few seconds)\n")
            flipp_ok = True
            try:
                prices_by_item = fetch_prices_for_list(grocery_list, postal_code)
                store_totals = build_store_totals(prices_by_item, grocery_list)
                if not store_totals:
                    raise RuntimeError("No results returned from Flipp (API may be unreachable)")
            except Exception as exc:
                flipp_ok = False
                print(f"  Could not reach Flipp API: {exc}")
                print("  Falling back to local store price database...\n")
            if flipp_ok:
                display_results(store_totals, grocery_list, prices_by_item)
            else:
                display_local_fallback(compare_prices(grocery_list), grocery_list)
            again = input("  Compare another list? (yes/no): ").strip().lower()
            if again not in ("yes", "y"):
                break

        elif choice == "2":
            postal_code = ask_postal_code()
            display_stores_preview(postal_code)
        elif choice == "3":
            break
        else:
            print("  Invalid option. Please choose 1, 2, or 3.\n")

    print("\nThank you for using Grocery Price Comparator! Happy saving!\n")


if __name__ == "__main__":
    main()
