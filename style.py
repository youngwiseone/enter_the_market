"""
style.py
---------

This module centralises all of the visual styling and configuration
constants used by the market trading game.  By moving colours,
dimensions and other tunable values into a separate file you can
easily reskin the user interface without touching the core game
logic.  Colours are defined in an easy to read manner and grouped
together for clarity.
"""

from typing import Dict

# Screen dimensions and frame rate
WIDTH, HEIGHT = 1200, 720
FPS = 60

# Starting inventory and capacity settings
DEFAULT_STARTING_CASH = 100
DEFAULT_CAPACITY = 5           # starting storage capacity (units)
CAPACITY_STEP = 1              # change in storage capacity per adjustment

# Price dynamics (may be overridden in market.py)
VOLATILITY = 0.18              # daily price movement magnitude (relative)
SPREAD = 0.90                  # player's sell price = shop buy price * SPREAD
RESTOCK_MIN, RESTOCK_MAX = 0, 8  # new shop stock each day

# Rent is paid weekly (every Sunday). Rent cost equals current storage capacity
# (i.e. $1 per unit of space you can hold).
BILL_INTERVAL = 7

# Retro colour palette (classic Windows 95 greys and blues)
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

# Table layout
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

# Height of the heads‑up display
HUD_HEIGHT = 50

# Height of the application window title bar
TITLE_BAR_HEIGHT = 30

# Height of the cash history graph inside the chat area.  The chat area is
# divided into a graph portion and a command‑line/message portion.  Keep
# GRAPH_HEIGHT relatively small so chat messages still have space.
GRAPH_HEIGHT = 60

# Column widths for tables (sum should fit within table width minus scroll bar)
# Shop columns: image, sku, description, quantity, current price, average buy price,
# input field, button.  Total width must be <= table_panel.width - scroll bar.
SHOP_COL_WIDTHS = [24, 60, 140, 60, 70, 70, 50, 50]

# Inventory columns: image, sku, description, avg cost, quantity, sell price,
# input field, button.
INV_COL_WIDTHS = [24, 60, 140, 60, 70, 70, 60, 50]

# Table headers (separate from the layouts to allow easy renaming)
SHOP_HEADERS = ["Img", "SKU", "Description", "Avg_Price", "Buy_price", "In Stock",  "Qty", ""]
INV_HEADERS = ["Img", "SKU", "Description", "Avg_cost", "Sell_price", "SOH", "Qty", ""]

# ---------------------------------------------------------------------------
# Theme and UI skin configuration
#
# The market game now supports multiple visual themes and UI skins that can
# be unlocked via the Store.  A theme defines a complete palette of colours
# used throughout the UI while a UI skin defines how controls such as
# buttons are drawn (e.g. rounded vs square corners).  The default theme
# replicates the original Windows 95 palette while the "Monochrome Green"
# theme uses a classic green‑on‑black look reminiscent of early CRT
# terminals.  Additional themes or skins can be added here without
# modifying the rest of the code.

