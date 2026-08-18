"""User-facing formatting helpers (no HTML building here - see messages.py)."""

from __future__ import annotations

import time


def tg_link(user_id: int, name: str) -> str:
    """Inline Telegram user link ``<a href="tg://user?id=..">name</a>``."""
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def escape_markup(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def humanize_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    parts: list[str] = []
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        count, seconds = divmod(seconds, size)
        if count:
            parts.append(f"{count}{unit}")
    return " ".join(parts)


def utc_now() -> int:
    return int(time.time())


def format_datetime(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or singular + "s")


_AESTHETIC_MAP: dict[str, str] = {
    "A": "𝐀", "B": "𝐁", "C": "𝐂", "D": "𝐃", "E": "𝐄", "F": "𝐅", "G": "𝐆", "H": "𝐇", "I": "𝐈", "J": "𝐉",
    "K": "𝐊", "L": "𝐋", "M": "𝐌", "N": "𝐍", "O": "𝐎", "P": "𝐏", "Q": "𝐐", "R": "𝐑", "S": "𝐒", "T": "𝐓",
    "U": "𝐔", "V": "𝐕", "W": "𝐖", "X": "𝐗", "Y": "𝐘", "Z": "𝐙",
    "a": "ᴧ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "є", "f": "ꜰ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
    "k": "ᴋ", "l": "ʟ", "m": "ϻ", "n": "η", "o": "σ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ",
    "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
}


def font_style(text: str) -> str:
    """Transform text into aesthetic unicode typography (e.g. 𝐁σᴛ ʜᴧs ʙєєη σᴘᴛɪϻɪsєᴅ ᴡєʟʟ)."""
    return "".join(_AESTHETIC_MAP.get(c, c) for c in text)

