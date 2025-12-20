import os
import csv
import random
from datetime import datetime

import pygame

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
# The default number of item slots the player starts with.  In this game we
# treat storage space as an ongoing subscription rather than a one‑time
# purchase – the rent you pay at the end of each week is equal to the
# capacity you have.  Starting capacity is intentionally small so that
# players feel pressure to upgrade only when necessary.
DEFAULT_CAPACITY = 5           # how many total units the player can hold

# When changing storage on Sundays the capacity will be adjusted by this
# amount per click.  A smaller step makes incremental upgrades feel fair
# and aligns with the weekly rent schedule.
CAPACITY_STEP = 5             # storage change increment

# Price dynamics
VOLATILITY = 0.18              # daily price movement magnitude (relative)
SPREAD = 0.90                  # player's sell price = shop buy price * SPREAD
RESTOCK_MIN, RESTOCK_MAX = 0, 8  # new shop stock each day

# Rent is collected weekly rather than monthly.  Every BILL_INTERVAL days
# (with the game starting on a Monday), you must pay an amount equal to
# your current capacity.  For example, if you have 8 storage slots when
# rent is due, you will pay $8.
BILL_INTERVAL = 7
# BILL_BASE is unused in the weekly rent model but retained for backwards
# compatibility.  It has no effect on gameplay when rent is computed as
# capacity.
BILL_BASE = 0

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

# Human‑friendly names for days of the week.  The game always starts on
# Monday (day 1) and increments the day counter from there.  These names
# are used in the HUD to display the current weekday alongside the day
# number.
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Chat formatting
CHAT_LINE_HEIGHT = 16  # pixel height per chat line

# Layout constants
MARGIN = 20
SPACING = 10
TABLE_WIDTH = (WIDTH - 2 * MARGIN - SPACING) // 2
TABLE_HEIGHT = 300
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
SHOP_COL_WIDTHS = [26, 60, 140, 70, 70, 70, 50, 50]
# Inventory columns: image, sku, description, avg cost, quantity, sell price,
# input field, button.
INV_COL_WIDTHS = [26, 60, 140, 70, 80, 80, 30, 30]
#SHOP_HEADERS = ["Img", "SKU", "Description", "In Stock", "Price", "Avg_Price", "Qty", ""]
SHOP_HEADERS = ["Img", "SKU", "Description", "Avg_Price", "Buy_price", "In Stock",  "Qty", ""]
INV_HEADERS = ["Img", "SKU", "Description", "Avg_cost", "Sell_price", "SOH", "Qty", ""]

