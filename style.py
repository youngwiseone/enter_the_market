"""UI theme + layout constants for Enter The Market.

Change colours and sizing here to re-skin the whole UI without touching gameplay code.
All values are plain constants so you can tweak quickly.
"""

# -------------------------------------------------------------
# Window + timing
# -------------------------------------------------------------
WIDTH, HEIGHT = 1200, 720
FPS = 60

# -------------------------------------------------------------
# Fonts (pygame.font.Font(None, size))
# -------------------------------------------------------------
FONT_SMALL_SIZE = 16
FONT_MEDIUM_SIZE = 20
FONT_LARGE_SIZE = 28
FONT_TITLE_SIZE = 24

# -------------------------------------------------------------
# Colours (Win95-ish)
# -------------------------------------------------------------
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

# Terminal/chat area styling
COLOR_CHAT_BACKGROUND = (0, 0, 0)
COLOR_CHAT_TEXT = (0, 255, 0)

# -------------------------------------------------------------
# Layout
# -------------------------------------------------------------
MARGIN = 20
SPACING = 10

TABLE_WIDTH = (WIDTH - 2 * MARGIN - SPACING * 2) // 2
TABLE_HEIGHT = 300
REPORT_HEIGHT = 500

HEADER_HEIGHT = 30
SCROLL_BUTTON_HEIGHT = 20
ROW_HEIGHT = 26

# The number of rows visible in each table before scrolling.
# We reserve space for a column header row (20px) in addition to the coloured
# header bar and scroll buttons.
VISIBLE_ROWS = (TABLE_HEIGHT - HEADER_HEIGHT - 20 - 2 * SCROLL_BUTTON_HEIGHT) // ROW_HEIGHT

# Chat area beneath the tables
CHAT_HEIGHT = 150

# Height of the cash history graph inside the chat area (the rest is messages)
GRAPH_HEIGHT = 60

# -------------------------------------------------------------
# Table columns + headers
# (Ensure widths fit within TABLE_WIDTH minus scrollbar.)
# -------------------------------------------------------------
SHOP_COL_WIDTHS = [24, 60, 140, 60, 70, 70, 50, 50]
INV_COL_WIDTHS  = [24, 60, 140, 60, 70, 70, 60, 50]

SHOP_HEADERS = ["Img", "SKU", "Description", "Avg_Price", "Buy_price", "In Stock", "Qty", ""]
INV_HEADERS  = ["Img", "SKU", "Description", "Avg_cost", "Sell_price", "SOH", "Qty", ""]