# A dictionary of available themes.  Each entry maps to a dictionary of
# colour constants keyed by the name of the constant in this module.  When a
# theme is applied the values in the selected dictionary are copied over
# the existing module globals.  Keys not present in a theme will keep
# whatever value is currently assigned.
THEMES: Dict[str, Dict[str, tuple]] = {
    "Default": {
        "COLOR_DESKTOP": COLOR_DESKTOP,
        "COLOR_WINDOW": COLOR_WINDOW,
        "COLOR_TITLE_BAR": COLOR_TITLE_BAR,
        "COLOR_TITLE_TEXT": COLOR_TITLE_TEXT,
        "COLOR_WINDOW_BORDER_LIGHT": COLOR_WINDOW_BORDER_LIGHT,
        "COLOR_WINDOW_BORDER_DARK": COLOR_WINDOW_BORDER_DARK,
        "COLOR_CONTROL_BACKGROUND": COLOR_CONTROL_BACKGROUND,
        "COLOR_CONTROL_BORDER_LIGHT": COLOR_CONTROL_BORDER_LIGHT,
        "COLOR_CONTROL_BORDER_DARK": COLOR_CONTROL_BORDER_DARK,
        "COLOR_CONTROL_TEXT": COLOR_CONTROL_TEXT,
        "COLOR_TABLE_HEADER": COLOR_TABLE_HEADER,
        "COLOR_TABLE_HEADER_TEXT": COLOR_TABLE_HEADER_TEXT,
        "COLOR_ROW_LIGHT": COLOR_ROW_LIGHT,
        "COLOR_ROW_DARK": COLOR_ROW_DARK,
        "COLOR_GRAPH_BACKGROUND": COLOR_GRAPH_BACKGROUND,
        "COLOR_GRAPH_LINE": COLOR_GRAPH_LINE,
        "COLOR_TOAST": COLOR_TOAST,
        "COLOR_CHAT_BACKGROUND": COLOR_CHAT_BACKGROUND,
        "COLOR_CHAT_TEXT": COLOR_CHAT_TEXT,
    },
    # Monochrome green theme – a retro "green screen" look
    "Monochrome Green": {
        "COLOR_DESKTOP": (0, 0, 0),
        "COLOR_WINDOW": (0, 32, 0),
        "COLOR_TITLE_BAR": (0, 64, 0),
        "COLOR_TITLE_TEXT": (0, 255, 0),
        "COLOR_WINDOW_BORDER_LIGHT": (0, 128, 0),
        "COLOR_WINDOW_BORDER_DARK": (0, 96, 0),
        "COLOR_CONTROL_BACKGROUND": (0, 48, 0),
        "COLOR_CONTROL_BORDER_LIGHT": (0, 96, 0),
        "COLOR_CONTROL_BORDER_DARK": (0, 64, 0),
        "COLOR_CONTROL_TEXT": (0, 255, 0),
        "COLOR_TABLE_HEADER": (0, 64, 0),
        "COLOR_TABLE_HEADER_TEXT": (0, 255, 0),
        "COLOR_ROW_LIGHT": (0, 40, 0),
        "COLOR_ROW_DARK": (0, 24, 0),
        "COLOR_GRAPH_BACKGROUND": (0, 24, 0),
        "COLOR_GRAPH_LINE": (0, 200, 0),
        "COLOR_TOAST": (0, 200, 0),
        "COLOR_CHAT_BACKGROUND": (0, 0, 0),
        "COLOR_CHAT_TEXT": (0, 255, 0),
    },
    # Aquatic Blue – deep blues and turquoise hues
    "Aquatic Blue": {
        "COLOR_DESKTOP": (20, 40, 60),
        "COLOR_WINDOW": (30, 90, 110),
        "COLOR_TITLE_BAR": (10, 20, 80),
        "COLOR_TITLE_TEXT": (200, 240, 255),
        "COLOR_WINDOW_BORDER_LIGHT": (80, 140, 160),
        "COLOR_WINDOW_BORDER_DARK": (10, 30, 50),
        "COLOR_CONTROL_BACKGROUND": (60, 110, 130),
        "COLOR_CONTROL_BORDER_LIGHT": (100, 160, 180),
        "COLOR_CONTROL_BORDER_DARK": (20, 50, 70),
        "COLOR_CONTROL_TEXT": (220, 240, 255),
        "COLOR_TABLE_HEADER": (0, 60, 80),
        "COLOR_TABLE_HEADER_TEXT": (220, 240, 255),
        "COLOR_ROW_LIGHT": (45, 80, 100),
        "COLOR_ROW_DARK": (35, 70, 90),
        "COLOR_GRAPH_BACKGROUND": (30, 70, 90),
        "COLOR_GRAPH_LINE": (200, 220, 255),
        "COLOR_TOAST": (180, 80, 90),
        "COLOR_CHAT_BACKGROUND": (10, 20, 30),
        "COLOR_CHAT_TEXT": (150, 220, 255),
    },
    # Flame Vixen – rich purples and fiery oranges
    "Flame Vixen": {
        "COLOR_DESKTOP": (50, 20, 40),
        "COLOR_WINDOW": (90, 40, 60),
        "COLOR_TITLE_BAR": (120, 30, 100),
        "COLOR_TITLE_TEXT": (255, 220, 200),
        "COLOR_WINDOW_BORDER_LIGHT": (160, 80, 140),
        "COLOR_WINDOW_BORDER_DARK": (70, 20, 60),
        "COLOR_CONTROL_BACKGROUND": (110, 50, 80),
        "COLOR_CONTROL_BORDER_LIGHT": (180, 90, 160),
        "COLOR_CONTROL_BORDER_DARK": (60, 20, 40),
        "COLOR_CONTROL_TEXT": (255, 230, 210),
        "COLOR_TABLE_HEADER": (255, 180, 0),
        "COLOR_TABLE_HEADER_TEXT": (255, 230, 210),
        "COLOR_ROW_LIGHT": (100, 40, 70),
        "COLOR_ROW_DARK": (80, 30, 60),
        "COLOR_GRAPH_BACKGROUND": (70, 30, 50),
        "COLOR_GRAPH_LINE": (255, 150, 100),
        "COLOR_TOAST": (200, 60, 40),
        "COLOR_CHAT_BACKGROUND": (20, 10, 30),
        "COLOR_CHAT_TEXT": (255, 200, 180),
    },
    # Coder Black – high‑contrast black and white scheme
    "Coder Black": {
        "COLOR_DESKTOP": (0, 0, 0),
        "COLOR_WINDOW": (15, 15, 15),
        "COLOR_TITLE_BAR": (30, 30, 30),
        "COLOR_TITLE_TEXT": (255, 255, 255),
        "COLOR_WINDOW_BORDER_LIGHT": (60, 60, 60),
        "COLOR_WINDOW_BORDER_DARK": (5, 5, 5),
        "COLOR_CONTROL_BACKGROUND": (25, 25, 25),
        "COLOR_CONTROL_BORDER_LIGHT": (70, 70, 70),
        "COLOR_CONTROL_BORDER_DARK": (10, 10, 10),
        "COLOR_CONTROL_TEXT": (255, 255, 255),
        "COLOR_TABLE_HEADER": (40, 40, 40),
        "COLOR_TABLE_HEADER_TEXT": (255, 255, 255),
        "COLOR_ROW_LIGHT": (20, 20, 20),
        "COLOR_ROW_DARK": (10, 10, 10),
        "COLOR_GRAPH_BACKGROUND": (0, 0, 0),
        "COLOR_GRAPH_LINE": (200, 200, 200),
        "COLOR_TOAST": (220, 80, 80),
        "COLOR_CHAT_BACKGROUND": (0, 0, 0),
        "COLOR_CHAT_TEXT": (0, 255, 0),
    },
    # Hotdog Stand – vibrant red and yellow throwback
    "Hotdog Stand": {
        "COLOR_DESKTOP": (255, 0, 0),
        "COLOR_WINDOW": (255, 255, 0),
        "COLOR_TITLE_BAR": (0, 0, 0),
        "COLOR_TITLE_TEXT": (255, 255, 0),
        "COLOR_WINDOW_BORDER_LIGHT": (255, 255, 0),
        "COLOR_WINDOW_BORDER_DARK": (128, 0, 0),
        "COLOR_CONTROL_BACKGROUND": (255, 255, 0),
        "COLOR_CONTROL_BORDER_LIGHT": (255, 255, 0),
        "COLOR_CONTROL_BORDER_DARK": (128, 0, 0),
        "COLOR_CONTROL_TEXT": (0, 0, 0),
        "COLOR_TABLE_HEADER": (128, 0, 0),
        "COLOR_TABLE_HEADER_TEXT": (255, 255, 0),
        "COLOR_ROW_LIGHT": (255, 200, 0),
        "COLOR_ROW_DARK": (255, 180, 0),
        "COLOR_GRAPH_BACKGROUND": (255, 255, 0),
        "COLOR_GRAPH_LINE": (0, 0, 0),
        "COLOR_TOAST": (255, 0, 0),
        "COLOR_CHAT_BACKGROUND": (255, 0, 0),
        "COLOR_CHAT_TEXT": (255, 255, 0),
    },
    # Teal Breeze – mellow teal with soft highlights
    "Teal Breeze": {
        "COLOR_DESKTOP": (0, 96, 96),
        "COLOR_WINDOW": (96, 128, 128),
        "COLOR_TITLE_BAR": (0, 64, 64),
        "COLOR_TITLE_TEXT": (240, 240, 240),
        "COLOR_WINDOW_BORDER_LIGHT": (128, 192, 192),
        "COLOR_WINDOW_BORDER_DARK": (0, 48, 48),
        "COLOR_CONTROL_BACKGROUND": (112, 144, 144),
        "COLOR_CONTROL_BORDER_LIGHT": (160, 200, 200),
        "COLOR_CONTROL_BORDER_DARK": (0, 64, 64),
        "COLOR_CONTROL_TEXT": (240, 240, 240),
        "COLOR_TABLE_HEADER": (0, 80, 80),
        "COLOR_TABLE_HEADER_TEXT": (240, 240, 240),
        "COLOR_ROW_LIGHT": (80, 112, 112),
        "COLOR_ROW_DARK": (64, 96, 96),
        "COLOR_GRAPH_BACKGROUND": (48, 80, 80),
        "COLOR_GRAPH_LINE": (200, 220, 220),
        "COLOR_TOAST": (200, 80, 80),
        "COLOR_CHAT_BACKGROUND": (0, 64, 64),
        "COLOR_CHAT_TEXT": (200, 240, 240),
    },
}

