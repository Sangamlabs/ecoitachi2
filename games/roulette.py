"""European Roulette game mechanics.

Supports betting on Red, Black, Green, Odd, Even, or a specific Number (0-36).
"""

from __future__ import annotations

import logging
import random
from typing import Any

from services import game_engine

logger = logging.getLogger(__name__)

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
BLACK_NUMBERS = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}


def get_color(num: int) -> str:
    if num == 0:
        return "green"
    return "red" if num in RED_NUMBERS else "black"


def get_color_emoji(num: int) -> str:
    if num == 0:
        return "🟢"
    return "🔴" if num in RED_NUMBERS else "⚫"


async def play(
    user_id: int,
    bet: int,
    selection: str,
    *,
    chat_id: int | None = None,
) -> dict[str, Any]:
    sel = selection.strip().lower()

    # Determine bet target and payout multiplier
    is_number = False
    target_number = -1

    if sel in ("red", "r"):
        bet_type = "red"
        multiplier = 2.0
    elif sel in ("black", "b", "blk"):
        bet_type = "black"
        multiplier = 2.0
    elif sel in ("green", "g", "zero", "0"):
        bet_type = "green"
        multiplier = 36.0
    elif sel in ("odd", "odds"):
        bet_type = "odd"
        multiplier = 2.0
    elif sel in ("even", "evens"):
        bet_type = "even"
        multiplier = 2.0
    elif sel.isdigit():
        num = int(sel)
        if not (0 <= num <= 36):
            raise game_engine.GameError("Roulette numbers must be between 0 and 36.")
        bet_type = f"number_{num}"
        is_number = True
        target_number = num
        multiplier = 36.0
    else:
        raise game_engine.GameError(
            "Invalid roulette selection! Choose:\n"
            "• <code>red</code> / <code>black</code> (2x payout)\n"
            "• <code>odd</code> / <code>even</code> (2x payout)\n"
            "• <code>green</code> / <code>0-36</code> (36x payout)"
        )

    # Spin the wheel (0 to 36)
    landed_number = random.randint(0, 36)
    landed_color = get_color(landed_number)
    landed_emoji = get_color_emoji(landed_number)

    # Check win
    won = False
    if is_number:
        won = (landed_number == target_number)
    elif bet_type == "red":
        won = (landed_color == "red")
    elif bet_type == "black":
        won = (landed_color == "black")
    elif bet_type == "green":
        won = (landed_number == 0)
    elif bet_type == "odd":
        won = (landed_number != 0 and landed_number % 2 != 0)
    elif bet_type == "even":
        won = (landed_number != 0 and landed_number % 2 == 0)

    payout = int(bet * multiplier) if won else 0

    await game_engine.instant_game(
        user_id,
        "roulette",
        bet,
        won=won,
        payout=payout,
        multiplier=multiplier,
        meta={
            "selection": sel,
            "bet_type": bet_type,
            "landed_number": landed_number,
            "landed_color": landed_color,
        },
        chat_id=chat_id,
    )

    return {
        "bet": bet,
        "selection": sel,
        "bet_type": bet_type,
        "landed_number": landed_number,
        "landed_color": landed_color,
        "landed_emoji": landed_emoji,
        "won": won,
        "multiplier": multiplier,
        "payout": payout,
    }
