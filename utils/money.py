"""Centralized money utilities.

All currency is stored as an integer in the smallest unit (rupees x 100,
so ₹10.50 = 1050).  Floating-point values are NEVER used for internal money.
Only pure functions live here so they can be unit tested without a database.
"""

from __future__ import annotations

import re
from typing import Union

UNIT = 100  # 1 UN = 100 sub-units
SYMBOL = "₹"

Number = Union[int, str, float]


class MoneyError(ValueError):
    """Raised for invalid monetary amounts."""


def _to_int(value: Number) -> int:
    if isinstance(value, bool):
        raise MoneyError("boolean is not a valid amount")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise MoneyError("float amounts must be whole sub-units")
        return int(value)
    raise MoneyError(f"cannot parse {value!r} as money")


def parse_amount(raw: str, allow_zero: bool = True) -> int:
    """Parse a user-supplied amount string into integer sub-units.

    Accepts forms like ``500``, ``10.50``, ``1,000.25``, ``0.01``,
    and human-friendly suffixes like ``500k``, ``1.5M``, ``2B``, ``1T``, ``5cr``, ``10L``.
    Rejects negatives, NaN, and invalid characters.
    """
    if not isinstance(raw, str):
        raw = str(raw)
    cleaned = raw.strip().lower().replace(",", "").replace(SYMBOL.lower(), "")
    for prefix in ("rs.", "rs", "inr"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    if not cleaned:
        raise MoneyError("amount is empty")

    # Check for suffix multipliers
    multipliers = {
        "k": 1_000,
        "m": 1_000_000,
        "b": 1_000_000_000,
        "t": 1_000_000_000_000,
        "cr": 10_000_000,
        "crore": 10_000_000,
        "l": 100_000,
        "lakh": 100_000,
    }

    match = re.fullmatch(r"(\d+(\.\d+)?)\s*([a-z]+)?", cleaned)
    if not match:
        raise MoneyError(f"invalid amount: {raw!r}")

    num_part = match.group(1)
    suffix = match.group(3)

    if suffix:
        if suffix not in multipliers:
            raise MoneyError(f"unknown amount suffix: {suffix!r}")
        val = float(num_part) * multipliers[suffix]
        subunits = int(round(val * UNIT))
        if subunits < 0:
            raise MoneyError("amount cannot be negative")
        if not allow_zero and subunits == 0:
            raise MoneyError("amount must be positive")
        return subunits

    # Plain number without suffix: enforce max 2 decimal places
    if not re.fullmatch(r"\d+(\.\d{1,2})?", cleaned):
        raise MoneyError(f"invalid amount: {raw!r}")

    if "." in cleaned:
        whole, _, frac = cleaned.partition(".")
        frac = (frac + "00")[:2]
        subunits = int(whole) * UNIT + int(frac)
    else:
        subunits = int(cleaned) * UNIT

    if subunits < 0:
        raise MoneyError("amount cannot be negative")
    return subunits


def is_valid_amount(raw: str) -> bool:
    try:
        parse_amount(raw)
        return True
    except MoneyError:
        return False


def format_money(units: Number, compact: bool = True) -> str:
    """Format integer sub-units as a human-readable ₹ string.
    
    When compact=True, large values (>= ₹100,000) are cleanly rendered
    as K, M, B, or T to prevent 0-spam in group chats.
    """
    units = _to_int(units)
    sign = "-" if units < 0 else ""
    abs_units = abs(units)
    rupees = abs_units / UNIT

    if compact and rupees >= 100_000:
        if rupees >= 1_000_000_000_000:  # Trillion
            num_str = f"{rupees / 1_000_000_000_000:.2f}".rstrip("0").rstrip(".")
            return f"{sign}{SYMBOL}{num_str}T"
        if rupees >= 1_000_000_000:  # Billion
            num_str = f"{rupees / 1_000_000_000:.2f}".rstrip("0").rstrip(".")
            return f"{sign}{SYMBOL}{num_str}B"
        if rupees >= 1_000_000:  # Million
            num_str = f"{rupees / 1_000_000:.2f}".rstrip("0").rstrip(".")
            return f"{sign}{SYMBOL}{num_str}M"
        if rupees >= 100_000:  # 100K+
            num_str = f"{rupees / 1_000:.1f}".rstrip("0").rstrip(".")
            return f"{sign}{SYMBOL}{num_str}K"

    whole_rupees, paise = divmod(abs_units, UNIT)
    body = f"{whole_rupees:,}"
    if paise:
        body += f".{paise:02d}".rstrip("0")
    return f"{sign}{SYMBOL}{body}"


def format_exact_money(units: Number) -> str:
    """Always format exact comma-separated sub-units without K/M/B abbreviations."""
    return format_money(units, compact=False)


def is_positive(units: Number) -> bool:
    return _to_int(units) > 0


def check_balance(balance: Number, amount: Number) -> bool:
    """True when balance - amount >= 0."""
    return _to_int(balance) >= _to_int(amount)


def add(a: Number, b: Number) -> int:
    return _to_int(a) + _to_int(b)


def subtract(a: Number, b: Number) -> int:
    return _to_int(a) - _to_int(b)


def percentage(amount: Number, rate: float) -> int:
    """Compute ``amount * rate %`` as an integer (rounded down)."""
    if rate < 0:
        raise MoneyError("rate cannot be negative")
    return int(_to_int(amount) * rate) // 100


def multiply(amount: Number, multiplier: float) -> int:
    """Integer payout for a decimal multiplier (e.g. 1.5x)."""
    if multiplier < 0:
        raise MoneyError("multiplier cannot be negative")
    return int(_to_int(amount) * multiplier)
