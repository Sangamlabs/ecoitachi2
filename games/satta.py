"""Satta Matka game mechanics.

Supports traditional Indian Satta Matka bets:
- Single Haruf (0-9): 9x Payout
- Jodi / Pair (00-99): 90x Jackpot Payout
- Odd / Even: 2x Payout
- High / Low (00-49 / 50-99): 2x Payout
"""

from __future__ import annotations

import logging
import random
from typing import Any

from services import game_engine

logger = logging.getLogger(__name__)


async def play(
    user_id: int,
    bet: int,
    selection: str,
    *,
    chat_id: int | None = None,
) -> dict[str, Any]:
    sel = selection.strip().lower()
    bet_type = None
    target_val = None
    multiplier = 0.0

    # 1. Even / Odd
    if sel in ("even", "ev"):
        bet_type = "even"
        multiplier = 2.0
    elif sel in ("odd", "od"):
        bet_type = "odd"
        multiplier = 2.0
    # 2. High / Low
    elif sel in ("high", "hi"):
        bet_type = "high"
        multiplier = 2.0
    elif sel in ("low", "lo"):
        bet_type = "low"
        multiplier = 2.0
    # 3. Jodi (00 to 99)
    elif sel.isdigit() and len(sel) == 2:
        bet_type = "jodi"
        target_val = int(sel)
        multiplier = 90.0
    # 4. Single Haruf (0 to 9)
    elif sel.isdigit() and len(sel) == 1:
        bet_type = "single"
        target_val = int(sel)
        multiplier = 9.0
    else:
        raise game_engine.GameError(
            "Invalid Satta bet! Options:\n"
            "• Single digit: <code>0-9</code> (9x payout, e.g. <code>/satta 7 50k</code>)\n"
            "• Jodi (pair): <code>00-99</code> (90x jackpot, e.g. <code>/satta 47 10k</code>)\n"
            "• <code>even</code> / <code>odd</code> (2x payout)\n"
            "• <code>high</code> / <code>low</code> (2x payout)"
        )

    # Draw random Satta Lucky Number from 00 to 99
    drawn_number = random.randint(0, 99)
    open_digit = drawn_number // 10
    close_digit = drawn_number % 10
    sum_digit = (open_digit + close_digit) % 10
    drawn_str = f"{drawn_number:02d}"

    won = False
    if bet_type == "jodi":
        won = (drawn_number == target_val)
    elif bet_type == "single":
        # Matches open digit, close digit, or sum digit (Haruf)
        won = (target_val == close_digit or target_val == open_digit)
    elif bet_type == "even":
        won = (drawn_number % 2 == 0)
    elif bet_type == "odd":
        won = (drawn_number % 2 != 0)
    elif bet_type == "high":
        won = (drawn_number >= 50)
    elif bet_type == "low":
        won = (drawn_number < 50)

    payout = int(bet * multiplier) if won else 0

    await game_engine.instant_game(
        user_id,
        "satta",
        bet,
        won=won,
        payout=payout,
        multiplier=multiplier if won else 0.0,
        meta={
            "bet_type": bet_type,
            "selection": selection,
            "drawn_number": drawn_str,
            "open_digit": open_digit,
            "close_digit": close_digit,
            "sum_digit": sum_digit,
        },
        chat_id=chat_id,
    )

    return {
        "bet": bet,
        "bet_type": bet_type,
        "selection": selection,
        "drawn_number": drawn_str,
        "open_digit": open_digit,
        "close_digit": close_digit,
        "sum_digit": sum_digit,
        "won": won,
        "multiplier": multiplier,
        "payout": payout,
    }
