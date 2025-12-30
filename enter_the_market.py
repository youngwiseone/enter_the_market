import os
import csv
import random
from datetime import datetime

import pygame

# Import shared styling constants and market logic
import style
import screensaver
from style import *  # bring all constants into local namespace for backwards compatibility
import market
from market import week_number  # use shared week calculation

"""
retro_market.py
----------------

This module provides a more authentic 1990s PC look for the market trading game.
Users can buy goods from a shop, sell items from their own inventory and watch
their cash balance change over time.  The interface has been reworked to
simulate a Windows 95–style application with side‑by‑side scrollable tables
and a simple graph showing cash over days.  Data persists via CSV files.
"""

# -------------------------------------------------------------
# Configuration and constants
# -------------------------------------------------------------

WIDTH, HEIGHT = 1200, 720
FPS = 60

DATA_DIR = "data"
RES_DIR = "resources"

DEFAULT_STARTING_CASH = 100
DEFAULT_CAPACITY = 5           # starting storage capacity (units)
CAPACITY_STEP = 1              # change in storage capacity per adjustment

# Price dynamics
VOLATILITY = 0.18              # daily price movement magnitude (relative)
SPREAD = 0.90                  # player's sell price = shop buy price * SPREAD
RESTOCK_MIN, RESTOCK_MAX = 0, 8  # new shop stock each day

# Rent is paid weekly (every Sunday). Rent cost equals current storage capacity
# (i.e. $1 per unit of space you can hold).
BILL_INTERVAL = 7

# Retro colour palette
# Classic Windows 95 greys and blues
COLOR_DESKTOP = (192, 192, 192)
COLOR_WINDOW = (212, 208, 200)
COLOR_TITLE_BAR = (0, 0, 128)
COLOR_TITLE_TEXT = (255, 255, 255)
COLOR_WINDOW_BORDER_LIGHT = (255, 255, 255)
COLOR_WINDOW_BORDER_DARK = (128, 128, 128)
COLOR_CONTROL_BACKGROUND = (236, 236, 236)
COLOR_CONTROL_BORDER_LIGHT = (255, 255, 255)
COLOR_CONTROL_BORDER_DARK = (128, 128, 128)
COLOR_CONTROL_TEXT = (0, 0, 0)
COLOR_TABLE_HEADER = (0, 0, 128)
COLOR_TABLE_HEADER_TEXT = (255, 255, 255)
COLOR_ROW_LIGHT = (224, 224, 224)
COLOR_ROW_DARK = (192, 192, 192)
COLOR_GRAPH_BACKGROUND = (255, 255, 255)
COLOR_GRAPH_LINE = (0, 0, 255)
COLOR_TOAST = (200, 50, 50)

# Chat colours (terminal style)
COLOR_CHAT_BACKGROUND = (0, 0, 0)
COLOR_CHAT_TEXT = (0, 255, 0)

# Chat formatting
CHAT_LINE_HEIGHT = 16  # pixel height per chat line

# Layout constants
MARGIN = 20
SPACING = 10
TABLE_WIDTH = (WIDTH - 2 * MARGIN - SPACING * 2) // 2
TABLE_HEIGHT = 300
REPORT_HEIGHT = 500
HEADER_HEIGHT = 30
SCROLL_BUTTON_HEIGHT = 20
ROW_HEIGHT = 26
# The number of rows visible in each table before scrolling.  We reserve space
# for a column header row in addition to the coloured header bar and scroll
# buttons.  The 20 pixels correspond to the column header row.
VISIBLE_ROWS = (TABLE_HEIGHT - HEADER_HEIGHT - 20 - 2 * SCROLL_BUTTON_HEIGHT) // ROW_HEIGHT
# Height of the chat area beneath the tables.  The graph from the earlier
# version has been replaced with a chat/terminal area for messages and tips.
CHAT_HEIGHT = 150
HUD_HEIGHT = 50
TITLE_BAR_HEIGHT = 30

# Height of the cash history graph inside the chat area.  The chat area is
# divided into a graph portion and a command-line/message portion.  Keep
# GRAPH_HEIGHT relatively small so chat messages still have space.
GRAPH_HEIGHT = 60

# Column widths for tables (sum should fit within table width minus scroll bar)
# Shop columns: image, sku, description, quantity, current price, average buy price,
# input field, button.  Total width must be <= table_panel.width - scroll bar.
SHOP_COL_WIDTHS = [24, 60, 140, 60, 70, 70, 50, 50]
# Inventory columns: image, sku, description, avg cost, quantity, sell price,
# input field, button.
INV_COL_WIDTHS = [24, 60, 140, 60, 70, 70, 60, 50]
#SHOP_HEADERS = ["Img", "SKU", "Description", "In Stock", "Price", "Avg_Price", "Qty", ""]
SHOP_HEADERS = ["Img", "SKU", "Description", "Avg_Price", "Buy_price", "In Stock",  "Qty", ""]
INV_HEADERS = ["Img", "SKU", "Description", "Avg_cost", "Sell_price", "SOH", "Qty", ""]


def refresh_style_from_module():
    """Refresh locally-cached style constants from the style module.

    This project historically keeps many UI constants as module-level globals
    (COLOR_*, UI border radius, etc.). When a theme / UI skin is changed at
    runtime, we update the *style module* and then call this function so the
    new values take effect immediately.
    """
    global COLOR_DESKTOP, COLOR_WINDOW, COLOR_TITLE_BAR, COLOR_TITLE_TEXT
    global COLOR_WINDOW_BORDER_LIGHT, COLOR_WINDOW_BORDER_DARK
    global COLOR_CONTROL_BACKGROUND, COLOR_CONTROL_BORDER_LIGHT, COLOR_CONTROL_BORDER_DARK
    global COLOR_CONTROL_TEXT, COLOR_TABLE_HEADER, COLOR_TABLE_HEADER_TEXT
    global COLOR_ROW_LIGHT, COLOR_ROW_DARK
    global COLOR_GRAPH_BACKGROUND, COLOR_GRAPH_LINE, COLOR_TOAST
    global COLOR_CHAT_BACKGROUND, COLOR_CHAT_TEXT
    global UI_BORDER_RADIUS

    # Only override if the attribute exists in style.py
    for name in [
        "COLOR_DESKTOP","COLOR_WINDOW","COLOR_TITLE_BAR","COLOR_TITLE_TEXT",
        "COLOR_WINDOW_BORDER_LIGHT","COLOR_WINDOW_BORDER_DARK",
        "COLOR_CONTROL_BACKGROUND","COLOR_CONTROL_BORDER_LIGHT","COLOR_CONTROL_BORDER_DARK",
        "COLOR_CONTROL_TEXT","COLOR_TABLE_HEADER","COLOR_TABLE_HEADER_TEXT",
        "COLOR_ROW_LIGHT","COLOR_ROW_DARK",
        "COLOR_GRAPH_BACKGROUND","COLOR_GRAPH_LINE","COLOR_TOAST",
        "COLOR_CHAT_BACKGROUND","COLOR_CHAT_TEXT",
    ]:
        if hasattr(style, name):
            globals()[name] = getattr(style, name)

    UI_BORDER_RADIUS = getattr(style, "UI_BORDER_RADIUS", 0)


# Apply the default theme/skin values from style.py on startup.
refresh_style_from_module()

# Day names (Day 1 = Monday)
DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# CSV file paths
ITEMS_CSV = os.path.join(DATA_DIR, "items.csv")
SHOP_CSV = os.path.join(DATA_DIR, "shop.csv")
INV_CSV = os.path.join(DATA_DIR, "inventory.csv")
TXN_CSV = os.path.join(DATA_DIR, "transactions.csv")
PLAYER_CSV = os.path.join(DATA_DIR, "player.csv")

# Path to the cosmetics catalogue.  Cosmetics such as themes, screensavers
# and UI skins are defined in this CSV with columns: name, type,
# unlocked (true/false) and price.  It is created on first run if
# missing by seed_cosmetics_if_missing().
COSMETICS_CSV = os.path.join(DATA_DIR, "cosmetics.csv")

# News CSV file paths
NEWS_CSV = os.path.join(DATA_DIR, "news.csv")
PREVIOUS_NEWS_CSV = os.path.join(DATA_DIR, "previous_news.csv")

# Weekly rollups (append-only)
WEEKLY_REPORT_CSV = os.path.join(DATA_DIR, "weekly_report.csv")

# -------------------------------------------------------------
# CSV and data helpers
# -------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """Ensure the directory exists."""
    os.makedirs(path, exist_ok=True)


def read_csv_dicts(path: str):
    """Read a CSV into a list of dictionaries."""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv_dicts(path: str, fieldnames, rows):
    """Write a list of dictionaries to a CSV with given field names."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_csv_row(path: str, fieldnames, row):
    """Append a single row to a CSV, writing the header if missing."""
    ensure_dir(os.path.dirname(path))
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def seed_items_if_missing():
    """Create a starter items.csv if none exists."""
    if os.path.exists(ITEMS_CSV):
        return
    # Define the starter item set.  Two new columns are included: "type"
    # identifies whether an item is RAW, REFINED or NULL (no crafting), and
    # "crafting_output" holds the SKU of the item produced when crafting.  A
    # NULL type indicates the item does not participate in crafting.
    starter = [
        # RAW materials
        {"sku":"A100","description":"Iron Ingot","image":"iron.png","price":"10","type":"RAW","crafting_output":"A180"},
        {"sku":"A170","description":"Glass Bottle","image":"bottle.png","price":"7","type":"RAW","crafting_output":"A130"},
        {"sku":"A120","description":"Wood Plank","image":"wood.png","price":"5","type":"NULL","crafting_output":""},
        # REFINED or intermediate items
        {"sku":"A130","description":"Health Potion","image":"potion.png","price":"15","type":"REFINED","crafting_output":""},
        {"sku":"A180","description":"Gear Wheel","image":"gear.png","price":"18","type":"REFINED","crafting_output":""},
        {"sku":"A190","description":"Cloth Bundle","image":"cloth.png","price":"9","type":"REFINED","crafting_output":""},
        {"sku":"A220","description":"Spice Pouch","image":"spice.png","price":"14","type":"REFINED","crafting_output":"A190"},
        # Other miscellaneous items which are non‑craftable
        {"sku":"A110","description":"Copper Wire","image":"copper.png","price":"8","type":"NULL","crafting_output":""},
        {"sku":"A140","description":"Leather Roll","image":"leather.png","price":"12","type":"NULL","crafting_output":""},
        {"sku":"A150","description":"Crystal Shard","image":"crystal.png","price":"22","type":"NULL","crafting_output":""},
        {"sku":"A160","description":"Coal Lump","image":"coal.png","price":"6","type":"NULL","crafting_output":""},
        {"sku":"A200","description":"Silver Nugget","image":"silver.png","price":"28","type":"NULL","crafting_output":""},
        {"sku":"A210","description":"Magic Ink","image":"ink.png","price":"25","type":"NULL","crafting_output":""},
        {"sku":"A230","description":"Stone Brick","image":"stone.png","price":"4","type":"NULL","crafting_output":""},
    ]
    # Write out with the new header that includes type and crafting_output
    write_csv_dicts(ITEMS_CSV, ["sku","description","image","price","type","crafting_output"], starter)


def load_items():
    """Load items from items.csv into a dict keyed by SKU."""
    seed_items_if_missing()
    rows = read_csv_dicts(ITEMS_CSV)
    items = {}
    for r in rows:
        try:
            base_price = float(r.get("price","0") or 0)
        except ValueError:
            base_price = 0.0
        # Normalise crafting fields; default to NULL/empty if missing
        craft_type = r.get("type", "NULL") or "NULL"
        craft_out = r.get("crafting_output", "") or ""
        items[r["sku"]] = {
            "sku": r["sku"],
            "description": r.get("description",""),
            "image": r.get("image",""),
            "base_price": base_price,
            "craft_type": craft_type.upper(),
            "craft_output": craft_out,
        }
    return items


def init_shop_from_items(items):
    """Initialise shop.csv with starting quantities and prices if missing."""
    if os.path.exists(SHOP_CSV):
        return
    rows = []
    for sku, it in items.items():
        qty = random.randint(5, 25)
        buy_price = max(1.0, it["base_price"] * random.uniform(0.85, 1.15))
        rows.append({
            "sku": sku,
            "qty_available": str(qty),
            "buy_price": f"{buy_price:.2f}",
        })
    write_csv_dicts(SHOP_CSV, ["sku","qty_available","buy_price"], rows)


def load_shop():
    """Load the shop from shop.csv."""
    rows = read_csv_dicts(SHOP_CSV)
    shop = {}
    for r in rows:
        sku = r["sku"]
        shop[sku] = {
            "sku": sku,
            "qty": int(float(r.get("qty_available","0") or 0)),
            "buy_price": float(r.get("buy_price","0") or 0),
        }
    return shop


def save_shop(shop):
    """Persist the shop state to shop.csv."""
    rows = []
    for sku, s in shop.items():
        rows.append({
            "sku": sku,
            "qty_available": str(int(s["qty"])),
            "buy_price": f"{float(s['buy_price']):.2f}",
        })
    write_csv_dicts(SHOP_CSV, ["sku","qty_available","buy_price"], rows)


def init_inventory_if_missing():
    """Create an empty inventory.csv if missing."""
    if os.path.exists(INV_CSV):
        return
    write_csv_dicts(INV_CSV, ["sku","qty_onhand","avg_cost"], [])


def load_inventory():
    """Load the player's inventory from inventory.csv."""
    init_inventory_if_missing()
    rows = read_csv_dicts(INV_CSV)
    inv = {}
    for r in rows:
        sku = r["sku"]
        inv[sku] = {
            "sku": sku,
            "qty": int(float(r.get("qty_onhand","0") or 0)),
            "avg_cost": float(r.get("avg_cost","0") or 0),
        }
    return inv


def save_inventory(inv):
    """Persist the player's inventory to inventory.csv."""
    rows = []
    for sku, i in inv.items():
        if i["qty"] <= 0:
            continue
        rows.append({
            "sku": sku,
            "qty_onhand": str(int(i["qty"])),
            "avg_cost": f"{float(i['avg_cost']):.2f}",
        })
    write_csv_dicts(INV_CSV, ["sku","qty_onhand","avg_cost"], rows)

# ---------------------------------------------------------------------------
# Cosmetics helpers
#
# Cosmetics include unlockable themes, screensavers and UI skins.  They are
# stored in cosmetics.csv and loaded at runtime.  Each record has fields:
# name, type (theme/screensaver/ui), unlocked ("true"/"false"), and price
# (string).  Unlocked cosmetics will be shown as selectable in the Store.

def seed_cosmetics_if_missing():
    """
    Initialise cosmetics.csv with a default set of themes, screensavers and
    UI skins.  If the file already exists it is left unchanged.  The
    default set includes one free theme and UI skin and several purchasable
    options.  You can add more entries here to expand the catalogue.
    """
    if os.path.exists(COSMETICS_CSV):
        return
    # Define the initial cosmetics catalogue.  UI skins have been removed
    # because the rounded corner feature was unreliable.  New themes
    # (Aquatic Blue, Flame Vixen, Coder Black, Hotdog Stand and Teal Breeze)
    # have been added to provide additional variety.  All themes except
    # the default are locked by default and can be purchased in the store.
    cosmetics = [
        # Themes
        {"name": "Default", "type": "theme", "unlocked": "true", "price": "0"},
        {"name": "Monochrome Green", "type": "theme", "unlocked": "false", "price": "20"},
        {"name": "Aquatic Blue", "type": "theme", "unlocked": "false", "price": "25"},
        {"name": "Flame Vixen", "type": "theme", "unlocked": "false", "price": "25"},
        {"name": "Coder Black", "type": "theme", "unlocked": "false", "price": "20"},
        {"name": "Hotdog Stand", "type": "theme", "unlocked": "false", "price": "20"},
        {"name": "Teal Breeze", "type": "theme", "unlocked": "false", "price": "20"},
        # Screensavers
        {"name": "None", "type": "screensaver", "unlocked": "true", "price": "0"},
        {"name": "Bouncing Item", "type": "screensaver", "unlocked": "false", "price": "10"},
    ]
    write_csv_dicts(COSMETICS_CSV, ["name","type","unlocked","price"], cosmetics)


