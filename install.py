#!/usr/bin/env python3
"""
Grocery Price Comparator — One-Command Installer
=================================================
Installs the package and wires it into Claude Desktop automatically.

Usage:
    python install.py

What it does:
  1. Installs the grocery-price-comparator package (pip install -e .)
  2. Locates your Claude Desktop config file
  3. Adds the grocery MCP server to the config
  4. Saves your ANTHROPIC_API_KEY so the AI advisor works
  5. Tells you to restart Claude Desktop — then you're live!
"""

import json
import os
import shutil
import subprocess
import sys


# ---------------------------------------------------------------------------
# Colours (graceful fallback on Windows without colorama)
# ---------------------------------------------------------------------------

def _c(code: str, text: str) -> str:
    if sys.platform == "win32" and not os.environ.get("WT_SESSION"):
        return text
    return f"\033[{code}m{text}\033[0m"

def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def cyan(t):   return _c("36", t)
def bold(t):   return _c("1",  t)
def red(t):    return _c("31", t)


# ---------------------------------------------------------------------------
# Claude Desktop config locations
# ---------------------------------------------------------------------------

CLAUDE_CONFIG_PATHS = {
    "darwin": os.path.expanduser(
        "~/Library/Application Support/Claude/claude_desktop_config.json"
    ),
    "win32": os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "Claude", "claude_desktop_config.json",
    ),
    "linux": os.path.expanduser("~/.config/Claude/claude_desktop_config.json"),
}


def get_config_path() -> str | None:
    platform = "linux" if sys.platform.startswith("linux") else sys.platform
    return CLAUDE_CONFIG_PATHS.get(platform)


# ---------------------------------------------------------------------------
# Step 1 — install the package
# ---------------------------------------------------------------------------

def install_package():
    print(bold("\n[1/4] Installing grocery-price-comparator..."))
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(red("  pip install failed:\n") + result.stderr)
        sys.exit(1)
    print(green("  Package installed successfully."))


# ---------------------------------------------------------------------------
# Step 2 — locate the grocery-mcp command
# ---------------------------------------------------------------------------

def find_mcp_command() -> list[str]:
    """Return the command array to start the MCP server."""
    cmd = shutil.which("grocery-mcp")
    if cmd:
        print(green(f"  Found entry point: {cmd}"))
        return [cmd]
    # Fallback: run as module
    fallback = [sys.executable, "-m", "grocery_price_comparator.server"]
    print(yellow(f"  Entry point not in PATH, using: {' '.join(fallback)}"))
    return fallback


# ---------------------------------------------------------------------------
# Step 3 — get ANTHROPIC_API_KEY
# ---------------------------------------------------------------------------

def get_api_key() -> str | None:
    existing = os.environ.get("ANTHROPIC_API_KEY", "")
    if existing:
        print(green(f"  Found ANTHROPIC_API_KEY in environment ({existing[:8]}...)."))
        use = input("  Use this key? (yes/no): ").strip().lower()
        if use in ("yes", "y", ""):
            return existing

    print(
        "\n  The " + cyan("smart_grocery_advisor") + " tool uses Claude AI internally."
    )
    print("  Get your key at: https://console.anthropic.com/settings/keys\n")
    key = input("  Paste your ANTHROPIC_API_KEY (or press Enter to skip): ").strip()
    if key and not key.startswith("sk-ant-"):
        print(yellow("  Warning: key doesn't look like a valid Anthropic key (should start with sk-ant-)."))
    return key or None


# ---------------------------------------------------------------------------
# Step 4 — write Claude Desktop config
# ---------------------------------------------------------------------------

def configure_claude_desktop(mcp_cmd: list[str], api_key: str | None):
    print(bold("\n[4/4] Configuring Claude Desktop..."))

    config_path = get_config_path()

    if not config_path:
        print(yellow("  Could not detect your OS config path."))
        config_path = input("  Enter the full path to claude_desktop_config.json: ").strip()

    # Load existing config or start fresh
    config: dict = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            print(f"  Loaded existing config: {config_path}")
        except (json.JSONDecodeError, OSError):
            print(yellow(f"  Existing config unreadable — will create a fresh one."))

    # Build the MCP server entry
    server_entry: dict = {
        "command": mcp_cmd[0],
        "args": mcp_cmd[1:],
    }
    if api_key:
        server_entry["env"] = {"ANTHROPIC_API_KEY": api_key}

    # Merge into config
    config.setdefault("mcpServers", {})
    already_exists = "grocery" in config["mcpServers"]
    config["mcpServers"]["grocery"] = server_entry

    # Ensure directory exists
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    action = "Updated" if already_exists else "Added"
    print(green(f"  {action} 'grocery' MCP server in: {config_path}"))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(api_key: str | None):
    print("\n" + "=" * 60)
    print(bold(green("  Grocery Price Comparator installed successfully!")))
    print("=" * 60)

    print(f"""
  {bold("Next step:")}
  Restart Claude Desktop — the grocery tools will be available.

  {bold("Tools you can use in Claude:")}
    • {cyan("get_nearby_stores")}         — find stores near your location
    • {cyan("get_cheapest_store")}        — compare prices (live Flipp data)
    • {cyan("get_cheapest_store_local")}  — compare prices (offline)
    • {cyan("search_grocery_prices")}     — price lookup per item
    • {cyan("list_available_items")}      — see offline database items
    • {cyan("smart_grocery_advisor")}     — AI-powered natural language advisor
""")

    if not api_key:
        print(
            yellow("  Note: smart_grocery_advisor needs ANTHROPIC_API_KEY.\n")
            + "  Set it in your Claude Desktop config or run this installer again.\n"
        )

    print(f"""  {bold("Example prompts for Claude:")}
    "What stores are near postal code 10001?"
    "Compare prices for milk, eggs, bread near 10001"
    "I want to make pasta bolognese for 4 near M5V 3L9"

  {bold("CLI commands (also available):")}
    grocery-compare     ← interactive terminal app
    grocery-mcp         ← start MCP server manually
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(bold(cyan("\n  Grocery Price Comparator — Installer\n")))

    # Step 1
    install_package()

    # Step 2
    print(bold("\n[2/4] Locating grocery-mcp command..."))
    mcp_cmd = find_mcp_command()

    # Step 3
    print(bold("\n[3/4] ANTHROPIC_API_KEY setup..."))
    api_key = get_api_key()

    # Step 4
    configure_claude_desktop(mcp_cmd, api_key)

    # Done
    print_summary(api_key)


if __name__ == "__main__":
    main()