# CSV file paths
ITEMS_CSV = os.path.join(DATA_DIR, "items.csv")
SHOP_CSV = os.path.join(DATA_DIR, "shop.csv")
INV_CSV = os.path.join(DATA_DIR, "inventory.csv")
TXN_CSV = os.path.join(DATA_DIR, "transactions.csv")
PLAYER_CSV = os.path.join(DATA_DIR, "player.csv")

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
    starter = [
        {"sku":"A100","description":"Iron Ingot","image":"iron.png","price":"10"},
        {"sku":"A110","description":"Copper Wire","image":"copper.png","price":"8"},
        {"sku":"A120","description":"Wood Plank","image":"wood.png","price":"5"},
        {"sku":"A130","description":"Health Potion","image":"potion.png","price":"15"},
        {"sku":"A140","description":"Leather Roll","image":"leather.png","price":"12"},
        {"sku":"A150","description":"Crystal Shard","image":"crystal.png","price":"22"},
        {"sku":"A160","description":"Coal Lump","image":"coal.png","price":"6"},
        {"sku":"A170","description":"Glass Bottle","image":"bottle.png","price":"7"},
        {"sku":"A180","description":"Gear Wheel","image":"gear.png","price":"18"},
        {"sku":"A190","description":"Cloth Bundle","image":"cloth.png","price":"9"},
        {"sku":"A200","description":"Silver Nugget","image":"silver.png","price":"28"},
        {"sku":"A210","description":"Magic Ink","image":"ink.png","price":"25"},
        {"sku":"A220","description":"Spice Pouch","image":"spice.png","price":"14"},
        {"sku":"A230","description":"Stone Brick","image":"stone.png","price":"4"},
    ]
    write_csv_dicts(ITEMS_CSV, ["sku","description","image","price"], starter)


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
        items[r["sku"]] = {
            "sku": r["sku"],
            "description": r.get("description",""),
            "image": r.get("image",""),
            "base_price": base_price,
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


def init_player_if_missing(starting_cash=DEFAULT_STARTING_CASH):
    """Create a default player.csv if missing."""
    if os.path.exists(PLAYER_CSV):
        return
    write_csv_dicts(
        PLAYER_CSV,
        ["cash","capacity","day"],
        [{"cash": f"{starting_cash:.2f}", "capacity": str(DEFAULT_CAPACITY), "day": "1"}]
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
    }


def save_player(player):
    """Persist player state to player.csv."""
    write_csv_dicts(
        PLAYER_CSV, ["cash","capacity","day"],
        [{"cash": f"{player['cash']:.2f}", "capacity": str(player["capacity"]), "day": str(player["day"])}]
    )


TXN_FIELDS = ["timestamp","day","sku","action","qty","unit_price","total","cash_after"]


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

    # Every BILL_INTERVAL days (i.e. at the end of each week), deduct rent
    # from cash.  Rent is equal to the player's current capacity.  Note that
    # player["day"] starts at 1 (Monday), so a week ends whenever
    # player["day"] % BILL_INTERVAL == 0 (Sunday).
    if player["day"] % BILL_INTERVAL == 0:
        cost = player["capacity"]
        player["cash"] -= cost
        # Log as a rent transaction; use SKU "" to denote non‑item
        log_txn(player["day"], "", "RENT", 1, cost, cost, player["cash"])
        return f"Paid rent: ${cost}"
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
        # fill background
        pygame.draw.rect(surf, COLOR_CONTROL_BACKGROUND, self.rect)
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
    font_small = pygame.font.Font(None, 20)
    font_medium = pygame.font.Font(None, 22)
    font_large = pygame.font.Font(None, 28)
    font_title = pygame.font.Font(None, 24)

    # Load base data
    items = load_items()
    init_shop_from_items(items)
    init_inventory_if_missing()

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
    buy_space_btn = None
    # Buttons for adjusting storage capacity (displayed on Sundays)
    inc_space_btn = None
    dec_space_btn = None
    # Chat scroll buttons
    chat_up_btn = None
    chat_down_btn = None

    toast = ""
    toast_timer = 0

    mode = "start"

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

    # Functions for day advance and capacity purchase
    def purchase_space():
        """
        Deprecated: storage space is no longer purchased with a one‑time cost.
        Storage capacity is now adjusted weekly on Sundays, and rent is
        proportional to capacity.  This function is kept for backward
        compatibility but will simply inform the player that space must be
        changed on Sundays.
        """
        set_toast("Storage changes can only be made on Sundays via the Increase/Decrease buttons.")

    # Track the last day on which the player changed their storage.  This
    # ensures players can only modify storage once per week.  Initialise to
    # zero (no changes made yet).
    last_space_change_day = 0

    def increase_space():
        """Increase the player's capacity by CAPACITY_STEP on a Sunday."""
        nonlocal last_space_change_day
        # Only allow changes on Sunday (end of week)
        if player['day'] % BILL_INTERVAL != 0:
            set_toast("You can only change storage on Sundays.")
            return
        # Prevent multiple changes on the same Sunday
        if last_space_change_day == player['day']:
            set_toast("You have already changed storage this Sunday.")
            return
        # Apply the increase
        player['capacity'] += CAPACITY_STEP
        last_space_change_day = player['day']
        save_player(player)
        set_toast(f"Increased storage to {player['capacity']} slots")

    def decrease_space():
        """Decrease the player's capacity by CAPACITY_STEP on a Sunday."""
        nonlocal last_space_change_day
        # Only allow changes on Sunday (end of week)
        if player['day'] % BILL_INTERVAL != 0:
            set_toast("You can only change storage on Sundays.")
            return
        # Prevent multiple changes on the same Sunday
        if last_space_change_day == player['day']:
            set_toast("You have already changed storage this Sunday.")
            return
        # Ensure there is room to decrease without losing items
        used = inv_used_units(inv)
        if player['capacity'] - CAPACITY_STEP < used:
            set_toast("Cannot decrease below current used storage.")
            return
        if player['capacity'] - CAPACITY_STEP < 1:
            set_toast("Cannot decrease below 1.")
            return
        player['capacity'] -= CAPACITY_STEP
        last_space_change_day = player['day']
        save_player(player)
        set_toast(f"Decreased storage to {player['capacity']} slots")

    def advance_day():
        """Advance the day, update prices and averages, pay bills and generate tips."""
        # progress the game day and handle bills
        bill_msg = next_day(items, shop, player)
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
            best_buy = min(buy_candidates, key=lambda x: x[1] / x[2])
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
            best_sell = max(sell_candidates, key=lambda x: x[1] / x[2])
            sku, sp, cost = best_sell
            tips.append(f"Tip: SELL {sku} – sell ${sp:.2f} > cost ${cost:.2f}")
        # Facts about rent due and cash.  Rent is due every BILL_INTERVAL days
        # (i.e. weekly) and is equal to your current capacity.  Compute the
        # number of days until the next rent day by taking the modulus of
        # the current day.  When days_until is zero, rent is due today.
        rem = player['day'] % BILL_INTERVAL
        days_until = (BILL_INTERVAL - rem) % BILL_INTERVAL
        next_rent = player['capacity']
        if days_until == 0:
            facts.append(f"Rent (${next_rent}) is due today.")
        else:
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
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if mode == "start":
                # Start screen events
                start_input.handle_event(event)
                if start_button:
                    start_button.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # clicking start button handled above
                    pass
            else:
                # Market mode events
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
                # chat scroll buttons
                chat_up_btn.handle_event(event)
                chat_down_btn.handle_event(event)
                next_day_btn.handle_event(event)
                # storage change buttons handle their own restrictions
                inc_space_btn.handle_event(event)
                dec_space_btn.handle_event(event)
                buy_space_btn.handle_event(event)

        # update hover states for buttons
        if mode != "start":
            for btn in shop_buttons + inv_buttons:
                btn.update()
            up_shop_btn.update()
            down_shop_btn.update()
            up_inv_btn.update()
            down_inv_btn.update()
            # update chat scroll buttons
            chat_up_btn.update()
            chat_down_btn.update()
            next_day_btn.update()
            inc_space_btn.update()
            dec_space_btn.update()
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
                    nonlocal next_day_btn, buy_space_btn, up_shop_btn, down_shop_btn, up_inv_btn, down_inv_btn
                    nonlocal chat_messages, chat_offset, avg_buy_prices, chat_up_btn, chat_down_btn
                    nonlocal inc_space_btn, dec_space_btn
                    try:
                        starting_cash = start_input.value_int()
                    except Exception:
                        starting_cash = DEFAULT_STARTING_CASH
                    if starting_cash <= 0:
                        set_toast("Starting cash must be > 0")
                        return
                    # reset files for new game
                    for p in [SHOP_CSV, INV_CSV, PLAYER_CSV, TXN_CSV]:
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
                    # create scroll buttons and action buttons
                    # positions depend on layout, will update during draw
                    next_day_btn = RetroButton(pygame.Rect(0,0,100,30), "Next Day", advance_day)
                    # Buttons to adjust storage capacity on Sundays.  They use
                    # the increase_space and decrease_space callbacks defined
                    # earlier.  These buttons will be positioned in the HUD
                    # during drawing.
                    inc_space_btn = RetroButton(pygame.Rect(0,0,100,30), "Increase", increase_space)
                    dec_space_btn = RetroButton(pygame.Rect(0,0,100,30), "Decrease", decrease_space)
                    # Retain buy_space_btn for backward compatibility but keep it hidden.
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
                    # switch to market mode
                    nonlocal mode
                    mode = "market"
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
            # Draw HUD text
            # Compute the day of the week based on the game's calendar.  The first
            # day (1) is Monday, so subtract 1 before modulo.  Use the
            # predefined DAY_NAMES list to look up the name.
            dow = (player['day'] - 1) % BILL_INTERVAL
            day_label = f"Day {player['day']}, {DAY_NAMES[dow]}"
            day_surf = font_medium.render(day_label, True, COLOR_CONTROL_TEXT)
            cash_surf = font_medium.render(f"Cash: ${player['cash']:.2f}", True, COLOR_CONTROL_TEXT)
            storage_surf = font_medium.render(f"Storage: {inv_used_units(inv)}/{player['capacity']}", True, COLOR_CONTROL_TEXT)
            net_worth = player["cash"] + sum((shop[sku]["buy_price"]*SPREAD) * inv[sku]["qty"] for sku in inv.keys())
            net_surf = font_medium.render(f"Net Worth: ${net_worth:.2f}", True, COLOR_CONTROL_TEXT)
            screen.blit(day_surf, (hud_rect.x + 8, hud_rect.y + 6))
            screen.blit(cash_surf, (hud_rect.x + 8, hud_rect.y + 28))
            screen.blit(storage_surf, (hud_rect.x + 180, hud_rect.y + 6))
            screen.blit(net_surf, (hud_rect.x + 180, hud_rect.y + 28))
            # Position action buttons next to HUD.  The "Next Day" button
            # sits on the top row.  Below it are the Increase/Decrease
            # storage buttons.  These buttons will operate only on Sundays.
            next_day_btn.rect.topleft = (hud_rect.right - 220, hud_rect.y + 4)
            inc_space_btn.rect.topleft = (hud_rect.right - 220, hud_rect.y + 28)
            dec_space_btn.rect.topleft = (hud_rect.right - 110, hud_rect.y + 28)
            # Draw the buttons
            next_day_btn.draw(screen, font_small)
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

            PANEL_PAD = 6
            HEADER_H = 20
            BTN_H = 16
            BTN_W = 20
            BTN_PAD = 2

            panel_x = app_rect.x + 4
            panel_width = app_rect.width - 8

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

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()