"""Armory and Gun Market service.

High-tier luxury firearms with combat perks for robbery offense and defense:
- GLOCK: Glock 19 (₹500K)
- DEAGLE: Desert Eagle .50 (₹2.5M)
- AK47: AK-47 Kalashnikov (₹10M)
- M4A1: M4A1 Carbine (₹25M)
- AWP: AWP Dragon Lore (₹50M)
- MINIGUN: M134 Vulcan Minigun (₹100M)
"""

from __future__ import annotations

import logging
import time
from typing import Any

from database.mongo import mongo
from database.users import COLLECTION as USERS_COLLECTION
from services import economy, transaction as tx_service
from services.economy import EconomyError, InsufficientBalance, ensure_active
from utils.formatting import font_style
from utils.money import format_money

logger = logging.getLogger(__name__)

GUNS: dict[str, dict[str, Any]] = {
    "glock": {
        "id": "glock",
        "name": "Glock 19 Gen5",
        "emoji": "🔫",
        "price": 100_000_000_000_000,  # ₹1 Trillion
        "attack_buff": 0.10,
        "defense_buff": 0.10,
        "desc": "Standard 9mm sidearm. Tactical stealth protection.",
    },
    "deagle": {
        "id": "deagle",
        "name": "Desert Eagle .50 AE",
        "emoji": "🦅",
        "price": 500_000_000_000_000,  # ₹5 Trillion
        "attack_buff": 0.20,
        "defense_buff": 0.20,
        "desc": "Heavy-caliber hand cannon. High stopping power.",
    },
    "ak47": {
        "id": "ak47",
        "name": "AK-47 Kalashnikov",
        "emoji": "💥",
        "price": 2_500_000_000_000_000,  # ₹25 Trillion
        "attack_buff": 0.35,
        "defense_buff": 0.35,
        "desc": "Legendary 7.62mm assault rifle. High durability and fire rate.",
    },
    "m4a1": {
        "id": "m4a1",
        "name": "M4A1 Tactical Carbine",
        "emoji": "⚡",
        "price": 10_000_000_000_000_000,  # ₹100 Trillion
        "attack_buff": 0.50,
        "defense_buff": 0.50,
        "desc": "Military-grade suppressed carbine. Superior raid accuracy.",
    },
    "awp": {
        "id": "awp",
        "name": "AWP Dragon Lore",
        "emoji": "🎯",
        "price": 25_000_000_000_000_000,  # ₹250 Trillion
        "attack_buff": 0.70,
        "defense_buff": 0.70,
        "desc": "High-powered bolt-action sniper rifle. One-shot supremacy.",
    },
    "minigun": {
        "id": "minigun",
        "name": "M134 Vulcan Minigun",
        "emoji": "🛡️",
        "price": 50_000_000_000_000_000,  # ₹500 Trillion
        "attack_buff": 0.90,
        "defense_buff": 0.90,
        "desc": "6-barrel rotary heavy machine gun. Total impenetrable defense.",
    },
}


def get_all_guns() -> dict[str, dict[str, Any]]:
    return GUNS


def get_gun(gun_id: str) -> dict[str, Any] | None:
    return GUNS.get(gun_id.lower().strip())


async def get_user_guns(user_id: int) -> list[str]:
    doc = await mongo.db[USERS_COLLECTION].find_one(
        {"user_id": user_id},
        {"inventory_guns": 1},
    )
    if not doc or "inventory_guns" not in doc:
        return []
    return list(doc["inventory_guns"])


async def buy_gun(user_id: int, gun_id: str) -> dict[str, Any]:
    gun = get_gun(gun_id)
    if not gun:
        raise EconomyError(f"Unknown firearm: <code>{gun_id}</code>")

    user = await economy._require_user(user_id)
    await ensure_active(user)

    owned = await get_user_guns(user_id)
    if gun["id"] in owned:
        raise EconomyError(f"You already own the <b>{gun['name']}</b> in your armory!")

    price = gun["price"]
    wallet = int(user.get("wallet", 0))
    if wallet < price:
        raise InsufficientBalance(price, wallet)

    # Deduct wallet atomically
    result = await economy.mongo_db_update_guarded(
        user_id, price, {"wallet": -price, "total_spent": price}
    )
    if result is None:
        raise InsufficientBalance(price, wallet)

    # Add gun to user inventory and increment asset value
    await mongo.db[USERS_COLLECTION].update_one(
        {"user_id": user_id},
        {
            "$addToSet": {"inventory_guns": gun["id"]},
            "$inc": {"asset_value": price},
            "$set": {"updated_at": int(time.time())},
        },
    )

    # Audit transaction
    tx_id = await tx_service.record(
        user_id=user_id,
        ttype="GUN_PURCHASE",
        amount=price,
        balance_before=wallet,
        balance_after=wallet - price,
        metadata={"gun_id": gun["id"], "gun_name": gun["name"]},
    )

    return {
        "gun": gun,
        "price": price,
        "tx_id": tx_id,
        "remaining_wallet": wallet - price,
    }


async def get_rob_buffs(user_id: int) -> tuple[float, float]:
    """Returns (attack_buff, defense_buff) derived from highest firearm owned."""
    owned = await get_user_guns(user_id)
    if not owned:
        return 0.0, 0.0

    max_attack = 0.0
    max_defense = 0.0
    for gid in owned:
        g = GUNS.get(gid)
        if g:
            if g["attack_buff"] > max_attack:
                max_attack = g["attack_buff"]
            if g["defense_buff"] > max_defense:
                max_defense = g["defense_buff"]

    return max_attack, max_defense
