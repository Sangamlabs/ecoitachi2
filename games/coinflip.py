"""Coinflip game mechanics.

Player bets on Heads (H) or Tails (T). 50/50 fair probability.
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
    choice: str,
    *,
    chat_id: int | None = None,
) -> dict[str, Any]:
    choice_normalized = choice.strip().lower()
    if choice_normalized in ("h", "head", "heads"):
        picked = "heads"
    elif choice_normalized in ("t", "tail", "tails"):
        picked = "tails"
    else:
        raise game_engine.GameError("Invalid coin choice! Use <code>heads</code> (or <code>h</code>) or <code>tails</code> (or <code>t</code>).")

    settings = await game_engine.validate_game_input("coinflip")
    win_prob = float(settings.get("win_probability", 0.50))
    multiplier = float(settings.get("multiplier", 2.0))

    # Fair random toss
    flipped = "heads" if random.random() < 0.50 else "tails"
    won = (picked == flipped)
    payout = int(bet * multiplier) if won else 0

    await game_engine.instant_game(
        user_id,
        "coinflip",
        bet,
        won=won,
        payout=payout,
        multiplier=multiplier,
        meta={"picked": picked, "flipped": flipped},
        chat_id=chat_id,
    )

    return {
        "bet": bet,
        "picked": picked,
        "flipped": flipped,
        "won": won,
        "multiplier": multiplier,
        "payout": payout,
    }
