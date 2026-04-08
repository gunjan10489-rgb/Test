"""
Grocery Price Comparator  (Flipp edition)
=========================================
Enter your postal / ZIP code and grocery list.
We fetch live flyer prices from stores near you via Flipp
and tell you which store gives the cheapest total bill.
"""

import sys
from flipp_api import fetch_prices_for_list, build_store_totals, get_flyers

SEPARATOR = "-" * 65


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def print_header():
    print("\n" + "=" * 65)
    print("        GROCERY PRICE COMPARATOR  (powered by Flipp)")
    print("=" * 65)


def ask_postal_code() -> str:
    """Prompt until the user gives a non-empty postal / ZIP code."""
    print("\nPlease enter your postal code or ZIP code.")
    print("  Examples:  M5V 3L9  (Canada)  |  10001  (USA)\n")
    while True:
        code = input("  Your pin / postal code: ").strip()
        if code:
            return code
        print("  Code cannot be empty. Please try again.")


def get_grocery_list_from_user() -> list[str]:
    """Prompt user to enter grocery items one per line."""
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
        item = raw.lower()
        grocery_list.append(item)
        print(f"    -> Added: {raw.title()}")
    return grocery_list


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def display_stores_preview(postal_code: str):
    """Show which store flyers are available near the postal code."""
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


def display_results(
    store_totals: list[dict],
    grocery_list: list[str],
    prices_by_item: dict,
):
    if not store_totals:
        print("\n  No matching products were found on Flipp for your area.")
        return

    cheapest = store_totals[0]

    # ---- Ranked table ----
    print(f"\n{SEPARATOR}")
    print("  TOTAL BILL COMPARISON  (stores that carry at least one item)")
    print(SEPARATOR)
    print(f"  {'#':<4} {'Store':<28} {'Total':>9}  {'Missing items'}")
    print("  " + "-" * 61)

    for rank, sd in enumerate(store_totals, 1):
        missing_label = (
            ", ".join(i.title() for i in sd["missing"]) if sd["missing"] else "none"
        )
        marker = " <-- CHEAPEST" if rank == 1 else ""
        print(
            f"  {rank:<4} {sd['store']:<28} ${sd['total']:>8.2f}  "
            f"{missing_label}{marker}"
        )

    print(SEPARATOR)

    # ---- Cheapest store breakdown ----
    print(f"\n  WINNER: {cheapest['store']}")
    print(f"  Your estimated total bill: ${cheapest['total']:.2f}\n")

    print(f"  Itemised breakdown at {cheapest['store']}:")
    print(f"  {'Item':<26} {'Price':>8}")
    print("  " + "-" * 36)
    for item in grocery_list:
        price = cheapest["found"].get(item)
        if price is not None:
            print(f"  {item.title():<26} ${price:>7.2f}")
        else:
            print(f"  {item.title():<26}  NOT IN FLYER")
    print("  " + "-" * 36)
    print(f"  {'TOTAL':<26} ${cheapest['total']:>7.2f}\n")

    # ---- Per-item cheapest ----
    print(f"{SEPARATOR}")
    print("  CHEAPEST STORE PER ITEM  (mix & match guide)")
    print(SEPARATOR)
    print(f"  {'Item':<26} {'Best Store':<28} {'Price':>8}")
    print("  " + "-" * 65)
    for item in grocery_list:
        offers = prices_by_item.get(item, [])
        if offers:
            best = offers[0]
            print(
                f"  {item.title():<26} {best['merchant']:<28} ${best['price']:>7.2f}"
            )
        else:
            print(f"  {item.title():<26} {'Not found on Flipp':<28}")
    print(SEPARATOR + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print_header()

    # --- Step 1: get postal code once per session ---
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

            print(
                f"\n  Fetching live prices for {len(grocery_list)} item(s) "
                f"near '{postal_code}' from Flipp ..."
            )
            print("  (This may take a few seconds)\n")

            try:
                prices_by_item = fetch_prices_for_list(grocery_list, postal_code)
            except Exception as exc:
                print(f"\n  Error contacting Flipp API: {exc}")
                print("  Please check your internet connection and try again.\n")
                continue

            store_totals = build_store_totals(prices_by_item, grocery_list)
            display_results(store_totals, grocery_list, prices_by_item)

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
