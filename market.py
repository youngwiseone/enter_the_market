"""market.py
Market/pricing logic for the Inventory Stock Manager.

Goal: keep *all* pricing behaviour in one place so you can iterate on it without
touching UI, persistence, or gameplay wiring.

The main game file should call:
- next_day(...) to advance and reprice/restock
- sell_price(...) wherever it needs the player's sell price
- build_daily_chat_message(...) to generate the "Tip/Facts" chat line
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, Callable, Optional, Tuple


@dataclass(frozen=True)
class MarketConfig:
    # Price movement
    volatility: float = 0.18           # daily price movement magnitude (relative)
    mean_reversion: float = 0.15       # pull towards base price each day (0..1)

    # Inventory economics
    spread: float = 0.90               # player's sell price = shop buy price * spread

    # Restock
    restock_min: int = 0
    restock_max: int = 8

    # Tip thresholds
    buy_tip_threshold: float = 0.95    # current < avg * threshold => buy tip
    sell_tip_threshold: float = 1.05   # sell_price > avg_cost * threshold => sell tip


DEFAULT_CONFIG = MarketConfig()


def sell_price(shop_buy_price: float, cfg: MarketConfig = DEFAULT_CONFIG) -> float:
    """Player sell price derived from the shop's buy price."""
    return float(shop_buy_price) * float(cfg.spread)


def update_shop_prices_and_stock(
    items: Dict[str, Dict],
    shop: Dict[str, Dict],
    cfg: MarketConfig = DEFAULT_CONFIG,
    rng: random.Random = random,
) -> None:
    """Mutate `shop` in-place: update buy_price + add restock qty."""
    for sku, s in shop.items():
        base = float(items[sku].get("base_price", 0.0) or 0.0)
        current = float(s.get("buy_price", 0.0) or 0.0)

        toward_base = (base - current) * float(cfg.mean_reversion)
        shock = current * rng.uniform(-float(cfg.volatility), float(cfg.volatility))

        new_price = max(1.0, current + toward_base + shock)
        s["buy_price"] = new_price

        s["qty"] = int(s.get("qty", 0) or 0) + int(rng.randint(cfg.restock_min, cfg.restock_max))


def next_day(
    items: Dict[str, Dict],
    shop: Dict[str, Dict],
    player: Dict,
    log_txn: Callable[[int, str, str, int, float, float, float], None],
    bill_interval: int = 7,
    cfg: MarketConfig = DEFAULT_CONFIG,
    rng: random.Random = random,
) -> str:
    """Advance one day: reprice/restock, increment day, handle rent (Sunday).

    Returns a bill message if rent was paid, else "".
    """
    update_shop_prices_and_stock(items, shop, cfg=cfg, rng=rng)

    player["day"] = int(player.get("day", 1) or 1) + 1

    # Every Sunday (each `bill_interval` day), deduct rent. Rent equals current storage capacity.
    if player["day"] % int(bill_interval) == 0:
        cost = float(player.get("capacity", 0) or 0)
        player["cash"] = float(player.get("cash", 0.0) or 0.0) - cost
        # Log as a rent transaction; use SKU "" to denote non-item
        log_txn(int(player["day"]), "", "RENT", 1, cost, cost, float(player["cash"]))
        return f"Paid rent: ${cost:.0f}"
    return ""


def update_avg_buy_prices(
    shop: Dict[str, Dict],
    avg_buy_prices: Dict[str, float],
    current_day: int,
) -> None:
    """Update running average buy prices per SKU (in-place)."""
    day = int(current_day or 1)
    for sku in shop:
        cur = float(shop[sku].get("buy_price", 0.0) or 0.0)
        prev_avg = float(avg_buy_prices.get(sku, cur))
        # Weighted average: previous average times (day-1) plus current price
        avg_buy_prices[sku] = ((prev_avg * (day - 1)) + cur) / day


def build_daily_chat_message(
    *,
    player: Dict,
    shop: Dict[str, Dict],
    inv: Dict[str, Dict],
    avg_buy_prices: Dict[str, float],
    bill_interval: int = 7,
    cfg: MarketConfig = DEFAULT_CONFIG,
    rng: random.Random = random,
) -> Optional[str]:
    """Return the daily chat message (tip or fact), or None if nothing to say.

    This keeps the *market advice* logic in one place.
    """
    day = int(player.get("day", 1) or 1)

    # Update running avg prices first (so the day's message uses the latest avg)
    update_avg_buy_prices(shop, avg_buy_prices, current_day=day)

    tips = []
    facts = []

    # Buy tip: current is meaningfully below avg
    buy_candidates = []
    for sku in shop:
        cur_price = float(shop[sku].get("buy_price", 0.0) or 0.0)
        avg_price = float(avg_buy_prices.get(sku, cur_price))
        if avg_price > 0 and cur_price < avg_price * float(cfg.buy_tip_threshold):
            buy_candidates.append((sku, cur_price, avg_price))
    if buy_candidates:
        sku, cur_price, avg_price = min(buy_candidates, key=lambda x: (x[1] / x[2]) if x[2] else 9999)
        tips.append(f"Tip: BUY {sku} – now ${cur_price:.2f} < avg ${avg_price:.2f}")

    # Sell tip: sell price beats your avg cost by threshold
    sell_candidates = []
    for sku in inv:
        if sku not in shop:
            continue
        sp = sell_price(float(shop[sku].get("buy_price", 0.0) or 0.0), cfg=cfg)
        avg_cost = float(inv[sku].get("avg_cost", 0.0) or 0.0)
        if avg_cost > 0 and sp > avg_cost * float(cfg.sell_tip_threshold):
            sell_candidates.append((sku, sp, avg_cost))
    if sell_candidates:
        sku, sp, cost = max(sell_candidates, key=lambda x: (x[1] / x[2]) if x[2] else 0)
        tips.append(f"Tip: SELL {sku} – sell ${sp:.2f} > cost ${cost:.2f}")

    # Facts about rent due and cash (rent = current storage capacity)
    bi = int(bill_interval) if int(bill_interval) > 0 else 7
    days_until = bi - (day % bi)
    next_rent = int(player.get("capacity", 0) or 0)
    facts.append(f"{days_until} day{'s' if days_until != 1 else ''} till rent (${next_rent}) is due.")
    facts.append(f"You have ${float(player.get('cash', 0.0) or 0.0):.2f} cash.")

    # Alternate: odd days => tips, even days => facts (if available)
    show_tip = (day % 2 == 1)

    chosen = None
    if show_tip and tips:
        chosen = rng.choice(tips)
    elif (not show_tip) and facts:
        chosen = rng.choice(facts)

    if not chosen:
        if tips:
            chosen = rng.choice(tips)
        elif facts:
            chosen = rng.choice(facts)

    return chosen