# A dictionary of available UI skins.  Each skin may define properties that
# affect how widgets are drawn.  Currently only the border radius for
# controls (e.g. RetroButton) is supported.  Additional properties can be
# added in the future.
UI_SKINS = {
    "Classic": {
        "border_radius": 0,
    },
    "Rounded": {
        "border_radius": 4,
    },
}

# Holds the current theme and UI skin names.  These can be changed at
# runtime via apply_theme() and apply_ui_skin() and are persisted to
# player.csv when the user purchases a theme or skin.
CURRENT_THEME = "Default"
CURRENT_UI_SKIN = "Classic"

# The active border radius for controls.  This is updated when the UI skin
# changes.  Default to 0 (square corners) to match the original style.
UI_BORDER_RADIUS = UI_SKINS[CURRENT_UI_SKIN]["border_radius"]

def apply_theme(name: str) -> None:
    """
    Apply the specified theme by copying all defined colour values into this
    module's global namespace.  Unknown names are ignored.
    """
    global CURRENT_THEME
    if name not in THEMES:
        return
    theme = THEMES[name]
    for const, value in theme.items():
        if const in globals():
            globals()[const] = value
    CURRENT_THEME = name

def apply_ui_skin(name: str) -> None:
    """
    Apply the specified UI skin by updating the border radius.  Unknown names
    fallback to the default skin.
    """
    global CURRENT_UI_SKIN, UI_BORDER_RADIUS
    if name not in UI_SKINS:
        name = "Classic"
    CURRENT_UI_SKIN = name
    UI_BORDER_RADIUS = UI_SKINS[name].get("border_radius", 0)

