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
]