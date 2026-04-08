"""
Grocery Price Comparator
========================
Compare your grocery list prices across multiple local stores
and find the cheapest option.
"""

from grocery_comparator import (
    compare_prices,
    get_available_items,
    get_per_item_cheapest,
)

SEPARATOR = "-" * 60


def print_header():
    print("\n" + "=" * 60)
    print("       GROCERY PRICE COMPARATOR")
    print("=" * 60)


def print_available_items():
    items = sorted(get_available_items())
    print("\nAvailable items in our database:")
    for i, item in enumerate(items, 1):
        print(f"  {i:2}. {item.title()}")
    print()


def get_grocery_list_from_user() -> list[str]:
    """Prompt user to enter grocery items interactively."""
    print("\nEnter your grocery list (one item per line).")
    print("Type 'done' when finished, or 'list' to see all available items.\n")

    grocery_list = []
    while True:
        raw = input("  Item: ").strip()
        if not raw:
            continue
        if raw.lower() == "done":
            break
        if raw.lower() == "list":
            print_available_items()
            continue
        grocery_list.append(raw.lower())
        print(f"    -> Added: {raw.title()}")

    return grocery_list


def display_comparison_results(comparison: dict):
    results = comparison["results"]
    cheapest = comparison["cheapest"]
    not_found = comparison["not_found_anywhere"]

    if not_found:
        print(f"\n  Items not found in any store: {', '.join(i.title() for i in not_found)}")

    print(f"\n{SEPARATOR}")
    print(f"  PRICE COMPARISON ACROSS ALL STORES")
    print(SEPARATOR)
    print(f"  {'Store':<18} {'Location':<15} {'Total':>10}  {'Missing'}")
    print(SEPARATOR)

    for r in results:
        missing_label = ", ".join(i.title() for i in r["missing_items"]) if r["missing_items"] else "None"
        marker = " <-- CHEAPEST" if r["store"] == cheapest["store"] else ""
        print(f"  {r['store']:<18} {r['location']:<15} ${r['total']:>8.2f}  {missing_label}{marker}")

    print(SEPARATOR)

    print(f"\n  WINNER: {cheapest['store']} ({cheapest['location']})")
    print(f"  Your total bill: ${cheapest['total']:.2f}\n")

    print(f"  Itemised breakdown at {cheapest['store']}:")
    print(f"  {'Item':<22} {'Price':>8}")
    print("  " + "-" * 32)
    for item, price in sorted(cheapest["found_items"].items()):
        print(f"  {item.title():<22} ${price:>7.2f}")
    if cheapest["missing_items"]:
        for item in cheapest["missing_items"]:
            print(f"  {item.title():<22}  NOT AVAILABLE")
    print("  " + "-" * 32)
    print(f"  {'TOTAL':<22} ${cheapest['total']:>7.2f}\n")


def display_per_item_cheapest(grocery_list: list[str]):
    per_item = get_per_item_cheapest(grocery_list)
    print(f"\n{SEPARATOR}")
    print("  CHEAPEST STORE PER ITEM")
    print(SEPARATOR)
    print(f"  {'Item':<22} {'Store':<18} {'Price':>8}")
    print("  " + "-" * 50)
    for item, info in sorted(per_item.items()):
        if info:
            print(f"  {item.title():<22} {info['store']:<18} ${info['price']:>7.2f}")
        else:
            print(f"  {item.title():<22} {'Not found anywhere':<18}")
    print(SEPARATOR + "\n")


def main():
    print_header()

    while True:
        print("\nOptions:")
        print("  1. Enter grocery list and compare prices")
        print("  2. View available items in database")
        print("  3. Exit")

        choice = input("\nChoose an option (1-3): ").strip()

        if choice == "1":
            grocery_list = get_grocery_list_from_user()

            if not grocery_list:
                print("\n  No items entered. Please try again.")
                continue

            print(f"\n  Comparing prices for {len(grocery_list)} item(s)...")
            comparison = compare_prices(grocery_list)

            display_comparison_results(comparison)
            display_per_item_cheapest(grocery_list)

            again = input("  Compare another list? (yes/no): ").strip().lower()
            if again not in ("yes", "y"):
                break

        elif choice == "2":
            print_available_items()

        elif choice == "3":
            break

        else:
            print("  Invalid option. Please choose 1, 2, or 3.")

    print("\nThank you for using Grocery Price Comparator! Happy saving!\n")


if __name__ == "__main__":
    main()