# Expose everything via __all__ for wildcard imports
__all__ = [
    'WIDTH', 'HEIGHT', 'FPS',
    'DEFAULT_STARTING_CASH', 'DEFAULT_CAPACITY', 'CAPACITY_STEP',
    'VOLATILITY', 'SPREAD', 'RESTOCK_MIN', 'RESTOCK_MAX',
    'BILL_INTERVAL',
    'COLOR_DESKTOP', 'COLOR_WINDOW', 'COLOR_TITLE_BAR', 'COLOR_TITLE_TEXT',
    'COLOR_WINDOW_BORDER_LIGHT', 'COLOR_WINDOW_BORDER_DARK',
    'COLOR_CONTROL_BACKGROUND', 'COLOR_CONTROL_BORDER_LIGHT', 'COLOR_CONTROL_BORDER_DARK',
    'COLOR_CONTROL_TEXT', 'COLOR_TABLE_HEADER', 'COLOR_TABLE_HEADER_TEXT',
    'COLOR_ROW_LIGHT', 'COLOR_ROW_DARK', 'COLOR_GRAPH_BACKGROUND', 'COLOR_GRAPH_LINE',
    'COLOR_TOAST', 'COLOR_CHAT_BACKGROUND', 'COLOR_CHAT_TEXT', 'CHAT_LINE_HEIGHT',
    'MARGIN', 'SPACING', 'TABLE_WIDTH', 'TABLE_HEIGHT', 'REPORT_HEIGHT',
    'HEADER_HEIGHT', 'SCROLL_BUTTON_HEIGHT', 'ROW_HEIGHT', 'VISIBLE_ROWS',
    'CHAT_HEIGHT', 'HUD_HEIGHT', 'TITLE_BAR_HEIGHT', 'GRAPH_HEIGHT',
    'SHOP_COL_WIDTHS', 'INV_COL_WIDTHS', 'SHOP_HEADERS', 'INV_HEADERS'
    ,'THEMES','UI_SKINS','CURRENT_THEME','CURRENT_UI_SKIN','UI_BORDER_RADIUS'
    ,'apply_theme','apply_ui_skin'
]