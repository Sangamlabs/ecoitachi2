"""Color Trading & Big / Small (Win Go) game mechanics.

Rules & Payouts:
- Big (5, 6, 7, 8, 9): 2.0x Payout
- Small (0, 1, 2, 3, 4): 2.0x Payout
- Green (1, 3, 7, 9 [and 5 half]): 2.0x Payout
- Red (2, 4, 6, 8 [and 0 half]): 2.0x Payout
- Violet (0, 5): 4.5x Payout
- Single Number (0 - 9): 9.0x Payout
"""

from __future__ import annotations

import logging
import random
from typing import Any

from services import game_engine

logger = logging.getLogger(__name__)

COLOR_MAP = {
    0: ("🔴 🟣", "Red + Violet"),
    1: ("🟢", "Green"),
    2: ("🔴", "Red"),
    3: ("🟢", "Green"),
    4: ("🔴", "Red"),
    5: ("🟢 🟣", "Green + Violet"),
    6: ("🔴", "Red"),
    7: ("🟢", "Green"),
    8: ("🔴", "Red"),
    9: ("🟢", "Green"),
}


async def play(
    user_id: int,
    bet: int,
    selection: str,
    *,
    chat_id: int | None = None,
) -> dict[str, Any]:
    sel = selection.strip().lower()
    bet_type = None
    target_num = None

    if sel in ("b", "big", "bada"):
        bet_type = "big"
    elif sel in ("s", "small", "chota"):
        bet_type = "small"
    elif sel in ("g", "green", "hara"):
        bet_type = "green"
    elif sel in ("r", "red", "lal"):
        bet_type = "red"
    elif sel in ("v", "violet", "purple", "baingani"):
        bet_type = "violet"
    elif sel.isdigit() and 0 <= int(sel) <= 9:
        bet_type = "number"
        target_num = int(sel)
    else:
        raise game_engine.GameError(
            "Invalid Color Trading selection! Options:\n"
            "• <code>big</code> (5-9) or <code>small</code> (0-4) — 2.0x\n"
            "• <code>green</code> or <code>red</code> — 2.0x\n"
            "• <code>violet</code> (0 or 5) — 4.5x\n"
            "• Number <code>0-9</code> — 9.0x"
        )

    # Random drawn number from 0 to 9
    drawn_number = random.randint(0, 9)
    color_emoji, color_name = COLOR_MAP[drawn_number]
    size_name = "Big 📈" if drawn_number >= 5 else "Small 📉"

    won = False
    multiplier = 0.0

    if bet_type == "big":
        won = drawn_number >= 5
        multiplier = 2.0 if won else 0.0
    elif bet_type == "small":
        won = drawn_number < 5
        multiplier = 2.0 if won else 0.0
    elif bet_type == "green":
        if drawn_number in (1, 3, 7, 9):
            won = True
            multiplier = 2.0
        elif drawn_number == 5:
            won = True
            multiplier = 1.5  # Green + Violet split
    elif bet_type == "red":
        if drawn_number in (2, 4, 6, 8):
            won = True
            multiplier = 2.0
        elif drawn_number == 0:
            won = True
            multiplier = 1.5  # Red + Violet split
    elif bet_type == "violet":
        won = drawn_number in (0, 5)
        multiplier = 4.5 if won else 0.0
    elif bet_type == "number":
        won = (drawn_number == target_num)
        multiplier = 9.0 if won else 0.0

    payout = int(bet * multiplier) if won else 0

    await game_engine.instant_game(
        user_id,
        "color",
        bet,
        won=won,
        payout=payout,
        multiplier=multiplier,
        meta={
            "bet_type": bet_type,
            "selection": selection,
            "drawn_number": drawn_number,
            "color_name": color_name,
            "size_name": size_name,
        },
        chat_id=chat_id,
    )

    return {
        "bet": bet,
        "bet_type": bet_type,
        "selection": selection,
        "drawn_number": drawn_number,
        "color_emoji": color_emoji,
        "color_name": color_name,
        "size_name": size_name,
        "won": won,
        "multiplier": multiplier,
        "payout": payout,
    }
