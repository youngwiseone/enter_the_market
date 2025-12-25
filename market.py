"""
market.py
---------

This module encapsulates the dynamic pricing logic and news system for the
inventory trading game.  It handles daily price movements, weekly rent
deductions, periodic news generation and the application of news events
to item prices.  All file operations (CSV reads/writes) are performed
here so the main UI code remains focused on rendering and user
interaction.

Functions in this module are intentionally stateless; they operate on
mutable dictionaries supplied by the caller (for example the `shop` and
`player` dictionaries) and persist news events to CSV files.
"""

import os
import csv
import random
from typing import List, Dict, Tuple

import style

# Derive configuration values from the shared style module.  These values
# drive the daily price volatility, spread and restock behaviour.  If
# you'd like to change how prices fluctuate or how often new stock
# arrives, modify these values in style.py rather than here.
VOLATILITY = style.VOLATILITY
RESTOCK_MIN, RESTOCK_MAX = style.RESTOCK_MIN, style.RESTOCK_MAX
BILL_INTERVAL = style.BILL_INTERVAL
SPREAD = style.SPREAD

# CSV helper functions (copied from the main module to avoid circular
# dependencies)

def ensure_dir(path: str) -> None:
    """Ensure that a directory exists."""
    if path:
        os.makedirs(path, exist_ok=True)