def load_cosmetics():
    """Load the cosmetics catalogue into a list of dictionaries."""
    seed_cosmetics_if_missing()
    rows = read_csv_dicts(COSMETICS_CSV)
    # Normalize unlocked to a boolean string (lowercase)
    out = []
    for r in rows:
        ctype = r.get("type", "").lower()
        # Filter out UI skins entirely.  The rounded UI skin feature has
        # been removed so we do not expose any existing UI cosmetic
        # entries from earlier save files.
        if ctype == "ui":
            continue
        rec = {
            "name": r.get("name", ""),
            "type": ctype,
            "unlocked": str(r.get("unlocked", "false")).lower() == "true",
        }
        # price may be missing or malformed
        try:
            rec["price"] = float(r.get("price", "0") or 0.0)
        except Exception:
            rec["price"] = 0.0
        out.append(rec)
    return out


def save_cosmetics(rows):
    """
    Persist the cosmetics catalogue back to cosmetics.csv.  Expects a list of
    dictionaries matching the structure returned by load_cosmetics().
    """
    # Convert boolean unlocked to lower-case string for CSV storage
    to_write = []
    for r in rows:
        to_write.append({
            "name": r.get("name", ""),
            "type": r.get("type", ""),
            "unlocked": "true" if r.get("unlocked", False) else "false",
            "price": f"{r.get('price', 0.0):.2f}",
        })
    write_csv_dicts(COSMETICS_CSV, ["name","type","unlocked","price"], to_write)


def init_player_if_missing(starting_cash=DEFAULT_STARTING_CASH):
    """Create a default player.csv if missing."""
    if os.path.exists(PLAYER_CSV):
        return
    # Initialise player.csv with additional fields for theme, screensaver and UI skin.
    write_csv_dicts(
        PLAYER_CSV,
        ["cash","capacity","day","cap_change_week","theme","screensaver","ui_skin"],
        [{
            "cash": f"{starting_cash:.2f}",
            "capacity": str(DEFAULT_CAPACITY),
            "day": "1",
            "cap_change_week": "0",
            # Default selections correspond to the built‑in free cosmetics
            "theme": style.CURRENT_THEME,
            "screensaver": "None",
            "ui_skin": style.CURRENT_UI_SKIN,
        }]
    )


def load_player():
    """Load player state from player.csv."""
    rows = read_csv_dicts(PLAYER_CSV)
    if not rows:
        init_player_if_missing(DEFAULT_STARTING_CASH)
        rows = read_csv_dicts(PLAYER_CSV)
    r = rows[0]
    return {
        "cash": float(r.get("cash","0") or 0),
        "capacity": int(float(r.get("capacity","0") or 0)),
        "day": int(float(r.get("day","1") or 1)),
        "cap_change_week": int(float(r.get("cap_change_week","0") or 0)),
        # Persisted cosmetic selections; fall back to current defaults if missing
        "theme": r.get("theme", style.CURRENT_THEME) or style.CURRENT_THEME,
        "screensaver": r.get("screensaver", "None") or "None",
        "ui_skin": r.get("ui_skin", style.CURRENT_UI_SKIN) or style.CURRENT_UI_SKIN,
    }


def save_player(player):
    """Persist player state to player.csv."""
    # Include cosmetic selections in the persisted player state
    write_csv_dicts(
        PLAYER_CSV,
        ["cash","capacity","day","cap_change_week","theme","screensaver","ui_skin"],
        [{
            "cash": f"{player['cash']:.2f}",
            "capacity": str(player["capacity"]),
            "day": str(player["day"]),
            "cap_change_week": str(int(player.get("cap_change_week", 0))),
            "theme": player.get("theme", style.CURRENT_THEME),
            "screensaver": player.get("screensaver", "None"),
            "ui_skin": player.get("ui_skin", style.CURRENT_UI_SKIN),
        }]
    )


TXN_FIELDS = ["timestamp","day","sku","action","qty","unit_price","total","cash_after"]

# Weekly report fields (append-only row per week, generated each Sunday)
WEEKLY_FIELDS = [
    "timestamp",
    "week",
    "rent_cost",
    "bought_total",
    "bought_qty",
    "bought_lines",
    "sold_total",
    "sold_qty",
    "sold_lines",
    "weekly_profit",
    "cash_total",
    "net_worth",
    "storage_used",
    "storage_capacity",
    "storage_utilization",
    "note",
]


def log_txn(day, sku, action, qty, unit_price, total, cash_after):
    """Log a transaction (buy, sell or bill) to transactions.csv."""
    append_csv_row(TXN_CSV, TXN_FIELDS, {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "day": str(day),
        "sku": sku,
        "action": action,
        "qty": str(int(qty)),
        "unit_price": f"{unit_price:.2f}",
        "total": f"{total:.2f}",
        "cash_after": f"{cash_after:.2f}",
    })


# -------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------

def inv_used_units(inv):
    """Total number of units currently held by the player."""
    return sum(i["qty"] for i in inv.values())


def week_number(day: int) -> int:
    """Return 1-based week number for a given 1-based day counter."""
    return ((day - 1) // BILL_INTERVAL) + 1


def week_day_range(week: int):
    """Return (start_day, end_day) inclusive for a given 1-based week."""
    start_day = (week - 1) * BILL_INTERVAL + 1
    end_day = start_day + (BILL_INTERVAL - 1)
    return start_day, end_day


def is_sunday(day: int) -> bool:
    """Game day 1 is Monday, so Sunday is every 7th day (7, 14, 21, ...)."""
    return day % BILL_INTERVAL == 0


def load_latest_weekly_report():
    """Load the most recent weekly report row (or None if none exists)."""
    rows = read_csv_dicts(WEEKLY_REPORT_CSV)
    if not rows:
        return None
    return rows[-1]


def load_weekly_reports_typed():
    """Load weekly reports with basic type normalization and sorted by week."""
    rows = read_csv_dicts(WEEKLY_REPORT_CSV)
    typed = []
    for r in rows:
        rr = dict(r)
        try:
            rr["week"] = int(float(rr.get("week", 0) or 0))
        except Exception:
            rr["week"] = 0
        # floats
        for k in [
            "rent_cost",
            "bought_total",
            "sold_total",
            "weekly_profit",
            "cash_total",
            "net_worth",
            "storage_utilization",
        ]:
            try:
                rr[k] = float(rr.get(k, 0) or 0)
            except Exception:
                rr[k] = 0.0
        # ints
        for k in [
            "bought_qty",
            "bought_lines",
            "sold_qty",
            "sold_lines",
            "storage_used",
            "storage_capacity",
        ]:
            try:
                rr[k] = int(float(rr.get(k, 0) or 0))
            except Exception:
                rr[k] = 0
        rr["note"] = str(rr.get("note", "") or "")
        typed.append(rr)
    typed.sort(key=lambda x: x.get("week", 0))
    return typed


def get_report_by_week(rows, week: int):
    for r in rows:
        if int(r.get("week", 0) or 0) == int(week):
            return r
    return None


def compute_dynamic_notes(report_row: dict):
    """Return comma-separated recommendations based on a weekly report row."""
    if not report_row:
        return ""

    notes = []

    profit = float(report_row.get("weekly_profit", 0) or 0)
    sold_total = float(report_row.get("sold_total", 0) or 0)
    bought_total = float(report_row.get("bought_total", 0) or 0)
    sold_lines = int(report_row.get("sold_lines", 0) or 0)
    bought_lines = int(report_row.get("bought_lines", 0) or 0)
    rent_cost = float(report_row.get("rent_cost", 0) or 0)
    util = float(report_row.get("storage_utilization", 0) or 0)
    cap = int(report_row.get("storage_capacity", 0) or 0)

    # Profit / revenue guidance
    if profit < 0:
        notes.append("Profit negative—sell more or reduce rent")
    elif profit > 0 and sold_lines > 0:
        notes.append("Good profit—consider scaling what sold")

    # Activity guidance
    if sold_lines == 0 and bought_lines > 0:
        notes.append("No sales—try selling before buying more")
    if bought_total > sold_total and sold_lines > 0:
        notes.append("Spend > revenue—slow purchases or increase sales")

    # Rent & storage guidance
    if cap > 0 and rent_cost > 0 and sold_total <= rent_cost:
        notes.append("Rent is heavy—aim for weekly sales above rent")
    if util >= 0.90:
        notes.append("Storage nearly full—consider increasing capacity Sunday")
    if util <= 0.20 and cap > DEFAULT_CAPACITY:
        notes.append("Low storage usage—consider decreasing capacity to cut rent")

    if not notes:
        notes.append("Keep an eye on profit vs rent—storage is your weekly overhead")

    # De-dup while keeping order
    seen = set()
    out = []
    for n in notes:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return ", ".join(out)


def weekly_report_exists(week: int) -> bool:
    rows = read_csv_dicts(WEEKLY_REPORT_CSV)
    for r in rows:
        try:
            if int(float(r.get("week", 0) or 0)) == week:
                return True
        except ValueError:
            continue
    return False


def generate_weekly_report_row(player, inv, shop, week: int):
    """Compute and append a weekly report row for the given week."""
    if weekly_report_exists(week):
        return

    start_day, end_day = week_day_range(week)
    txns = read_csv_dicts(TXN_CSV)
    week_txns = []
    for t in txns:
        try:
            d = int(float(t.get("day", 0) or 0))
        except ValueError:
            continue
        if start_day <= d <= end_day:
            week_txns.append(t)

    bought = [t for t in week_txns if t.get("action") == "BUY"]
    sold = [t for t in week_txns if t.get("action") == "SELL"]
    rent = [t for t in week_txns if t.get("action") == "RENT"]

    def f(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    def i(x):
        try:
            return int(float(x))
        except Exception:
            return 0

    bought_total = sum(f(t.get("total")) for t in bought)
    sold_total = sum(f(t.get("total")) for t in sold)
    rent_cost = sum(f(t.get("total")) for t in rent)

    bought_qty = sum(i(t.get("qty")) for t in bought)
    sold_qty = sum(i(t.get("qty")) for t in sold)

    bought_lines = len(bought)
    sold_lines = len(sold)

    weekly_profit = sold_total - bought_total - rent_cost

    storage_used = inv_used_units(inv)
    storage_capacity = max(1, int(player.get("capacity", 1)))
    storage_util = storage_used / storage_capacity

    # Use the same net-worth approximation as the HUD (cash + inventory @ sell price)
    net_worth = float(player.get("cash", 0.0)) + sum(
        (shop[sku]["buy_price"] * SPREAD) * inv[sku]["qty"]
        for sku in inv.keys()
        if sku in shop
    )

    # Simple note generator (keeps it punchy)
    note = ""
    if weekly_profit < 0:
        note = "Consider expanding storage, aim to sell more than purchase cost"
    elif storage_util >= 0.9:
        note = "Storage is nearly full. Consider selling slow movers or expanding."
    elif sold_total <= 0 and bought_total > 0:
        note = "No sales this week. Consider lowering risk and buying less next week."

    append_csv_row(WEEKLY_REPORT_CSV, WEEKLY_FIELDS, {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "week": str(week),
        "rent_cost": f"{rent_cost:.2f}",
        "bought_total": f"{bought_total:.2f}",
        "bought_qty": str(bought_qty),
        "bought_lines": str(bought_lines),
        "sold_total": f"{sold_total:.2f}",
        "sold_qty": str(sold_qty),
        "sold_lines": str(sold_lines),
        "weekly_profit": f"{weekly_profit:.2f}",
        "cash_total": f"{float(player.get('cash', 0.0)):.2f}",
        "net_worth": f"{net_worth:.2f}",
        "storage_used": str(storage_used),
        "storage_capacity": str(storage_capacity),
        "storage_utilization": f"{storage_util:.4f}",
        "note": note,
    })


def capacity_upgrade_cost(player):
    """Cost in cash for the next capacity upgrade."""
    base = 40
    growth = (player["capacity"] / DEFAULT_CAPACITY) ** 1.2
    return int(base * growth)


def next_day(items, shop, player):
    """
    Advance the game by one day.  Prices move, new stock arrives and periodic
    bills are charged every BILL_INTERVAL days.  Returns a message if a bill
    payment occurred.
    """
    # Update prices toward base and random shock
    for sku, s in shop.items():
        base = items[sku]["base_price"]
        current = s["buy_price"]
        toward_base = (base - current) * 0.15
        shock = current * random.uniform(-VOLATILITY, VOLATILITY)
        new_price = max(1.0, current + toward_base + shock)
        s["buy_price"] = new_price
        s["qty"] += random.randint(RESTOCK_MIN, RESTOCK_MAX)

    # Advance day
    player["day"] += 1

    # Every Sunday (each 7th day), deduct rent. Rent equals current storage capacity.
    if player["day"] % BILL_INTERVAL == 0:
        cost = float(player.get("capacity", 0) or 0)
        player["cash"] -= cost
        # Log as a rent transaction; use SKU "" to denote non-item
        log_txn(player["day"], "", "RENT", 1, cost, cost, player["cash"])
        return f"Paid rent: ${cost:.0f}"
    return ""


def load_image_or_placeholder(path: str, size=(24,24), colour=(180,180,180)):
    """
    Load an image from the given path relative to RES_DIR.  If it doesn't
    exist return a coloured surface of the specified size.
    """
    full_path = os.path.join(RES_DIR, path) if path else ""
    # Attempt to load the given image; if it fails, try a default "image.jpg" fallback
    if full_path:
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path).convert_alpha()
                return pygame.transform.smoothscale(img, size)
            except Exception:
                pass
        # try fallback file
        fallback = os.path.join(RES_DIR, "image.jpg")
        if os.path.exists(fallback):
            try:
                img = pygame.image.load(fallback).convert_alpha()
                return pygame.transform.smoothscale(img, size)
            except Exception:
                pass
    # create coloured placeholder if no image found
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(colour + (255,))
    # draw border for placeholder for visual appeal
    border_col = (max(0, colour[0]-40), max(0, colour[1]-40), max(0, colour[2]-40), 255)
    pygame.draw.rect(surf, border_col, surf.get_rect(), 2)
    return surf


# -------------------------------------------------------------
# UI components
# -------------------------------------------------------------

class InputBox:
    """
    A numeric input field styled in a retro manner.  When active it accepts
    digit keys and backspace.  The input is limited to non-negative integers.
    """
    def __init__(self, rect, text="", numeric=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.active = False
        self.numeric = numeric

    def handle_event(self, event):
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            changed = True
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                changed = True
            elif event.key == pygame.K_RETURN:
                self.active = False
                changed = True
            else:
                ch = event.unicode
                if self.numeric:
                    if ch.isdigit():
                        self.text += ch
                        changed = True
                else:
                    if ch.isprintable():
                        self.text += ch
                        changed = True
        return changed

    def value_int(self):
        try:
            return int(self.text) if self.text.strip() else 0
        except ValueError:
            return 0

    def draw(self, surf, font):
        """Draw the input box.  Highlight when active and draw a caret."""
        # choose background colour based on active state
        bg_col = COLOR_CONTROL_BACKGROUND if not self.active else COLOR_ROW_DARK
        pygame.draw.rect(surf, bg_col, self.rect)
        # 3D border: invert shading when active to emphasise selection
        x, y, w, h = self.rect
        if self.active:
            # when active, darken top/left and lighten bottom/right
            tl_col = COLOR_CONTROL_BORDER_DARK
            br_col = COLOR_CONTROL_BORDER_LIGHT
        else:
            tl_col = COLOR_CONTROL_BORDER_LIGHT
            br_col = COLOR_CONTROL_BORDER_DARK
        # top and left edges
        pygame.draw.line(surf, tl_col, (x, y), (x + w - 1, y))
        pygame.draw.line(surf, tl_col, (x, y), (x, y + h - 1))
        # bottom and right edges
        pygame.draw.line(surf, br_col, (x, y + h - 1), (x + w - 1, y + h - 1))
        pygame.draw.line(surf, br_col, (x + w - 1, y), (x + w - 1, y + h - 1))
        # render text
        txt = font.render(self.text, True, COLOR_CONTROL_TEXT)
        text_x = self.rect.x + 4
        text_y = self.rect.y + (self.rect.height - txt.get_height()) // 2
        surf.blit(txt, (text_x, text_y))
        # draw caret if active
        if self.active:
            # blink the caret every 500 ms
            blink = (pygame.time.get_ticks() // 500) % 2 == 0
            if blink:
                caret_x = text_x + txt.get_width() + 1
                caret_top = self.rect.y + 4
                caret_bottom = self.rect.y + self.rect.height - 4
                pygame.draw.line(surf, COLOR_CONTROL_TEXT, (caret_x, caret_top), (caret_x, caret_bottom))


class RetroButton:
    """
    A button styled after Windows 95 controls.  It uses top/left highlights and
    bottom/right shadows to appear raised.  When pressed the shading is
    inverted.  The button handles mouse events to trigger a callback when
    clicked.
    """
    def __init__(self, rect, label, callback):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.pressed = False
        self.hover = False
        self.visible = True

    def handle_event(self, event):
        if not self.visible:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.callback()
            self.pressed = False

    def update(self):
        # update hover state
        if not self.visible:
            self.hover = False
            return
        mouse_pos = pygame.mouse.get_pos()
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, surf, font):
        if not self.visible:
            return
        # fill background with current skin border radius
        # Use UI_BORDER_RADIUS from style to round corners when the user selects
        # a different UI skin.  Default is 0 for square corners.
        pygame.draw.rect(surf, COLOR_CONTROL_BACKGROUND, self.rect, border_radius=UI_BORDER_RADIUS)
        # Determine shading: when pressed invert light/dark
        if self.pressed:
            tl_col = COLOR_CONTROL_BORDER_DARK
            br_col = COLOR_CONTROL_BORDER_LIGHT
        else:
            tl_col = COLOR_CONTROL_BORDER_LIGHT
            br_col = COLOR_CONTROL_BORDER_DARK
        x, y, w, h = self.rect
        # top and left edges
        pygame.draw.line(surf, tl_col, (x, y), (x + w - 1, y))
        pygame.draw.line(surf, tl_col, (x, y), (x, y + h - 1))
        # bottom and right edges
        pygame.draw.line(surf, br_col, (x, y + h - 1), (x + w - 1, y + h - 1))
        pygame.draw.line(surf, br_col, (x + w - 1, y), (x + w - 1, y + h - 1))
        # text
        txt = font.render(self.label, True, COLOR_CONTROL_TEXT)
        surf.blit(txt, (self.rect.centerx - txt.get_width()//2,
                        self.rect.centery - txt.get_height()//2))


# -------------------------------------------------------------
# Main application
# -------------------------------------------------------------

def main():
    # Prepare directories
    ensure_dir(DATA_DIR)
    ensure_dir(RES_DIR)
    pygame.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Inventory Stock Manager")
    clock = pygame.time.Clock()

    # Fonts: default sans-serif approximates MS Sans Serif
    font_small = pygame.font.Font(None, 16)
    font_medium = pygame.font.Font(None, 20)
    font_large = pygame.font.Font(None, 28)
    font_title = pygame.font.Font(None, 24)

    # Load base data
    items = load_items()
    init_shop_from_items(items)
    init_inventory_if_missing()

    # Screensaver manager and idle tracking.  Create this early so it exists
    # throughout the game.  We pass our image loader so the screensaver can
    # load icons using the same placeholder logic as the rest of the UI.
    ss_manager = screensaver.ScreensaverManager(load_image_or_placeholder)
    idle_timer = 0.0

    # Start screen state
    start_input = InputBox((0, 0, 100, 24), text=str(DEFAULT_STARTING_CASH), numeric=True)
    start_button = None  # placeholder
    start_message = ""
    start_window_rect = pygame.Rect(0, 0, 400, 180)
    start_window_rect.center = (WIDTH//2, HEIGHT//2)

    # Game state variables (assigned on start)
    player = None
    shop = None
    inv = None
    # We previously used cash_history for the graph.  Chat replaces the graph, but
    # we still record cash over days for internal suggestions if needed.
    cash_history = []  # list of (day, cash)

    # Offsets for scrolling tables and chat
    shop_offset = 0
    inv_offset = 0
    chat_offset = 0

    # Average buy prices per SKU (computed over days).  Will be initialised after
    # the game starts.
    avg_buy_prices = {}

    # Widgets lists for tables
    shop_inputs = []
    shop_buttons = []
    inv_inputs = []
    inv_buttons = []

    # Chat messages buffer
    chat_messages = []  # list of strings

    # Buttons for scrolling and actions
    up_shop_btn = None
    down_shop_btn = None
    up_inv_btn = None
    down_inv_btn = None
    next_day_btn = None
    tab_market_btn = None
    tab_weekly_btn = None
    buy_space_btn = None
    inc_space_btn = None
    dec_space_btn = None
    # Weekly report navigation
    report_prev_btn = None
    report_next_btn = None
    selected_report_week = 1

    # News tab navigation
    tab_news_btn = None
    news_prev_btn = None
    news_next_btn = None
    selected_news_week = 1
    # Chat scroll buttons
    chat_up_btn = None
    chat_down_btn = None

    # Store tab and sub‑category widgets
    tab_store_btn = None
    # Which sub‑tab is active within the Store: "cosmetics", "crafting" or "inventory"
    store_sub_tab = "cosmetics"
    # Dynamic widget lists for the Store categories.  These will hold
    # RetroButtons and InputBoxes for cosmetics, crafting and inventory
    # upgrades respectively.  Their contents are managed by update_store_widgets().
    store_cos_buttons = []
    store_craft_inputs = []
    store_craft_buttons = []
    store_inv_add_buttons = []
    store_inv_remove_buttons = []
    store_inv_custom_add_input = None
    store_inv_custom_remove_input = None
    # In‑memory catalogue of cosmetics loaded from cosmetics.csv
    cosmetics_list = []

    # Store sub‑tab button placeholders (cosmetics, crafting, inventory)
    store_cos_tab_btn = None
    store_craft_tab_btn = None
    store_inv_tab_btn = None

    toast = ""
    toast_timer = 0

    mode = "start"         # start screen vs main app
    app_tab = "market"      # "market" or "weekly"

    def set_toast(msg, frames=240):
        """Display a transient message.  Also add it to the chat feed."""
        nonlocal toast, toast_timer
        # push the message into chat for persistence
        add_chat_message(msg)
        # store as toast but we will render in chat style (no red)
        toast = msg
        toast_timer = frames

    # Chat helper: append a message and auto-scroll to bottom
    def add_chat_message(msg: str) -> None:
        """Append a line to the chat buffer and adjust the offset to show the newest messages."""
        nonlocal chat_messages, chat_offset
        chat_messages.append(msg)
        # compute number of lines visible in the message area of the chat
        visible_lines = max(1, (CHAT_HEIGHT - 20 - GRAPH_HEIGHT - 20) // CHAT_LINE_HEIGHT)
        max_offset = max(0, len(chat_messages) - visible_lines)
        chat_offset = max_offset

    # Utility: update widgets for tables when offsets or contents change
    def update_table_widgets():
        """Assign appropriate callbacks and visibility to table row widgets based on offsets."""
        # Ensure we have enough widget objects
        # Create them if lists empty
        nonlocal shop_inputs, shop_buttons, inv_inputs, inv_buttons
        while len(shop_inputs) < VISIBLE_ROWS:
            shop_inputs.append(InputBox((0,0,60,20), text="", numeric=True))
            shop_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "Buy", lambda: None))
        while len(inv_inputs) < VISIBLE_ROWS:
            inv_inputs.append(InputBox((0,0,60,20), text="", numeric=True))
            inv_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "Sell", lambda: None))

        # Shop rows mapping
        shop_keys = sorted(shop.keys())
        for i in range(VISIBLE_ROWS):
            if shop_offset + i < len(shop_keys):
                sku = shop_keys[shop_offset + i]
                # update buy callback capturing correct sku and local index
                def make_buy_callback(sku=sku, idx=i):
                    def _cb():
                        qty_req = shop_inputs[idx].value_int()
                        if qty_req <= 0:
                            set_toast("Enter a buy quantity > 0")
                            return
                        if shop[sku]["qty"] < qty_req:
                            set_toast("Not enough stock in shop")
                            return
                        used = inv_used_units(inv)
                        free = player["capacity"] - used
                        if qty_req > free:
                            set_toast(f"Not enough storage (free {free})")
                            return
                        unit_price = shop[sku]["buy_price"]
                        total = unit_price * qty_req
                        if player["cash"] < total:
                            set_toast("Not enough cash")
                            return
                        # apply purchase
                        player["cash"] -= total
                        shop[sku]["qty"] -= qty_req
                        if sku not in inv:
                            inv[sku] = {"sku": sku, "qty": 0, "avg_cost": 0.0}
                        prev_qty = inv[sku]["qty"]
                        prev_cost = inv[sku]["avg_cost"]
                        new_qty = prev_qty + qty_req
                        new_avg = ((prev_qty * prev_cost) + (qty_req * unit_price)) / new_qty
                        inv[sku]["qty"] = new_qty
                        inv[sku]["avg_cost"] = new_avg
                        log_txn(player["day"], sku, "BUY", qty_req, unit_price, total, player["cash"])
                        save_player(player)
                        save_shop(shop)
                        save_inventory(inv)
                        shop_inputs[idx].text = ""
                        set_toast(f"Bought {qty_req} of {sku}")
                        update_table_widgets()
                    return _cb
                shop_buttons[i].label = "Buy"
                shop_buttons[i].callback = make_buy_callback()
                shop_buttons[i].visible = True
                shop_inputs[i].active = False
                shop_inputs[i].text = shop_inputs[i].text  # keep existing value
                # update rects based on layout later in draw
            else:
                # hide
                shop_buttons[i].visible = False
                shop_inputs[i].text = ""
                shop_inputs[i].active = False

        # Inventory rows mapping
        inv_keys = sorted(inv.keys())
        for i in range(VISIBLE_ROWS):
            if inv_offset + i < len(inv_keys):
                sku = inv_keys[inv_offset + i]
                def make_sell_callback(sku=sku, idx=i):
                    def _cb():
                        qty_req = inv_inputs[idx].value_int()
                        if qty_req <= 0:
                            set_toast("Enter a sell quantity > 0")
                            return
                        if inv[sku]["qty"] < qty_req:
                            set_toast("Not enough quantity to sell")
                            return
                        sell_price = shop[sku]["buy_price"] * SPREAD
                        total = sell_price * qty_req
                        inv[sku]["qty"] -= qty_req
                        player["cash"] += total
                        shop[sku]["qty"] += qty_req
                        if inv[sku]["qty"] <= 0:
                            del inv[sku]
                        log_txn(player["day"], sku, "SELL", qty_req, sell_price, total, player["cash"])
                        save_player(player)
                        save_shop(shop)
                        save_inventory(inv)
                        inv_inputs[idx].text = ""
                        set_toast(f"Sold {qty_req} of {sku}")
                        update_table_widgets()
                    return _cb
                inv_buttons[i].label = "Sell"
                inv_buttons[i].callback = make_sell_callback()
                inv_buttons[i].visible = True
                inv_inputs[i].active = False
                inv_inputs[i].text = inv_inputs[i].text
            else:
                inv_buttons[i].visible = False
                inv_inputs[i].text = ""
                inv_inputs[i].active = False

    # -----------------------------------------------------------------
    # Store widget assignment
    def update_store_widgets():
        """
        Update callbacks and visibility for the dynamic widgets used in the
        store.  This includes cosmetics purchase/select buttons, crafting
        quantity inputs and convert buttons, and inventory upgrade buttons.
        This function should be called whenever the cosmetics list, player
        inventory or capacity changes so that the UI reflects the latest
        data.
        """
        nonlocal store_cos_buttons, store_craft_inputs, store_craft_buttons
        nonlocal store_inv_add_buttons, store_inv_remove_buttons
        nonlocal store_inv_custom_add_input, store_inv_custom_remove_input
        # Make the screensaver manager available inside this helper so we can
        # update the active screensaver when the player selects a different one.
        nonlocal ss_manager
        # Cosmetics: one button per cosmetic entry
        # Ensure we have enough buttons
        while len(store_cos_buttons) < len(cosmetics_list):
            store_cos_buttons.append(RetroButton(pygame.Rect(0,0,80,20), "", lambda: None))
        for i, cos in enumerate(cosmetics_list):
            # Determine label based on unlocked state
            label = "Select" if cos["unlocked"] else f"Buy ${int(cos['price'])}"
            store_cos_buttons[i].label = label
            # Define callback capturing the current cosmetic
            def make_cos_cb(idx=i, cos=cos):
                def _cb():
                    # Unlocked items can be selected
                    if cosmetics_list[idx]["unlocked"]:
                        name = cosmetics_list[idx]["name"]
                        ctype = cosmetics_list[idx]["type"]
                        # apply and update player selection
                        if ctype == "theme":
                            player["theme"] = name
                            style.apply_theme(name)
                            refresh_style_from_module()
                        elif ctype == "ui":
                            player["ui_skin"] = name
                            style.apply_ui_skin(name)
                            refresh_style_from_module()
                        elif ctype == "screensaver":
                            # Update both the player record and the
                            # screensaver manager so the change takes
                            # effect immediately.
                            player["screensaver"] = name
                            ss_manager.set(name)
                        save_player(player)
                        set_toast(f"Selected {name}")
                    else:
                        # Attempt to purchase if locked
                        price = cosmetics_list[idx]["price"]
                        if player["cash"] < price:
                            set_toast("Not enough cash to buy " + cosmetics_list[idx]["name"])
                            return
                        player["cash"] -= price
                        cosmetics_list[idx]["unlocked"] = True
                        save_player(player)
                        save_cosmetics(cosmetics_list)
                        set_toast(f"Purchased {cosmetics_list[idx]['name']}")
                    # After purchase or selection, refresh widgets
                    update_store_widgets()
                return _cb
            store_cos_buttons[i].callback = make_cos_cb()
            store_cos_buttons[i].visible = True
        # Hide any extra buttons
        for i in range(len(cosmetics_list), len(store_cos_buttons)):
            store_cos_buttons[i].visible = False

        # Crafting: generate craftable rows based on current inventory and items
        craftables = []
        for sku, itm in inv.items():
            info = items.get(sku, {})
            craft_type = info.get("craft_type", "NULL")
            out_sku = info.get("craft_output", "")
            if craft_type in ("RAW", "REFINED") and out_sku:
                # Only craft if output exists in items
                if out_sku in items:
                    craftables.append((sku, out_sku))
        # Ensure enough inputs/buttons
        while len(store_craft_inputs) < len(craftables):
            store_craft_inputs.append(InputBox((0,0,60,20), text="", numeric=True))
            store_craft_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "Convert", lambda: None))
        # Assign callbacks
        for i, (in_sku, out_sku) in enumerate(craftables):
            def make_craft_cb(idx=i, in_sku=in_sku, out_sku=out_sku):
                def _cb():
                    qty = store_craft_inputs[idx].value_int()
                    if qty <= 0:
                        set_toast("Enter qty > 0")
                        return
                    if inv[in_sku]["qty"] < qty:
                        set_toast("Not enough to convert")
                        return
                    # cost is 5% of current shop price of output per item
                    unit_cost = shop[out_sku]["buy_price"] * 0.05
                    total_cost = unit_cost * qty
                    if player["cash"] < total_cost:
                        set_toast("Not enough cash to craft")
                        return
                    # apply transaction
                    inv[in_sku]["qty"] -= qty
                    if inv[in_sku]["qty"] <= 0:
                        del inv[in_sku]
                    # add output
                    if out_sku not in inv:
                        inv[out_sku] = {"sku": out_sku, "qty": 0, "avg_cost": 0.0}
                    inv[out_sku]["qty"] += qty
                    # Deduct cash
                    player["cash"] -= total_cost
                    # Log the crafting transaction
                    log_txn(player["day"], f"{in_sku}->{out_sku}", "CRAFT", qty, unit_cost, total_cost, player["cash"])
                    save_player(player)
                    save_inventory(inv)
                    # After crafting, update widgets
                    set_toast(f"Crafted {qty} of {out_sku}")
                    update_store_widgets()
                return _cb
            store_craft_buttons[i].label = "Convert"
            store_craft_buttons[i].callback = make_craft_cb()
            store_craft_buttons[i].visible = True
            store_craft_inputs[i].active = False
        # Hide any extra craft widgets
        for i in range(len(craftables), len(store_craft_buttons)):
            store_craft_buttons[i].visible = False
            store_craft_inputs[i].text = ""

        # Inventory upgrades: quick buttons for add and remove and custom inputs
        # The available multipliers depend on current capacity
        increments = [1, 5, 10, 100]
        # Ensure enough buttons: one per increment plus one for custom
        total_buttons = len(increments) + 1
        # Expand button lists if needed
        while len(store_inv_add_buttons) < total_buttons:
            store_inv_add_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "+", lambda: None))
        while len(store_inv_remove_buttons) < total_buttons:
            store_inv_remove_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "-", lambda: None))

        # Define helper to make capacity change callbacks
        def make_add_cb(amount):
            def _cb():
                nonlocal player
                cost = amount
                # For Add, cost = amount; check affordability
                if player["cash"] < cost:
                    set_toast("Not enough cash to increase capacity")
                    return
                player["capacity"] += amount
                player["cash"] -= cost
                save_player(player)
                set_toast(f"Increased capacity by {amount}")
                update_store_widgets()
            return _cb
        def make_remove_cb(amount):
            def _cb():
                nonlocal player
                used = inv_used_units(inv)
                cost = amount
                if player["capacity"] - amount < used:
                    set_toast("Cannot reduce below items held")
                    return
                if player["cash"] < cost:
                    set_toast("Not enough cash to decrease capacity")
                    return
                player["capacity"] -= amount
                player["cash"] -= cost
                save_player(player)
                set_toast(f"Decreased capacity by {amount}")
                update_store_widgets()
            return _cb

        # Assign labels and callbacks for each quick increment button
        # Visibility depends on current storage capacity.  The spec requires
        # always showing the x1 buttons but enabling the x5, x10 and
        # x100 buttons only when the player's capacity is at least that
        # amount.  To satisfy this requirement we mark the buttons
        # visible when the threshold is met and hide them otherwise.
        for i, inc in enumerate(increments):
            add_btn = store_inv_add_buttons[i]
            add_btn.label = f"+{inc}"
            add_btn.callback = make_add_cb(inc)
            rem_btn = store_inv_remove_buttons[i]
            rem_btn.label = f"-{inc}"
            rem_btn.callback = make_remove_cb(inc)
            # Always show x1 buttons; hide others if capacity below threshold
            if inc == 1 or player["capacity"] >= inc:
                add_btn.visible = True
                rem_btn.visible = True
            else:
                add_btn.visible = False
                rem_btn.visible = False
        # Custom buttons (last index)
        custom_idx = len(increments)
        # Add custom button uses value from store_inv_custom_add_input
        def add_custom():
            try:
                amt = store_inv_custom_add_input.value_int()
            except Exception:
                amt = 0
            if amt <= 0:
                set_toast("Enter a positive number")
                return
            make_add_cb(amt)()
        def remove_custom():
            try:
                amt = store_inv_custom_remove_input.value_int()
            except Exception:
                amt = 0
            if amt <= 0:
                set_toast("Enter a positive number")
                return
            make_remove_cb(amt)()
        # Create or update custom buttons
        # Create or update custom buttons.  These are always visible
        if custom_idx >= len(store_inv_add_buttons):
            store_inv_add_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "Add", add_custom))
        else:
            store_inv_add_buttons[custom_idx].label = "Add"
            store_inv_add_buttons[custom_idx].callback = add_custom
        store_inv_add_buttons[custom_idx].visible = True
        if custom_idx >= len(store_inv_remove_buttons):
            store_inv_remove_buttons.append(RetroButton(pygame.Rect(0,0,60,20), "Remove", remove_custom))
        else:
            store_inv_remove_buttons[custom_idx].label = "Remove"
            store_inv_remove_buttons[custom_idx].callback = remove_custom
        store_inv_remove_buttons[custom_idx].visible = True

    # Functions for scroll buttons
    def scroll_shop_up():
        nonlocal shop_offset
        if shop_offset > 0:
            shop_offset -= 1
            update_table_widgets()
    def scroll_shop_down():
        nonlocal shop_offset
        shop_count = len(sorted(shop.keys()))
        max_offset = max(0, shop_count - VISIBLE_ROWS)
        if shop_offset < max_offset:
            shop_offset += 1
            update_table_widgets()
    def scroll_inv_up():
        nonlocal inv_offset
        if inv_offset > 0:
            inv_offset -= 1
            update_table_widgets()
    def scroll_inv_down():
        nonlocal inv_offset
        inv_count = len(sorted(inv.keys()))
        max_offset = max(0, inv_count - VISIBLE_ROWS)
        if inv_offset < max_offset:
            inv_offset += 1
            update_table_widgets()

    # Chat scroll functions
    def scroll_chat_up():
        nonlocal chat_offset
        if chat_offset > 0:
            chat_offset -= 1
    def scroll_chat_down():
        nonlocal chat_offset
        # number of lines visible in chat area
        visible_lines = max(1, (CHAT_HEIGHT - 20 - GRAPH_HEIGHT - 20) // CHAT_LINE_HEIGHT)
        max_offset = max(0, len(chat_messages) - visible_lines)
        if chat_offset < max_offset:
            chat_offset += 1

    # Storage capacity adjustment: only on Sundays (can adjust multiple times).
    def _can_change_capacity():
        if not is_sunday(player["day"]):
            set_toast("Inventory can only be changed on Sunday")
            return False
        return True

    def increase_space():
        if not _can_change_capacity():
            return
        player["capacity"] += CAPACITY_STEP
        save_player(player)
        set_toast(f"Storage set to {player['capacity']} (rent will be ${player['capacity']} each Sunday)")

    def decrease_space():
        if not _can_change_capacity():
            return
        used = inv_used_units(inv)
        if player["capacity"] - CAPACITY_STEP < used:
            set_toast(f"Can't drop storage below items held ({used})")
            return
        player["capacity"] = max(1, player["capacity"] - CAPACITY_STEP)
        save_player(player)
        set_toast(f"Storage set to {player['capacity']} (rent will be ${player['capacity']} each Sunday)")

    # Backward compatible alias (old button name)
    def purchase_space():
        increase_space()

    def advance_day():
        """Advance the day, update prices and averages, pay bills, generate tips and handle news."""
        nonlocal app_tab, selected_report_week, selected_news_week
        # Progress the game day and handle bills and news via the market module
        messages, rent_due, new_events = market.next_day(items, shop, player, NEWS_CSV, PREVIOUS_NEWS_CSV)

        bill_msg = ""
        # Handle rent transaction separately (log and message)
        if rent_due > 0:
            # Log the rent as a transaction; SKU "" denotes non-item
            log_txn(player["day"], "", "RENT", 1, rent_due, rent_due, player["cash"])
        # Join any returned messages into a single toast message
        if messages:
            bill_msg = "\n".join(messages)

        # If we are now on a Sunday, generate a weekly report row (once) and
        # auto-switch to the Weekly Report tab.
        if is_sunday(player["day"]):
            generate_weekly_report_row(player, inv, shop, week_number(player["day"]))
            app_tab = "weekly"
            selected_report_week = week_number(player["day"])
        # If we are now on a Friday, auto-switch to the News tab so the player sees impacts immediately.
        dow = (player["day"] - 1) % BILL_INTERVAL  # Monday=0 ... Sunday=6
        if dow == 4:  # Friday
            app_tab = "news"
            selected_news_week = week_number(player["day"])

        # Refresh the list of news weeks and clamp the selected week to the available range
        news_weeks = market.get_news_weeks(PREVIOUS_NEWS_CSV)
        if news_weeks:
            # If new events were generated, default to the latest news week
            if new_events:
                selected_news_week = news_weeks[-1]
            # Clamp existing selection
            if selected_news_week < news_weeks[0]:
                selected_news_week = news_weeks[0]
            if selected_news_week > news_weeks[-1]:
                selected_news_week = news_weeks[-1]
        else:
            selected_news_week = week_number(player["day"])

        # update cash history
        cash_history.append((player["day"], player["cash"]))
        # Update running average buy prices per SKU (including today's price)
        current_day = player["day"]
        for sku in shop:
            current_price = shop[sku]["buy_price"]
            prev_avg = avg_buy_prices.get(sku, current_price)
            # Weighted average: previous average times (day-1) plus current price
            new_avg = ((prev_avg * (current_day - 1)) + current_price) / current_day
            avg_buy_prices[sku] = new_avg
        # Prepare separate lists for tips and facts
        tips = []
        facts = []
        # Build buy and sell tips
        buy_candidates = []
        for sku in shop:
            cur_price = shop[sku]["buy_price"]
            avg_price = avg_buy_prices.get(sku, cur_price)
            if cur_price < avg_price * 0.95:  # at least 5% below average
                buy_candidates.append((sku, cur_price, avg_price))
        if buy_candidates:
            # Use a safe ratio to avoid division by zero in case avg_price is zero
            best_buy = min(buy_candidates, key=lambda x: (x[1] / x[2]) if x[2] > 0 else float('inf'))
            sku, cur_price, avg_price = best_buy
            tips.append(f"Tip: BUY {sku} – now ${cur_price:.2f} < avg ${avg_price:.2f}")
        # Sell tips
        sell_candidates = []
        for sku in inv:
            sell_price = shop[sku]["buy_price"] * SPREAD
            avg_cost = inv[sku]["avg_cost"]
            if sell_price > avg_cost * 1.05:
                sell_candidates.append((sku, sell_price, avg_cost))
        if sell_candidates:
            # Avoid division by zero when computing profitability.  Items
            # produced via crafting may have an average cost of zero which
            # would otherwise cause a ZeroDivisionError.  Treat zero cost
            # items as having infinite return so they bubble to the top of
            # the recommendation list.
            def _sell_ratio(candidate):
                sp, cost = candidate[1], candidate[2]
                return sp / cost if cost > 0 else float('inf')
            best_sell = max(sell_candidates, key=_sell_ratio)
            sku, sp, cost = best_sell
            tips.append(f"Tip: SELL {sku} – sell ${sp:.2f} > cost ${cost:.2f}")
        # Facts about rent due and cash (rent = current storage capacity)
        days_until = BILL_INTERVAL - (player['day'] % BILL_INTERVAL)
        next_rent = int(player.get('capacity', 0) or 0)
        facts.append(f"{days_until} day{'s' if days_until != 1 else ''} till rent (${next_rent}) is due.")
        # Always include cash fact
        facts.append(f"You have ${player['cash']:.2f} cash.")
        # Show bill message if any.  set_toast adds it to chat as well.
        if bill_msg:
            set_toast(bill_msg)
        # Determine whether to show a tip or a fact on this day
        show_tip = (player["day"] % 2 == 1)
        # Choose a message accordingly
        chosen_msg = None
        if show_tip and tips:
            # pick one tip at random
            chosen_msg = random.choice(tips)
        elif not show_tip and facts:
            chosen_msg = random.choice(facts)
        # If no message chosen yet, fall back to whichever exists
        if not chosen_msg:
            if tips:
                chosen_msg = random.choice(tips)
            elif facts:
                chosen_msg = random.choice(facts)
        # Add the chosen message if available
        if chosen_msg:
            add_chat_message(chosen_msg)
        save_shop(shop)
        save_player(player)
        update_table_widgets()

    running = True
    while running:
        # Compute elapsed time for this frame in seconds.  We use this
        # delta both for the screensaver movement and to update our
        # idle timer.  Using clock.tick here returns milliseconds.
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Any mouse or keyboard interaction resets the idle timer and
            # hides the screensaver.  We treat motion, button presses and
            # key presses as activity.
            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                              pygame.KEYDOWN, pygame.KEYUP):
                idle_timer = 0.0
                ss_manager.deactivate()
            if mode == "start":
                # Start screen events
                start_input.handle_event(event)
                if start_button:
                    start_button.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # clicking start button handled above
                    pass
            else:
                # Main app events (tabbed UI)
                tab_market_btn.handle_event(event)
                tab_weekly_btn.handle_event(event)
                tab_news_btn.handle_event(event)
                # Store tab
                if tab_store_btn:
                    tab_store_btn.handle_event(event)

                # Next day button is available on both tabs
                next_day_btn.handle_event(event)

                # Tab-specific interactions
                if app_tab == "market":
                    # Inputs
                    for ib in shop_inputs:
                        ib.handle_event(event)
                    for ib in inv_inputs:
                        ib.handle_event(event)
                    # Buttons
                    for btn in shop_buttons + inv_buttons:
                        btn.handle_event(event)
                    up_shop_btn.handle_event(event)
                    down_shop_btn.handle_event(event)
                    up_inv_btn.handle_event(event)
                    down_inv_btn.handle_event(event)
                elif app_tab == "weekly":
                    # Weekly report tab: storage change buttons live here
                    inc_space_btn.handle_event(event)
                    dec_space_btn.handle_event(event)
                    report_prev_btn.handle_event(event)
                    report_next_btn.handle_event(event)
                elif app_tab == "news":
                    # News tab: navigation arrows
                    news_prev_btn.handle_event(event)
                    news_next_btn.handle_event(event)
                elif app_tab == "store":
                    # Handle sub‑tab navigation within the store
                    store_cos_tab_btn.handle_event(event)
                    store_craft_tab_btn.handle_event(event)
                    store_inv_tab_btn.handle_event(event)
                    # Cosmetics interactions
                    if store_sub_tab == "cosmetics":
                        for btn in store_cos_buttons:
                            if btn.visible:
                                btn.handle_event(event)
                    # Crafting interactions
                    elif store_sub_tab == "crafting":
                        for ib in store_craft_inputs:
                            ib.handle_event(event)
                        for btn in store_craft_buttons:
                            if btn.visible:
                                btn.handle_event(event)
                    # Inventory upgrades interactions
                    elif store_sub_tab == "inventory":
                        # Custom inputs for add/remove
                        if store_inv_custom_add_input:
                            store_inv_custom_add_input.handle_event(event)
                        if store_inv_custom_remove_input:
                            store_inv_custom_remove_input.handle_event(event)
                        # Quick buttons
                        for btn in store_inv_add_buttons + store_inv_remove_buttons:
                            if btn.visible:
                                btn.handle_event(event)

                # chat scroll buttons (visible on both tabs)
                chat_up_btn.handle_event(event)
                chat_down_btn.handle_event(event)

                # Backward-compat (hidden)
                buy_space_btn.handle_event(event)

        # update hover states for buttons

        # Update idle timer and screensaver.  Only run the screensaver in the
        # main game (not on the start screen) and only when the player has
        # selected a screensaver other than "None".
        idle_timer += dt
        if mode != "start":
            try:
                sel_name = player.get("screensaver", "None") if player else "None"
            except Exception:
                sel_name = "None"
            # Activate the screensaver if we've been idle long enough and it's not already active.
            if idle_timer >= screensaver.DEFAULT_IDLE_SECONDS and not ss_manager.is_active() and sel_name.lower() != "none":
                ss_manager.set(sel_name)
                ss_manager.activate(items)
            # Always update the screensaver so that the bouncing object moves if active.
            ss_manager.update(dt, screen.get_rect())
        if mode != "start":
            tab_market_btn.update()
            tab_weekly_btn.update()
            tab_news_btn.update()
            # Store tab exists only after game starts
            if tab_store_btn:
                tab_store_btn.update()
            next_day_btn.update()
            chat_up_btn.update()
            chat_down_btn.update()

            if app_tab == "market":
                for btn in shop_buttons + inv_buttons:
                    btn.update()
                up_shop_btn.update()
                down_shop_btn.update()
                up_inv_btn.update()
                down_inv_btn.update()
            elif app_tab == "weekly":
                inc_space_btn.update()
                dec_space_btn.update()
                report_prev_btn.update()
                report_next_btn.update()
            elif app_tab == "news":
                news_prev_btn.update()
                news_next_btn.update()
            elif app_tab == "store":
                # Update store sub‑tab navigation buttons
                store_cos_tab_btn.update()
                store_craft_tab_btn.update()
                store_inv_tab_btn.update()
                # Update dynamic buttons for the active sub‑tab
                if store_sub_tab == "cosmetics":
                    for btn in store_cos_buttons:
                        if btn.visible:
                            btn.update()
                elif store_sub_tab == "crafting":
                    for btn in store_craft_buttons:
                        if btn.visible:
                            btn.update()
                elif store_sub_tab == "inventory":
                    for btn in store_inv_add_buttons + store_inv_remove_buttons:
                        if btn.visible:
                            btn.update()
            # update chat scroll buttons
            buy_space_btn.update()

        # Toast countdown
        if toast_timer > 0:
            toast_timer -= 1
            if toast_timer == 0:
                toast = ""

        # Draw everything
        # Draw desktop background
        screen.fill(COLOR_DESKTOP)

        if mode == "start":
            # draw a window for starting parameters
            win_rect = start_window_rect
            # window background
            pygame.draw.rect(screen, COLOR_WINDOW, win_rect)
            # window border (outer dark, inner light)
            # Outer border
            pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, win_rect, 2)
            # Title bar
            title_bar_rect = pygame.Rect(win_rect.x, win_rect.y, win_rect.width, TITLE_BAR_HEIGHT)
            pygame.draw.rect(screen, COLOR_TITLE_BAR, title_bar_rect)
            title_txt = font_title.render("Inventory Stock Manager", True, COLOR_TITLE_TEXT)
            screen.blit(title_txt, (title_bar_rect.x + 6, title_bar_rect.y + (TITLE_BAR_HEIGHT - title_txt.get_height())//2))
            # Body area
            body_rect = pygame.Rect(win_rect.x, win_rect.y + TITLE_BAR_HEIGHT, win_rect.width, win_rect.height - TITLE_BAR_HEIGHT)
            pygame.draw.rect(screen, COLOR_WINDOW, body_rect)
            # Body border (simulate 3D panel)
            # highlight top/left
            pygame.draw.line(screen, COLOR_WINDOW_BORDER_LIGHT, (body_rect.x, body_rect.y), (body_rect.x + body_rect.width - 1, body_rect.y))
            pygame.draw.line(screen, COLOR_WINDOW_BORDER_LIGHT, (body_rect.x, body_rect.y), (body_rect.x, body_rect.y + body_rect.height - 1))
            # shadow bottom/right
            pygame.draw.line(screen, COLOR_WINDOW_BORDER_DARK, (body_rect.x, body_rect.y + body_rect.height - 1), (body_rect.x + body_rect.width - 1, body_rect.y + body_rect.height - 1))
            pygame.draw.line(screen, COLOR_WINDOW_BORDER_DARK, (body_rect.x + body_rect.width - 1, body_rect.y), (body_rect.x + body_rect.width - 1, body_rect.y + body_rect.height - 1))
            # draw label and input
            label = font_medium.render("Starting Cash:", True, COLOR_CONTROL_TEXT)
            label_x = win_rect.x + 40
            label_y = win_rect.y + TITLE_BAR_HEIGHT + 40
            screen.blit(label, (label_x, label_y))
            # position input box relative to window
            start_input.rect.topleft = (label_x + 150, label_y - 4)
            start_input.rect.size = (80, 24)
            start_input.draw(screen, font_medium)
            # start button
            if not start_button:
                btn_rect = pygame.Rect(0, 0, 100, 28)
                btn_rect.center = (win_rect.centerx, label_y + 60)
                def on_start():
                    nonlocal player, shop, inv, shop_offset, inv_offset, cash_history
                    nonlocal next_day_btn, tab_market_btn, tab_weekly_btn, tab_news_btn, tab_store_btn
                    nonlocal buy_space_btn, inc_space_btn, dec_space_btn
                    nonlocal report_prev_btn, report_next_btn, selected_report_week
                    nonlocal news_prev_btn, news_next_btn, selected_news_week
                    nonlocal up_shop_btn, down_shop_btn, up_inv_btn, down_inv_btn
                    nonlocal app_tab, store_sub_tab
                    nonlocal chat_messages, chat_offset, avg_buy_prices, chat_up_btn, chat_down_btn
                    nonlocal store_cos_buttons, store_craft_inputs, store_craft_buttons
                    nonlocal store_inv_add_buttons, store_inv_remove_buttons
                    nonlocal store_inv_custom_add_input, store_inv_custom_remove_input
                    nonlocal cosmetics_list
                    nonlocal store_cos_tab_btn, store_craft_tab_btn, store_inv_tab_btn
                    try:
                        starting_cash = start_input.value_int()
                    except Exception:
                        starting_cash = DEFAULT_STARTING_CASH
                    if starting_cash <= 0:
                        set_toast("Starting cash must be > 0")
                        return
                    # reset files for new game
                    for p in [SHOP_CSV, INV_CSV, PLAYER_CSV, TXN_CSV, WEEKLY_REPORT_CSV, PREVIOUS_NEWS_CSV]:
                        if os.path.exists(p):
                            os.remove(p)
                    init_shop_from_items(items)
                    init_inventory_if_missing()
                    init_player_if_missing(starting_cash)
                    player = load_player()
                    shop = load_shop()
                    inv = load_inventory()
                    cash_history = [(player["day"], player["cash"])]
                    # reset offsets
                    shop_offset = 0
                    inv_offset = 0
                    chat_messages = []
                    chat_offset = 0
                    # initialise average buy prices for each SKU with current buy price
                    avg_buy_prices = {sku: shop[sku]["buy_price"] for sku in shop.keys()}

                    # -----------------------------------------------------------------
                    # Load cosmetics catalogue and apply player selected cosmetic options
                    # Seed the cosmetics file if necessary
                    seed_cosmetics_if_missing()
                    cosmetics_list = load_cosmetics()
                    # Apply the player's selected theme and UI skin immediately so the
                    # interface reflects their last choice at the start of the game.
                    style.apply_theme(player.get("theme", style.CURRENT_THEME))
                    style.apply_ui_skin(player.get("ui_skin", style.CURRENT_UI_SKIN))
                    # Refresh our locally cached style constants so colours and
                    # border radii update instantly.  Without this call the UI
                    # would remain stuck on the previous theme/skin values.
                    refresh_style_from_module()
                    # Configure the screensaver to the player's stored choice.  If
                    # "None" this effectively disables the screensaver until they
                    # select another option in the Store.
                    ss_manager.set(player.get("screensaver", "None"))

                    # -----------------------------------------------------------------
                    # Create the Store tab and its sub‑tab buttons.  Clicking the Store
                    # tab switches the top‑level app_tab to "store".  Within the Store
                    # players can navigate between Cosmetics, Crafting and Inventory
                    # upgrades via sub‑tab buttons.  All buttons are created here and
                    # their positions are adjusted during the draw phase.
                    def go_store():
                        nonlocal app_tab
                        app_tab = "store"
                    tab_store_btn = RetroButton(pygame.Rect(0,0,100,24), "Store", go_store)
                    # Sub‑tab callbacks
                    def go_cosmetics():
                        nonlocal store_sub_tab
                        store_sub_tab = "cosmetics"
                        # Refresh dynamic widgets when switching tabs so the
                        # displayed controls (e.g. quantity inputs) match the
                        # current inventory and cosmetic state.
                        update_store_widgets()

                    def go_crafting():
                        nonlocal store_sub_tab
                        store_sub_tab = "crafting"
                        update_store_widgets()

                    def go_inventory():
                        nonlocal store_sub_tab
                        store_sub_tab = "inventory"
                        update_store_widgets()
                    store_cos_tab_btn = RetroButton(pygame.Rect(0,0,120,24), "Cosmetics", go_cosmetics)
                    store_craft_tab_btn = RetroButton(pygame.Rect(0,0,120,24), "Crafting", go_crafting)
                    store_inv_tab_btn = RetroButton(pygame.Rect(0,0,120,24), "Inventory", go_inventory)
                    # Reset dynamic store widget lists and custom inputs
                    store_cos_buttons = []
                    store_craft_inputs = []
                    store_craft_buttons = []
                    store_inv_add_buttons = []
                    store_inv_remove_buttons = []
                    store_inv_custom_add_input = InputBox((0,0,60,20), text="", numeric=True)
                    store_inv_custom_remove_input = InputBox((0,0,60,20), text="", numeric=True)

                    # Initialise store widgets based on current inventory and capacity
                    update_store_widgets()
                    # create scroll buttons and action buttons
                    # positions depend on layout, will update during draw
                    next_day_btn = RetroButton(pygame.Rect(0,0,100,30), "Next Day", advance_day)

                    # Tabs (always available)
                    def go_market():
                        nonlocal app_tab
                        app_tab = "market"
                    def go_weekly():
                        nonlocal app_tab
                        app_tab = "weekly"
                    def go_news():
                        nonlocal app_tab
                        app_tab = "news"
                    tab_market_btn = RetroButton(pygame.Rect(0,0,120,24), "Market", go_market)
                    tab_weekly_btn = RetroButton(pygame.Rect(0,0,140,24), "Weekly Report", go_weekly)
                    tab_news_btn = RetroButton(pygame.Rect(0,0,100,24), "News", go_news)

                    # Storage buttons live on the Weekly Report tab
                    inc_space_btn = RetroButton(pygame.Rect(0,0,160,30), "Increase Inventory", increase_space)
                    dec_space_btn = RetroButton(pygame.Rect(0,0,160,30), "Decrease Inventory", decrease_space)
                    # Hide the legacy inventory buttons since capacity is now adjusted via the Store
                    inc_space_btn.visible = False
                    dec_space_btn.visible = False

                    # Weekly report navigation (prev/next week)
                    def report_prev():
                        nonlocal selected_report_week
                        rows = load_weekly_reports_typed()
                        if not rows:
                            return
                        min_w = rows[0]["week"]
                        selected_report_week = max(min_w, selected_report_week - 1)

                    def report_next():
                        nonlocal selected_report_week
                        rows = load_weekly_reports_typed()
                        if not rows:
                            return
                        max_w = rows[-1]["week"]
                        selected_report_week = min(max_w, selected_report_week + 1)

                    report_prev_btn = RetroButton(pygame.Rect(0,0,26,22), "<", report_prev)
                    report_next_btn = RetroButton(pygame.Rect(0,0,26,22), ">", report_next)

                    # -----------------------------------------------------------------
                    # News navigation (prev/next week)
                    # The news tab shows a weekly feed of news events.  Each news item
                    # persists for the duration defined in the news CSV.  Players can
                    # navigate between weeks using these buttons.
                    def news_prev():
                        nonlocal selected_news_week
                        weeks = market.get_news_weeks(PREVIOUS_NEWS_CSV)
                        if not weeks:
                            return
                        min_w = weeks[0]
                        selected_news_week = max(min_w, selected_news_week - 1)

                    def news_next():
                        nonlocal selected_news_week
                        weeks = market.get_news_weeks(PREVIOUS_NEWS_CSV)
                        if not weeks:
                            return
                        max_w = weeks[-1]
                        selected_news_week = min(max_w, selected_news_week + 1)

                    news_prev_btn = RetroButton(pygame.Rect(0,0,26,22), "<", news_prev)
                    news_next_btn = RetroButton(pygame.Rect(0,0,26,22), ">", news_next)

                    # Ensure the previous news CSV exists
                    market.init_previous_news_if_missing(PREVIOUS_NEWS_CSV)
                    # Default selected news week = latest week with news or current week if none
                    news_weeks = market.get_news_weeks(PREVIOUS_NEWS_CSV)
                    selected_news_week = news_weeks[-1] if news_weeks else week_number(player["day"])
                    # Default selected report week = latest (if any)
                    rows = load_weekly_reports_typed()
                    selected_report_week = rows[-1]["week"] if rows else 1

                    # Retain buy_space_btn for backward compatibility (hidden)
                    buy_space_btn = RetroButton(pygame.Rect(0,0,100,30), "Change", purchase_space)
                    up_shop_btn = RetroButton(pygame.Rect(0,0,20,20), "^", scroll_shop_up)
                    down_shop_btn = RetroButton(pygame.Rect(0,0,20,20), "v", scroll_shop_down)
                    up_inv_btn = RetroButton(pygame.Rect(0,0,20,20), "^", scroll_inv_up)
                    down_inv_btn = RetroButton(pygame.Rect(0,0,20,20), "v", scroll_inv_down)
                    # chat scroll buttons
                    chat_up_btn = RetroButton(pygame.Rect(0,0,20,20), "^", scroll_chat_up)
                    chat_down_btn = RetroButton(pygame.Rect(0,0,20,20), "v", scroll_chat_down)
                    # update table widgets now that inv/shop exist
                    update_table_widgets()

                    # Weekly report navigation defaults to latest available week (or current week)
                    reports = load_weekly_reports_typed()
                    if reports:
                        selected_report_week = int(reports[-1].get("week", 1) or 1)
                    else:
                        selected_report_week = week_number(player["day"])
                    # switch to market mode
                    nonlocal mode
                    mode = "market"
                    # Default to the weekly report tab on Sundays
                    app_tab = "weekly" if is_sunday(player["day"]) else "market"
                    # If today is Friday, ensure today's news exists and impacts shop prices immediately.
                    dow = (player["day"] - 1) % BILL_INTERVAL  # Monday=0 ... Sunday=6
                    if dow == 4:  # Friday
                        try:
                            prev_rows = market.load_previous_news(PREVIOUS_NEWS_CSV)
                            has_today = any(int(float(r.get("day", 0) or 0)) == player["day"] for r in prev_rows)
                        except Exception:
                            has_today = False
                        if not has_today:
                            new_events = market.generate_news(player["day"], items, NEWS_CSV, PREVIOUS_NEWS_CSV)
                            if new_events:
                                market.apply_news_to_shop(shop, market.get_active_news(player["day"], PREVIOUS_NEWS_CSV))
                                save_shop(shop)
                                add_chat_message("Market news released! Check the News tab.")
                        app_tab = "news"
                        news_weeks = market.get_news_weeks(PREVIOUS_NEWS_CSV)
                        selected_news_week = news_weeks[-1] if news_weeks else week_number(player["day"])
                    set_toast("Welcome to the Market")
                start_button = RetroButton(btn_rect, "Start", on_start)
            else:
                start_button.rect = pygame.Rect(0,0,100,28)
                start_button.rect.center = (win_rect.centerx, label_y + 60)
            # draw start button
            start_button.update()
            start_button.draw(screen, font_medium)
            # display start message or toast
            if toast:
                msg_surf = font_medium.render(toast, True, COLOR_TOAST)
                screen.blit(msg_surf, (win_rect.x + 20, win_rect.bottom - 40))
        else:
            # Market mode draw
            # Draw outer window representing application
            app_rect = pygame.Rect(MARGIN, MARGIN, WIDTH - 2*MARGIN, HEIGHT - 2*MARGIN)
            pygame.draw.rect(screen, COLOR_WINDOW, app_rect)
            # draw 3D border for app_rect
            pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, app_rect, 2)
            # Title bar
            title_rect = pygame.Rect(app_rect.x, app_rect.y, app_rect.width, TITLE_BAR_HEIGHT)
            pygame.draw.rect(screen, COLOR_TITLE_BAR, title_rect)
            title_text = font_title.render("Inventory Stock Manager", True, COLOR_TITLE_TEXT)
            screen.blit(title_text, (title_rect.x + 6, title_rect.y + (TITLE_BAR_HEIGHT - title_text.get_height())//2))
            # HUD area
            hud_rect = pygame.Rect(app_rect.x + 4, app_rect.y + TITLE_BAR_HEIGHT + 4, app_rect.width - 8, HUD_HEIGHT)
            # Fill HUD background
            pygame.draw.rect(screen, COLOR_WINDOW, hud_rect)
            # Draw HUD text (show weekday)
            dow = (player['day'] - 1) % BILL_INTERVAL
            day_surf = font_medium.render(f"Day {player['day']}, {DAY_NAMES[dow]}", True, COLOR_CONTROL_TEXT)
            cash_surf = font_medium.render(f"Cash: ${player['cash']:.2f}", True, COLOR_CONTROL_TEXT)
            storage_surf = font_medium.render(f"Storage: {inv_used_units(inv)}/{player['capacity']}", True, COLOR_CONTROL_TEXT)
            net_worth = player["cash"] + sum((shop[sku]["buy_price"]*SPREAD) * inv[sku]["qty"] for sku in inv.keys())
            net_surf = font_medium.render(f"Net Worth: ${net_worth:.2f}", True, COLOR_CONTROL_TEXT)
            screen.blit(day_surf, (hud_rect.x + 8, hud_rect.y + 6))
            screen.blit(cash_surf, (hud_rect.x + 8, hud_rect.y + 28))
            screen.blit(storage_surf, (hud_rect.x + 180, hud_rect.y + 6))
            screen.blit(net_surf, (hud_rect.x + 180, hud_rect.y + 28))
            # Tabs (top-left inside the HUD)
            # Position the tab buttons relative to the HUD.  Tabs are laid out
            # horizontally with a small gap between them.  The market tab
            # anchors at an offset from the left of the HUD.
            # Position the primary tabs horizontally.  Place the Market tab at a
            # fixed offset within the HUD and space subsequent tabs by 5px.
            tab_market_btn.rect.topleft = (hud_rect.x + 420, hud_rect.y + 6)
            tab_weekly_btn.rect.topleft = (tab_market_btn.rect.right + 5, hud_rect.y + 6)
            tab_news_btn.rect.topleft = (tab_weekly_btn.rect.right + 5, hud_rect.y + 6)
            # The Store tab appears after the News tab once the game has started
            if tab_store_btn:
                tab_store_btn.rect.topleft = (tab_news_btn.rect.right + 5, hud_rect.y + 6)
            # Draw the tabs
            tab_market_btn.draw(screen, font_small)
            tab_weekly_btn.draw(screen, font_small)
            tab_news_btn.draw(screen, font_small)
            if tab_store_btn:
                tab_store_btn.draw(screen, font_small)

            # Position action buttons next to HUD
            next_day_btn.rect.topleft = (hud_rect.right - 220, hud_rect.y + 4)
            next_day_btn.draw(screen, font_small)

            # Storage buttons are only shown on the Weekly Report tab
            if app_tab == "weekly":
                inc_space_btn.rect.topleft = (hud_rect.right - 220, hud_rect.y + 28)
                dec_space_btn.rect.topleft = (hud_rect.right - 110, hud_rect.y + 28)
                inc_space_btn.draw(screen, font_small)
                dec_space_btn.draw(screen, font_small)
            # Table positions
            left_table_x = app_rect.x + 6
            right_table_x = left_table_x + TABLE_WIDTH + SPACING
            table_top_y = hud_rect.bottom + 8
            # Draw left table (Shop)
            # Outer panel
            shop_panel = pygame.Rect(left_table_x, table_top_y, TABLE_WIDTH, TABLE_HEIGHT)
            pygame.draw.rect(screen, COLOR_WINDOW, shop_panel)
            pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, shop_panel, 1)
            # Header bar
            shop_header = pygame.Rect(shop_panel.x, shop_panel.y, shop_panel.width, HEADER_HEIGHT)
            pygame.draw.rect(screen, COLOR_TABLE_HEADER, shop_header)
            header_text = font_medium.render("Shop", True, COLOR_TABLE_HEADER_TEXT)
            screen.blit(header_text, (shop_header.x + 6, shop_header.y + (HEADER_HEIGHT - header_text.get_height())//2))
            # Scroll buttons for shop
            up_shop_btn.rect = pygame.Rect(shop_panel.right - 24, shop_panel.y + HEADER_HEIGHT + 2, 20, SCROLL_BUTTON_HEIGHT)
            down_shop_btn.rect = pygame.Rect(shop_panel.right - 24, shop_panel.bottom - SCROLL_BUTTON_HEIGHT - 2, 20, SCROLL_BUTTON_HEIGHT)
            up_shop_btn.label = "^"
            down_shop_btn.label = "v"
            up_shop_btn.draw(screen, font_small)
            down_shop_btn.draw(screen, font_small)
            # Draw column header row for shop
            col_header_y = shop_panel.y + HEADER_HEIGHT + SCROLL_BUTTON_HEIGHT + 4
            # background for header row
            pygame.draw.rect(screen, COLOR_WINDOW, (shop_panel.x + 1, col_header_y, shop_panel.width - 2 - 24, ROW_HEIGHT))
            # draw column header names
            x_offset = shop_panel.x + 4
            for idx, col_w in enumerate(SHOP_COL_WIDTHS):
                header_name = SHOP_HEADERS[idx]
                # avoid drawing header for button column (last col) as label is blank
                if header_name:
                    hdr_surf = font_small.render(header_name, True, COLOR_CONTROL_TEXT)
                    screen.blit(hdr_surf, (x_offset + 2, col_header_y + 5))
                x_offset += col_w
            # Draw shop rows below header
            row_area_y = col_header_y + ROW_HEIGHT
            for i in range(VISIBLE_ROWS):
                row_y = row_area_y + i * ROW_HEIGHT
                # shading
                row_col = COLOR_ROW_LIGHT if i % 2 == 0 else COLOR_ROW_DARK
                pygame.draw.rect(screen, row_col, (shop_panel.x + 1, row_y, shop_panel.width - 2 - 24, ROW_HEIGHT))
                if shop_offset + i < len(sorted(shop.keys())):
                    sku = sorted(shop.keys())[shop_offset + i]
                    item = items[sku]
                    s = shop[sku]
                    # track x position per column
                    x_pos = shop_panel.x + 4
                    # column 0: image
                    img = load_image_or_placeholder(item["image"], size=(20,20), colour=(160,160,160))
                    screen.blit(img, (x_pos + (SHOP_COL_WIDTHS[0] - 20)//2, row_y + 3))
                    x_pos += SHOP_COL_WIDTHS[0]
                    # column 1: sku
                    sku_surf = font_small.render(sku, True, COLOR_CONTROL_TEXT)
                    screen.blit(sku_surf, (x_pos + 2, row_y + 6))
                    x_pos += SHOP_COL_WIDTHS[1]
                    # column 2: description (truncate)
                    desc_text = item["description"]
                    desc_surf = font_small.render(desc_text[:25], True, COLOR_CONTROL_TEXT)
                    screen.blit(desc_surf, (x_pos + 2, row_y + 6))
                    x_pos += SHOP_COL_WIDTHS[2]                    
                    # column 3: average buy price
                    avg_val = avg_buy_prices.get(sku, s["buy_price"])
                    avg_surf = font_small.render(f"${avg_val:.2f}", True, COLOR_CONTROL_TEXT)
                    screen.blit(avg_surf, (x_pos + 2, row_y + 6))
                    x_pos += SHOP_COL_WIDTHS[3]
                    # column 4: current price
                    price_surf = font_small.render(f"${s['buy_price']:.2f}", True, COLOR_CONTROL_TEXT)
                    screen.blit(price_surf, (x_pos + 2, row_y + 6))
                    x_pos += SHOP_COL_WIDTHS[4]
                    # column 5: qty available
                    qty_surf = font_small.render(str(s["qty"]), True, COLOR_CONTROL_TEXT)
                    screen.blit(qty_surf, (x_pos + 2, row_y + 6))
                    x_pos += SHOP_COL_WIDTHS[5]
                    # column 6: input box for qty to buy
                    shop_inputs[i].rect.topleft = (x_pos + 2, row_y + 3)
                    shop_inputs[i].rect.size = (SHOP_COL_WIDTHS[6] - 4, ROW_HEIGHT - 6)
                    shop_inputs[i].draw(screen, font_small)
                    x_pos += SHOP_COL_WIDTHS[6]
                    # column 7: button
                    shop_buttons[i].rect.topleft = (x_pos + 2, row_y + 3)
                    shop_buttons[i].rect.size = (SHOP_COL_WIDTHS[7] - 4, ROW_HEIGHT - 6)
                    shop_buttons[i].draw(screen, font_small)
                else:
                    # hide input & button for empty rows
                    shop_inputs[i].rect.topleft = (shop_panel.x, shop_panel.y)
                    shop_inputs[i].rect.size = (0,0)
                    shop_buttons[i].rect.topleft = (shop_panel.x, shop_panel.y)
                    shop_buttons[i].rect.size = (0,0)
            # Right table (Inventory)
            inv_panel = pygame.Rect(right_table_x, table_top_y, TABLE_WIDTH, TABLE_HEIGHT)
            pygame.draw.rect(screen, COLOR_WINDOW, inv_panel)
            pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, inv_panel, 1)
            # Header bar
            inv_header = pygame.Rect(inv_panel.x, inv_panel.y, inv_panel.width, HEADER_HEIGHT)
            pygame.draw.rect(screen, COLOR_TABLE_HEADER, inv_header)
            inv_header_text = font_medium.render("Inventory", True, COLOR_TABLE_HEADER_TEXT)
            screen.blit(inv_header_text, (inv_header.x + 6, inv_header.y + (HEADER_HEIGHT - inv_header_text.get_height())//2))
            # Scroll buttons for inventory
            up_inv_btn.rect = pygame.Rect(inv_panel.right - 24, inv_panel.y + HEADER_HEIGHT + 2, 20, SCROLL_BUTTON_HEIGHT)
            down_inv_btn.rect = pygame.Rect(inv_panel.right - 24, inv_panel.bottom - SCROLL_BUTTON_HEIGHT - 2, 20, SCROLL_BUTTON_HEIGHT)
            up_inv_btn.label = "^"
            down_inv_btn.label = "v"
            up_inv_btn.draw(screen, font_small)
            down_inv_btn.draw(screen, font_small)
            # Column header row for inventory
            inv_col_header_y = inv_panel.y + HEADER_HEIGHT + SCROLL_BUTTON_HEIGHT + 4
            pygame.draw.rect(screen, COLOR_WINDOW, (inv_panel.x + 1, inv_col_header_y, inv_panel.width - 2 - 24, ROW_HEIGHT))
            x_offset = inv_panel.x + 4
            for idx, col_w in enumerate(INV_COL_WIDTHS):
                header_name = INV_HEADERS[idx]
                if header_name:
                    hdr_surf = font_small.render(header_name, True, COLOR_CONTROL_TEXT)
                    screen.blit(hdr_surf, (x_offset + 2, inv_col_header_y + 5))
                x_offset += col_w
            # Draw inventory rows below header
            inv_row_start_y = inv_col_header_y + ROW_HEIGHT
            for i in range(VISIBLE_ROWS):
                row_y = inv_row_start_y + i * ROW_HEIGHT
                row_col = COLOR_ROW_LIGHT if i % 2 == 0 else COLOR_ROW_DARK
                pygame.draw.rect(screen, row_col, (inv_panel.x + 1, row_y, inv_panel.width - 2 - 24, ROW_HEIGHT))
                if inv_offset + i < len(sorted(inv.keys())):
                    sku = sorted(inv.keys())[inv_offset + i]
                    item = items[sku]
                    iv = inv[sku]
                    x_pos = inv_panel.x + 4
                    # column 0: image
                    img = load_image_or_placeholder(item["image"], size=(20,20), colour=(160,160,160))
                    screen.blit(img, (x_pos + (INV_COL_WIDTHS[0] - 20)//2, row_y + 3))
                    x_pos += INV_COL_WIDTHS[0]
                    # column 1: sku
                    sku_surf = font_small.render(sku, True, COLOR_CONTROL_TEXT)
                    screen.blit(sku_surf, (x_pos + 2, row_y + 6))
                    x_pos += INV_COL_WIDTHS[1]
                    # column 2: description
                    desc_text = item["description"]
                    desc_surf = font_small.render(desc_text[:25], True, COLOR_CONTROL_TEXT)
                    screen.blit(desc_surf, (x_pos + 2, row_y + 6))
                    x_pos += INV_COL_WIDTHS[2]
                    # column 3: avg cost
                    avg_surf = font_small.render(f"${iv['avg_cost']:.2f}", True, COLOR_CONTROL_TEXT)
                    screen.blit(avg_surf, (x_pos + 2, row_y + 6))
                    x_pos += INV_COL_WIDTHS[3]
                    # column 4: sell price
                    sell_price = shop[sku]["buy_price"] * SPREAD
                    sell_surf = font_small.render(f"${sell_price:.2f}", True, COLOR_CONTROL_TEXT)
                    screen.blit(sell_surf, (x_pos + 2, row_y + 6))
                    x_pos += INV_COL_WIDTHS[4]
                    # column 5: quantity on hand
                    qty_surf = font_small.render(str(iv["qty"]), True, COLOR_CONTROL_TEXT)
                    screen.blit(qty_surf, (x_pos + 2, row_y + 6))
                    x_pos += INV_COL_WIDTHS[5]                    
                    # column 6: input
                    inv_inputs[i].rect.topleft = (x_pos + 2, row_y + 3)
                    inv_inputs[i].rect.size = (INV_COL_WIDTHS[6] - 4, ROW_HEIGHT - 6)
                    inv_inputs[i].draw(screen, font_small)
                    x_pos += INV_COL_WIDTHS[6]
                    # column 7: button
                    inv_buttons[i].rect.topleft = (x_pos + 2, row_y + 3)
                    inv_buttons[i].rect.size = (INV_COL_WIDTHS[7] - 4, ROW_HEIGHT - 6)
                    inv_buttons[i].draw(screen, font_small)
                else:
                    # hide input & button
                    inv_inputs[i].rect.topleft = (inv_panel.x, inv_panel.y)
                    inv_inputs[i].rect.size = (0,0)
                    inv_buttons[i].rect.topleft = (inv_panel.x, inv_panel.y)
                    inv_buttons[i].rect.size = (0,0)

            # ---------------------------------------------------------
            # Weekly Report tab overlay
            # ---------------------------------------------------------
            if app_tab == "weekly":
                report_panel = pygame.Rect(left_table_x, table_top_y, (TABLE_WIDTH * 2) + SPACING, REPORT_HEIGHT)
                pygame.draw.rect(screen, COLOR_WINDOW, report_panel)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, report_panel, 1)

                # Header bar
                rep_header = pygame.Rect(report_panel.x, report_panel.y, report_panel.width, HEADER_HEIGHT)
                pygame.draw.rect(screen, COLOR_TABLE_HEADER, rep_header)
                rep_title = font_medium.render("Weekly Store Report", True, COLOR_TABLE_HEADER_TEXT)
                screen.blit(rep_title, (rep_header.x + 6, rep_header.y + (HEADER_HEIGHT - rep_title.get_height())//2))

                # Load reports and show the selected week
                reports = load_weekly_reports_typed()
                if reports:
                    # Clamp selected week to available range
                    selected_report_week = max(reports[0]["week"], min(reports[-1]["week"], selected_report_week))
                    rep = get_report_by_week(reports, selected_report_week) or reports[-1]
                else:
                    rep = None

                text_x_l = report_panel.x + 18
                text_x_r = report_panel.x + report_panel.width // 2 + 40
                y_top = rep_header.bottom + 18
                line_h = 26

                if not rep:
                    report_prev_btn.visible = False
                    report_next_btn.visible = False
                    msg = "No weekly report yet. A report is created each Sunday."
                    screen.blit(font_medium.render(msg, True, COLOR_CONTROL_TEXT), (text_x_l, y_top))
                else:
                    week = int(rep.get("week", 0) or 0)
                    rent_cost = float(rep.get("rent_cost", 0) or 0)
                    bought_total = float(rep.get("bought_total", 0) or 0)
                    bought_qty = int(rep.get("bought_qty", 0) or 0)
                    bought_lines = int(rep.get("bought_lines", 0) or 0)
                    sold_total = float(rep.get("sold_total", 0) or 0)
                    sold_qty = int(rep.get("sold_qty", 0) or 0)
                    sold_lines = int(rep.get("sold_lines", 0) or 0)
                    weekly_profit = float(rep.get("weekly_profit", 0) or 0)
                    cash_total = float(rep.get("cash_total", 0) or 0)
                    net_worth_v = float(rep.get("net_worth", 0) or 0)
                    storage_used = int(rep.get("storage_used", 0) or 0)
                    storage_cap = max(1, int(rep.get("storage_capacity", 1) or 1))
                    storage_util = float(rep.get("storage_utilization", 0) or 0)

                    # Dynamic note (comma-separated)
                    note = compute_dynamic_notes(rep)

                    # Title + navigation arrows
                    title_txt = f"WEEK {week} STORE REPORT"
                    center_title = font_large.render(title_txt, True, COLOR_CONTROL_TEXT)
                    title_x = report_panel.centerx - center_title.get_width() // 2
                    title_y = y_top
                    screen.blit(center_title, (title_x, title_y))

                    # Position arrows around the title
                    # Hide arrows if only 1 report exists
                    if len(reports) <= 1:
                        report_prev_btn.visible = False
                        report_next_btn.visible = False
                    else:
                        report_prev_btn.visible = True
                        report_next_btn.visible = True
                        gap = 12
                        report_prev_btn.rect.topleft = (
                            title_x - gap - report_prev_btn.rect.width,
                            title_y + 2,
                        )
                        report_next_btn.rect.topleft = (
                            title_x + center_title.get_width() + gap,
                            title_y + 2,
                        )
                        # Disable at ends
                        report_prev_btn.visible = (selected_report_week > reports[0]["week"])
                        report_next_btn.visible = (selected_report_week < reports[-1]["week"])
                        report_prev_btn.draw(screen, font_small)
                        report_next_btn.draw(screen, font_small)

                    underline = font_medium.render("_" * 30, True, COLOR_CONTROL_TEXT)
                    screen.blit(underline, (report_panel.centerx - underline.get_width() // 2, title_y + 24))

                    # Small helpers
                    red = (140, 0, 0)
                    green = (0, 110, 0)

                    def money(v):
                        return f"${v:,.2f}" if abs(v) >= 1 else f"${v:.2f}"

                    def draw_heading(txt, x, y):
                        surf = font_medium.render(txt, True, COLOR_CONTROL_TEXT)
                        screen.blit(surf, (x, y))

                    def draw_kv(label, value, x, y, vcol=COLOR_CONTROL_TEXT):
                        screen.blit(font_medium.render(label + ":", True, COLOR_CONTROL_TEXT), (x, y))
                        screen.blit(font_medium.render(value, True, vcol), (x + 170, y))

                    # Layout blocks (Cost / Sales / Results)
                    y0 = title_y + 60
                    x1 = text_x_l
                    x2 = text_x_r

                    # COSTS
                    draw_heading("COSTS", x1, y0)
                    draw_kv("Rent", money(rent_cost), x1, y0 + line_h, red)
                    draw_kv("Bought", money(bought_total), x1, y0 + line_h * 2, red)
                    draw_kv("Bought Qty", str(bought_qty), x1, y0 + line_h * 3)
                    draw_kv("Bought Lines", str(bought_lines), x1, y0 + line_h * 4)

                    # SALES
                    y_sales = y0 + line_h * 6
                    draw_heading("SALES", x1, y_sales)
                    draw_kv("Sold", money(sold_total), x1, y_sales + line_h, green)
                    draw_kv("Sold Qty", str(sold_qty), x1, y_sales + line_h * 2)
                    draw_kv("Sold Lines", str(sold_lines), x1, y_sales + line_h * 3)

                    # RESULTS
                    draw_heading("RESULTS", x2, y0)
                    pcol = green if weekly_profit >= 0 else red
                    draw_kv("Weekly Profit", money(weekly_profit), x2, y0 + line_h, pcol)
                    draw_kv("Cash Total", money(cash_total), x2, y0 + line_h * 2)
                    draw_kv("Net Worth", money(net_worth_v), x2, y0 + line_h * 3)
                    util_pct = int(storage_util * 100)
                    draw_kv("Storage", f"{util_pct}% ({storage_used}/{storage_cap})", x2, y0 + line_h * 4)

                    # NOTES
                    note_y = report_panel.bottom - 70
                    screen.blit(font_medium.render("Notes:", True, COLOR_CONTROL_TEXT), (text_x_l, note_y))
                    # wrap notes to fit
                    max_w = report_panel.width - 120
                    words = (note or "").split(" ")
                    lines = []
                    cur = ""
                    for w in words:
                        test = (cur + " " + w).strip()
                        if font_medium.size(test)[0] <= max_w:
                            cur = test
                        else:
                            if cur:
                                lines.append(cur)
                            cur = w
                    if cur:
                        lines.append(cur)
                    for li, line in enumerate(lines[:2]):
                        screen.blit(font_medium.render(line, True, COLOR_CONTROL_TEXT), (text_x_l + 70, note_y + li * 22))

            # -----------------------------------------------------------------
            # News tab overlay
            # When the News tab is active this section renders news events for
            # the selected week.  News items are generated every Friday and
            # persisted to previous_news.csv.  Players can use the arrow
            # buttons to navigate between weeks.
            if app_tab == "news":
                news_panel = pygame.Rect(left_table_x, table_top_y, (TABLE_WIDTH * 2) + SPACING, REPORT_HEIGHT)
                pygame.draw.rect(screen, COLOR_WINDOW, news_panel)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, news_panel, 1)

                # Header bar
                news_header = pygame.Rect(news_panel.x, news_panel.y, news_panel.width, HEADER_HEIGHT)
                pygame.draw.rect(screen, COLOR_TABLE_HEADER, news_header)
                news_title = font_medium.render("Market News", True, COLOR_TABLE_HEADER_TEXT)
                screen.blit(news_title, (news_header.x + 6, news_header.y + (HEADER_HEIGHT - news_title.get_height())//2))

                # Determine available weeks and clamp the selected week
                weeks_available = market.get_news_weeks(PREVIOUS_NEWS_CSV)
                if weeks_available:
                    if selected_news_week < weeks_available[0]:
                        selected_news_week = weeks_available[0]
                    if selected_news_week > weeks_available[-1]:
                        selected_news_week = weeks_available[-1]

                # Title line with week number
                title_str = f"WEEK {selected_news_week} NEWS"
                center_title = font_large.render(title_str, True, COLOR_CONTROL_TEXT)
                title_x = news_panel.centerx - center_title.get_width() // 2
                title_y = news_header.bottom + 16
                screen.blit(center_title, (title_x, title_y))

                # Position navigation arrows around the title
                if len(weeks_available) > 1:
                    gap = 12
                    news_prev_btn.visible = (selected_news_week > weeks_available[0])
                    news_next_btn.visible = (selected_news_week < weeks_available[-1])
                    news_prev_btn.rect.topleft = (title_x - gap - news_prev_btn.rect.width, title_y + 2)
                    news_next_btn.rect.topleft = (title_x + center_title.get_width() + gap, title_y + 2)
                    news_prev_btn.draw(screen, font_small)
                    news_next_btn.draw(screen, font_small)
                else:
                    news_prev_btn.visible = False
                    news_next_btn.visible = False

                # Underline under the title
                underline = font_medium.render("_" * 30, True, COLOR_CONTROL_TEXT)
                screen.blit(underline, (news_panel.centerx - underline.get_width() // 2, title_y + 24))

                # Load news events for the selected week
                events = market.get_news_for_week(selected_news_week, PREVIOUS_NEWS_CSV)

                # Area to render the news items
                content_x = news_panel.x + 18
                y_cursor = title_y + 50
                line_height = 22
                max_width = news_panel.width - 36
                if not events:
                    msg = "No news yet. New reports are published each Friday."
                    screen.blit(font_medium.render(msg, True, COLOR_CONTROL_TEXT), (content_x, y_cursor))
                else:
                    for ev in events:
                        # Headline
                        headline = ev.get("headline", "")
                        headline_surf = font_medium.render(headline, True, COLOR_CONTROL_TEXT)
                        screen.blit(headline_surf, (content_x, y_cursor))
                        y_cursor += line_height
                        # Article (wrap text using font_small measurement)
                        article = ev.get("article", "")
                        words = article.split(" ")
                        line = ""
                        for w in words:
                            test = (line + " " + w).strip()
                            if font_small.size(test)[0] <= max_width - 20:
                                line = test
                            else:
                                screen.blit(font_small.render(line, True, COLOR_CONTROL_TEXT), (content_x + 20, y_cursor))
                                y_cursor += line_height
                                line = w
                        if line:
                            screen.blit(font_small.render(line, True, COLOR_CONTROL_TEXT), (content_x + 20, y_cursor))
                            y_cursor += line_height
                        # Impact line
                        try:
                            impact_val = float(ev.get("impact", 0) or 0)
                        except Exception:
                            impact_val = 0.0
                        if impact_val > 0:
                            impact_col = (0, 110, 0)
                            imp_text = f"Impact on price: +${impact_val:.2f}"
                        elif impact_val < 0:
                            impact_col = (140, 0, 0)
                            imp_text = f"Impact on price: -${abs(impact_val):.2f}"
                        else:
                            impact_col = COLOR_CONTROL_TEXT
                            imp_text = f"Impact on price: ${impact_val:.2f}"
                        screen.blit(font_small.render(imp_text, True, impact_col), (content_x, y_cursor))
                        y_cursor += line_height
                        # Duration line
                        dur = ev.get("duration", "1")
                        screen.blit(font_small.render(f"Expected duration in days this will last: {dur}", True, COLOR_CONTROL_TEXT), (content_x, y_cursor))
                        y_cursor += line_height + 6  # extra space before next item

            # -----------------------------------------------------------------
            # Store tab overlay
            # When the Store tab is active this section renders the store
            # interface with sub‑tabs for cosmetics, crafting and inventory.
            if app_tab == "store":
                # Define the panel for the store overlay covering both tables
                store_panel = pygame.Rect(left_table_x, table_top_y, (TABLE_WIDTH * 2) + SPACING, REPORT_HEIGHT)
                # Background and border
                pygame.draw.rect(screen, COLOR_WINDOW, store_panel)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, store_panel, 1)
                # Header bar
                store_header = pygame.Rect(store_panel.x, store_panel.y, store_panel.width, HEADER_HEIGHT)
                pygame.draw.rect(screen, COLOR_TABLE_HEADER, store_header)
                store_title = font_medium.render("Store", True, COLOR_TABLE_HEADER_TEXT)
                screen.blit(store_title, (store_header.x + 6, store_header.y + (HEADER_HEIGHT - store_title.get_height())//2))
                # Define dimensions for sub‑tab navigation and content area
                sub_width = 140
                content_x = store_panel.x + sub_width + 8
                content_y = store_header.bottom + 4
                content_width = store_panel.width - sub_width - 12
                content_height = store_panel.height - HEADER_HEIGHT - 8
                # Draw sub‑tab navigation area background
                sub_rect = pygame.Rect(store_panel.x + 4, store_header.bottom + 4, sub_width - 8, store_panel.height - HEADER_HEIGHT - 8)
                pygame.draw.rect(screen, COLOR_WINDOW, sub_rect)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, sub_rect, 1)
                # Position sub‑tab buttons vertically
                btn_h = 28
                btn_pad = 4
                # Cosmetics tab
                store_cos_tab_btn.rect.topleft = (sub_rect.x + 4, sub_rect.y + 4)
                store_cos_tab_btn.rect.size = (sub_rect.width - 8, btn_h)
                # Highlight active tab visually WITHOUT breaking click handling.
                _prev_pressed = store_cos_tab_btn.pressed
                store_cos_tab_btn.pressed = _prev_pressed or (store_sub_tab == "cosmetics")
                store_cos_tab_btn.draw(screen, font_small)
                store_cos_tab_btn.pressed = _prev_pressed
                # Crafting tab
                store_craft_tab_btn.rect.topleft = (sub_rect.x + 4, sub_rect.y + 4 + (btn_h + btn_pad))
                store_craft_tab_btn.rect.size = (sub_rect.width - 8, btn_h)
                _prev_pressed = store_craft_tab_btn.pressed
                store_craft_tab_btn.pressed = _prev_pressed or (store_sub_tab == "crafting")
                store_craft_tab_btn.draw(screen, font_small)
                store_craft_tab_btn.pressed = _prev_pressed
                # Inventory tab
                store_inv_tab_btn.rect.topleft = (sub_rect.x + 4, sub_rect.y + 4 + 2 * (btn_h + btn_pad))
                store_inv_tab_btn.rect.size = (sub_rect.width - 8, btn_h)
                _prev_pressed = store_inv_tab_btn.pressed
                store_inv_tab_btn.pressed = _prev_pressed or (store_sub_tab == "inventory")
                store_inv_tab_btn.draw(screen, font_small)
                store_inv_tab_btn.pressed = _prev_pressed
                # Draw content based on active sub‑tab
                if store_sub_tab == "cosmetics":
                    # Cosmetics: list available cosmetics with status and buy/select buttons
                    row_h = 26
                    # Column widths: Name, Type, Status, Button
                    col1 = 240
                    col2 = 120
                    col3 = 120
                    col4 = 100
                    for i, cos in enumerate(cosmetics_list):
                        row_y = content_y + i * row_h
                        # alternating row colour
                        row_col = COLOR_ROW_LIGHT if i % 2 == 0 else COLOR_ROW_DARK
                        pygame.draw.rect(screen, row_col, (content_x, row_y, content_width, row_h))
                        # Name
                        name_surf = font_small.render(cos["name"], True, COLOR_CONTROL_TEXT)
                        screen.blit(name_surf, (content_x + 4, row_y + 6))
                        # Type
                        type_str = cos["type"].capitalize()
                        type_surf = font_small.render(type_str, True, COLOR_CONTROL_TEXT)
                        screen.blit(type_surf, (content_x + col1 + 4, row_y + 6))
                        # Status/Price
                        status_text = "Unlocked" if cos.get("unlocked") else f"$ {int(cos.get('price',0))}"
                        status_col = COLOR_CONTROL_TEXT
                        stat_surf = font_small.render(status_text, True, status_col)
                        screen.blit(stat_surf, (content_x + col1 + col2 + 4, row_y + 6))
                        # Button
                        if i < len(store_cos_buttons):
                            btn = store_cos_buttons[i]
                            # set button rect relative to this row
                            btn_w = col4 - 8
                            btn_h2 = row_h - 8
                            btn.rect = pygame.Rect(content_x + col1 + col2 + col3 + 4, row_y + 4, btn_w, btn_h2)
                            btn.draw(screen, font_small)
                elif store_sub_tab == "crafting":
                    # Crafting: show craftable pairs with qty input and convert button
                    header_h = 24
                    row_h = 28
                    col_img = 24
                    col_sku = 80
                    col_name = 200
                    col_arrow = 20
                    col_img2 = 24
                    col_sku2 = 80
                    col_name2 = 200
                    col_cost = 80
                    col_qty = 60
                    col_btn = 80
                    # Header row
                    header_rect = pygame.Rect(content_x, content_y, content_width, header_h)
                    pygame.draw.rect(screen, COLOR_TABLE_HEADER, header_rect)
                    xh = content_x + 4
                    # Columns: Img, SKU, Description, Cost, Img2, Sku2, Description2, Qty, Convert
                    headers = [
                        ("Img", col_img),
                        ("SKU", col_sku),
                        ("Description", col_name),
                        ("", col_arrow),
                        ("Img2", col_img2),
                        ("SKU2", col_sku2),
                        ("Description2", col_name2),
                        ("Cost", col_cost),
                        ("Qty", col_qty),
                        ("Convert", col_btn),
                    ]
                    for text, w in headers:
                        if text:
                            ts = font_small.render(text, True, COLOR_TABLE_HEADER_TEXT)
                            screen.blit(ts, (xh + 2, content_y + (header_h - ts.get_height())//2))
                        xh += w

                    # Recompute craftable list based on current inventory and items
                    craftables = []
                    for sku, itm in inv.items():
                        info = items.get(sku, {})
                        ctype = info.get("craft_type", "NULL")
                        out_sku = info.get("craft_output", "")
                        if ctype in ("RAW", "REFINED") and out_sku and out_sku in items:
                            craftables.append((sku, out_sku))
                    if not craftables:
                        msg = font_medium.render("Nothing craftable in inventory", True, COLOR_CONTROL_TEXT)
                        screen.blit(msg, (content_x + 8, content_y + header_h + 12))

                    for i, (in_sku, out_sku) in enumerate(craftables):
                        row_y = content_y + header_h + i * row_h
                        row_col = COLOR_ROW_LIGHT if i % 2 == 0 else COLOR_ROW_DARK
                        pygame.draw.rect(screen, row_col, (content_x, row_y, content_width, row_h))
                        x = content_x + 4
                        # Input image
                        img1 = load_image_or_placeholder(items[in_sku]["image"], size=(20,20), colour=(160,160,160))
                        screen.blit(img1, (x + (col_img - 20)//2, row_y + 4))
                        x += col_img
                        # Input SKU
                        sku_surf = font_small.render(in_sku, True, COLOR_CONTROL_TEXT)
                        screen.blit(sku_surf, (x + 2, row_y + 6))
                        x += col_sku
                        # Input Name (truncate)
                        in_name = items[in_sku]["description"]
                        in_surf = font_small.render(in_name[:25], True, COLOR_CONTROL_TEXT)
                        screen.blit(in_surf, (x + 2, row_y + 6))
                        x += col_name
                        # Arrow
                        arrow_surf = font_small.render("→", True, COLOR_CONTROL_TEXT)
                        screen.blit(arrow_surf, (x + (col_arrow - arrow_surf.get_width())//2, row_y + 6))
                        x += col_arrow
                        # Output image
                        img2 = load_image_or_placeholder(items[out_sku]["image"], size=(20,20), colour=(160,160,160))
                        screen.blit(img2, (x + (col_img2 - 20)//2, row_y + 4))
                        x += col_img2
                        # Output SKU
                        out_surf = font_small.render(out_sku, True, COLOR_CONTROL_TEXT)
                        screen.blit(out_surf, (x + 2, row_y + 6))
                        x += col_sku2
                        # Output Name
                        out_name = items[out_sku]["description"]
                        out_desc_surf = font_small.render(out_name[:25], True, COLOR_CONTROL_TEXT)
                        screen.blit(out_desc_surf, (x + 2, row_y + 6))
                        x += col_name2
                        # Cost per item (5% of shop price)
                        unit_cost = shop[out_sku]["buy_price"] * 0.05
                        cost_surf = font_small.render(f"${unit_cost:.2f}", True, COLOR_CONTROL_TEXT)
                        screen.blit(cost_surf, (x + 2, row_y + 6))
                        x += col_cost
                        # Quantity input
                        if i < len(store_craft_inputs):
                            ib = store_craft_inputs[i]
                            ib.rect = pygame.Rect(x + 2, row_y + 4, col_qty - 4, row_h - 8)
                            ib.draw(screen, font_small)
                        x += col_qty
                        # Convert button
                        if i < len(store_craft_buttons):
                            btn = store_craft_buttons[i]
                            btn.rect = pygame.Rect(x + 2, row_y + 4, col_btn - 4, row_h - 8)
                            btn.draw(screen, font_small)
                else:
                    # Inventory upgrades: capacity adjustments
                    # Top information
                    y_pos = content_y
                    # Display current capacity and usage
                    cap_text = f"Capacity: {player['capacity']}  (Used: {inv_used_units(inv)})"
                    cap_surf = font_medium.render(cap_text, True, COLOR_CONTROL_TEXT)
                    screen.blit(cap_surf, (content_x + 4, y_pos))
                    y_pos += 26
                    rent_text = f"Rent next Sunday: ${player['capacity']}"
                    rent_surf = font_medium.render(rent_text, True, COLOR_CONTROL_TEXT)
                    screen.blit(rent_surf, (content_x + 4, y_pos))
                    y_pos += 26
                    cash_text = f"Cash: ${player['cash']:.2f}"
                    cash_surf = font_medium.render(cash_text, True, COLOR_CONTROL_TEXT)
                    screen.blit(cash_surf, (content_x + 4, y_pos))
                    y_pos += 36
                    # Increase capacity row
                    inc_label = font_medium.render("Increase Capacity:", True, COLOR_CONTROL_TEXT)
                    screen.blit(inc_label, (content_x + 4, y_pos))
                    y_row = y_pos
                    x_pos = content_x + 180
                    increments = [1,5,10,100]
                    # Draw quick add buttons
                    for idx, inc in enumerate(increments):
                        if idx < len(store_inv_add_buttons):
                            btn = store_inv_add_buttons[idx]
                            if btn.visible:
                                btn.rect = pygame.Rect(x_pos, y_row, 60, 26)
                                btn.draw(screen, font_small)
                                x_pos += 64
                    # Custom input and Add button
                    store_inv_custom_add_input.rect = pygame.Rect(x_pos, y_row, 80, 26)
                    store_inv_custom_add_input.draw(screen, font_small)
                    x_pos += 84
                    if len(store_inv_add_buttons) > len(increments):
                        custom_add_btn = store_inv_add_buttons[len(increments)]
                        custom_add_btn.rect = pygame.Rect(x_pos, y_row, 60, 26)
                        custom_add_btn.draw(screen, font_small)
                    y_pos += 36
                    # Decrease capacity row
                    dec_label = font_medium.render("Decrease Capacity:", True, COLOR_CONTROL_TEXT)
                    screen.blit(dec_label, (content_x + 4, y_pos))
                    y_row = y_pos
                    x_pos = content_x + 180
                    for idx, inc in enumerate(increments):
                        if idx < len(store_inv_remove_buttons):
                            btn = store_inv_remove_buttons[idx]
                            if btn.visible:
                                btn.rect = pygame.Rect(x_pos, y_row, 60, 26)
                                btn.draw(screen, font_small)
                                x_pos += 64
                    store_inv_custom_remove_input.rect = pygame.Rect(x_pos, y_row, 80, 26)
                    store_inv_custom_remove_input.draw(screen, font_small)
                    x_pos += 84
                    if len(store_inv_remove_buttons) > len(increments):
                        custom_rem_btn = store_inv_remove_buttons[len(increments)]
                        custom_rem_btn.rect = pygame.Rect(x_pos, y_row, 60, 26)
                        custom_rem_btn.draw(screen, font_small)

            PANEL_PAD = 6
            HEADER_H = 20
            BTN_H = 16
            BTN_W = 20
            BTN_PAD = 2

            panel_x = app_rect.x + 4
            panel_width = app_rect.width - 8

            if app_tab == "market": # hide graph & chat on weekly tab

                # Top of the lower UI region (under tables)
                lower_top_y = table_top_y + TABLE_HEIGHT + 10

                #GRAPH PANEL
                graph_panel_h = HEADER_H + GRAPH_HEIGHT + 2  # header + graph + a tiny pad
                graph_rect = pygame.Rect(panel_x, lower_top_y, panel_width, graph_panel_h)

                pygame.draw.rect(screen, COLOR_CHAT_BACKGROUND, graph_rect)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, graph_rect, 1)

                graph_header = pygame.Rect(graph_rect.x, graph_rect.y, graph_rect.width, HEADER_H)
                pygame.draw.rect(screen, COLOR_TABLE_HEADER, graph_header)
                graph_label = font_medium.render("Cash Total by Day", True, COLOR_TABLE_HEADER_TEXT)
                screen.blit(
                    graph_label,
                    (graph_header.x + 4, graph_header.y + (HEADER_H - graph_label.get_height()) // 2),
                )

                # graph drawing area (inside graph panel)
                graph_area = pygame.Rect(
                    graph_rect.x + 1,
                    graph_header.bottom,
                    graph_rect.width - 2,
                    graph_rect.height - HEADER_H - 1
                )
                pygame.draw.rect(screen, COLOR_WINDOW, graph_area)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, graph_area, 1)

                # Draw cash history line graph
                if len(cash_history) > 1:
                    min_cash = min(val for _, val in cash_history)
                    max_cash = max(val for _, val in cash_history)
                    if min_cash == max_cash:
                        max_cash += 1

                    total_points = len(cash_history)

                    # padding inside graph
                    px0 = graph_area.x + 28   # leave room for Y labels
                    py0 = graph_area.y + 4
                    gw = graph_area.width - 32
                    gh = graph_area.height - 20  # leave room for X labels

                    # --- Y axis min / max ---
                    min_label = font_small.render(str(int(min_cash)), True, COLOR_GRAPH_LINE)
                    max_label = font_small.render(str(int(max_cash)), True, COLOR_GRAPH_LINE)

                    screen.blit(min_label, (graph_area.x + 2, py0 + gh - min_label.get_height() // 2))
                    screen.blit(max_label, (graph_area.x + 2, py0 - max_label.get_height() // 2))

                    # --- X axis min / max ---
                    min_day = str(cash_history[0][0])
                    max_day = str(cash_history[-1][0])

                    min_day_surf = font_small.render(min_day, True, COLOR_GRAPH_LINE)
                    max_day_surf = font_small.render(max_day, True, COLOR_GRAPH_LINE)

                    screen.blit(min_day_surf, (px0, py0 + gh + 2))
                    screen.blit(max_day_surf, (px0 + gw - max_day_surf.get_width(), py0 + gh + 2))

                    # --- line graph ---
                    prev_point = None
                    for idx, (_, cash_val) in enumerate(cash_history):
                        x_frac = idx / (total_points - 1)
                        y_frac = (cash_val - min_cash) / (max_cash - min_cash)

                        px = int(px0 + gw * x_frac)
                        py = int(py0 + gh * (1 - y_frac))

                        if prev_point:
                            pygame.draw.line(screen, COLOR_GRAPH_LINE, prev_point, (px, py), 2)
                        prev_point = (px, py)

                # CHAT PANEL BELOW graph panel
                chat_y = graph_rect.bottom + PANEL_PAD
                chat_rect = pygame.Rect(panel_x, chat_y, panel_width, CHAT_HEIGHT)

                pygame.draw.rect(screen, COLOR_CHAT_BACKGROUND, chat_rect)
                pygame.draw.rect(screen, COLOR_WINDOW_BORDER_DARK, chat_rect, 1)

                chat_header = pygame.Rect(chat_rect.x, chat_rect.y, chat_rect.width, HEADER_H)
                pygame.draw.rect(screen, COLOR_TABLE_HEADER, chat_header)
                chat_label = font_medium.render("Messages", True, COLOR_TABLE_HEADER_TEXT)
                screen.blit(
                    chat_label,
                    (chat_header.x + 4, chat_header.y + (HEADER_H - chat_label.get_height()) // 2),
                )

                # message area inside chat panel
                msg_area_y = chat_header.bottom + 2
                msg_area_bottom = chat_rect.bottom - (BTN_H + BTN_PAD)  # leave room for bottom button strip
                msg_area_height = max(1, msg_area_bottom - msg_area_y)

                # scroll buttons ONLY for chat (top + bottom inside chat panel)
                chat_up_btn.rect = pygame.Rect(chat_rect.right - (BTN_W + 4), chat_rect.y + BTN_PAD, BTN_W, BTN_H)
                chat_down_btn.rect = pygame.Rect(chat_rect.right - (BTN_W + 4), chat_rect.bottom - (BTN_H + BTN_PAD), BTN_W, BTN_H)
                chat_up_btn.label = "^"
                chat_down_btn.label = "v"
                chat_up_btn.draw(screen, font_small)
                chat_down_btn.draw(screen, font_small)

                # draw visible lines
                lines_visible = max(1, msg_area_height // CHAT_LINE_HEIGHT)
                start_idx = chat_offset
                end_idx = start_idx + lines_visible

                for i, msg in enumerate(chat_messages[start_idx:end_idx]):
                    y_pos = msg_area_y + i * CHAT_LINE_HEIGHT
                    if y_pos + CHAT_LINE_HEIGHT <= msg_area_bottom:
                        msg_surf = font_small.render(msg, True, COLOR_CHAT_TEXT)
                        screen.blit(msg_surf, (chat_rect.x + 4, y_pos))

        # Draw screensaver overlay on top of all UI elements when active.
        if mode != "start":
            ss_manager.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()