def read_csv_dicts(path: str) -> List[Dict[str, str]]:
    """Read a CSV into a list of dictionaries.  Missing files yield an empty list."""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv_dicts(path: str, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    """Write a list of dictionaries to a CSV with given field names."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def append_csv_row(path: str, fieldnames: List[str], row: Dict[str, str]) -> None:
    """Append a single row to a CSV, writing the header if missing."""
    ensure_dir(os.path.dirname(path))
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


# News system helpers

def week_number(day: int) -> int:
    """Return a 1‑based week number for a given 1‑based day counter."""
    return ((day - 1) // BILL_INTERVAL) + 1


def init_previous_news_if_missing(prev_csv_path: str) -> None:
    """
    Ensure that the previous news CSV exists with the proper header.  If the
    file does not exist an empty file with the correct header will be
    created.  This function does not overwrite existing data.
    """
    if not os.path.exists(prev_csv_path):
        write_csv_dicts(prev_csv_path, ["day", "sku", "headline", "article", "impact", "duration"], [])


def reset_previous_news(prev_csv_path: str) -> None:
    """Clear all persisted news history and write a fresh header."""
    write_csv_dicts(prev_csv_path, ["day", "sku", "headline", "article", "impact", "duration"], [])


def generate_news(day: int, items: Dict[str, Dict[str, str]], news_csv_path: str, prev_news_csv_path: str) -> List[Dict[str, str]]:
    """
    Generate 1–3 news events for random SKUs.  Each news item is pulled from
    news_csv_path which must contain columns `headline`, `article`,
    `impact` and `duration`.  The placeholder word "sku" in the headline
    and article will be replaced with the item's description.  Newly
    generated events are persisted to prev_news_csv_path with the
    following fields: day, sku, headline, article, impact, duration.

    Returns a list of the newly created event dictionaries.
    """
    rows = read_csv_dicts(news_csv_path)
    if not rows:
        return []
    available_skus = list(items.keys())
    if not available_skus:
        return []
    n = random.randint(1, min(3, len(available_skus)))
    selected_skus = random.sample(available_skus, k=n)
    random.shuffle(rows)
    events = []
    for i, sku in enumerate(selected_skus):
        row = rows[i % len(rows)]
        item_desc = items[sku].get("description", sku)
        # Replace occurrences of 'sku' (case insensitive) with the item description
        head = row.get("headline", "").replace("SKU", item_desc).replace("sku", item_desc)
        art = row.get("article", "").replace("SKU", item_desc).replace("sku", item_desc)
        try:
            impact = float(row.get("impact", "0") or 0)
        except Exception:
            impact = 0.0
        try:
            duration = int(float(row.get("duration", "1") or 1))
        except Exception:
            duration = 1
        ev = {
            "day": str(day),
            "sku": sku,
            "headline": head,
            "article": art,
            "impact": f"{impact}",
            "duration": str(duration),
        }
        events.append(ev)
        append_csv_row(prev_news_csv_path, ["day", "sku", "headline", "article", "impact", "duration"], ev)
    return events


def load_previous_news(prev_news_csv_path: str) -> List[Dict[str, str]]:
    """Load all previously generated news events from a CSV."""
    return read_csv_dicts(prev_news_csv_path)


def get_active_news(day: int, prev_news_csv_path: str) -> List[Dict[str, str]]:
    """
    Return a list of news events still in effect on the given day.  An
    event is active if the difference between the current day and the day
    the news was generated is less than the event's duration.
    """
    events = []
    rows = load_previous_news(prev_news_csv_path)
    for r in rows:
        try:
            ev_day = int(float(r.get("day", 0) or 0))
            duration = int(float(r.get("duration", 0) or 0))
        except Exception:
            continue
        if day - ev_day < duration:
            events.append(r)
    return events


def apply_news_to_shop(shop: Dict[str, Dict[str, float]], active_events: List[Dict[str, str]]) -> None:
    """
    Apply active news impacts to the shop prices.  For each event the
    shop's buy price for the affected SKU is increased or decreased by
    the event's impact.  Prices will never drop below 1.0.  Multiple
    events on the same SKU are additive.
    """
    for ev in active_events:
        sku = ev.get("sku")
        if not sku or sku not in shop:
            continue
        try:
            impact = float(ev.get("impact", 0) or 0)
        except Exception:
            impact = 0.0
        new_price = shop[sku]["buy_price"] + impact
        shop[sku]["buy_price"] = new_price if new_price > 1.0 else 1.0


def get_news_weeks(prev_news_csv_path: str) -> List[int]:
    """Return a sorted list of week numbers for which news events exist."""
    rows = load_previous_news(prev_news_csv_path)
    weeks: List[int] = []
    for r in rows:
        try:
            d = int(float(r.get("day", 0) or 0))
        except Exception:
            continue
        w = week_number(d)
        if w not in weeks:
            weeks.append(w)
    weeks.sort()
    return weeks


def get_news_for_week(week: int, prev_news_csv_path: str) -> List[Dict[str, str]]:
    """
    Retrieve all news events belonging to the specified week number.  The
    week number is 1‑based and corresponds to the game week as returned
    by `week_number`.
    """
    rows = load_previous_news(prev_news_csv_path)
    events = []
    for r in rows:
        try:
            d = int(float(r.get("day", 0) or 0))
        except Exception:
            continue
        if week_number(d) == week:
            events.append(r)
    return events


def next_day(items: Dict[str, Dict[str, float]], shop: Dict[str, Dict[str, float]], player: Dict[str, float],
             news_csv_path: str, prev_news_csv_path: str) -> Tuple[List[str], float, List[Dict[str, str]]]:
    """
    Advance the game by one day.  Prices move towards their base values
    with random volatility, new stock arrives and periodic rent is
    deducted.  On Fridays new news items are generated.  Active news
    events are applied to prices after the daily price update.  The
    player's `day` field is incremented and their cash is reduced by
    rent on Sundays.  This function returns a tuple consisting of a
    list of message strings, the rent charged (or 0 if none) and a
    list of newly generated news events.
    """
    messages: List[str] = []
    day_before = int(player.get("day", 0) or 0)
    # Update prices toward base and random shock
    for sku, s in shop.items():
        base = items[sku]["base_price"]
        current = s["buy_price"]
        toward_base = (base - current) * 0.15
        shock = current * random.uniform(-VOLATILITY, VOLATILITY)
        new_price = current + toward_base + shock
        s["buy_price"] = new_price if new_price > 1.0 else 1.0
        # restock
        s["qty"] += random.randint(RESTOCK_MIN, RESTOCK_MAX)
    # Advance day
    player["day"] = day_before + 1
    day = player["day"]
    # Deduct rent every Sunday (7th day)
    rent_due = 0.0
    if day % BILL_INTERVAL == 0:
        rent_due = float(player.get("capacity", 0) or 0)
        player["cash"] -= rent_due
        messages.append(f"Paid rent: ${rent_due:.0f}")
    # Generate news on Fridays.  Day 1 is Monday, so Friday is day % 7 == 5
    dow = (day - 1) % BILL_INTERVAL  # Monday=0, ..., Sunday=6
    new_events: List[Dict[str, str]] = []
    if dow == 4:  # Friday
        new_events = generate_news(day, items, news_csv_path, prev_news_csv_path)
        if new_events:
            messages.append("Market news released! Check the News tab.")
    # Apply all active news events to prices
    active_events = get_active_news(day, prev_news_csv_path)
    apply_news_to_shop(shop, active_events)
    return messages, rent_due, new_events