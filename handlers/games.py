"""Game handlers: /fly, /mines, /bet + mines inline-board callbacks."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from games import (
    bet as bet_game,
    coinflip as coinflip_game,
    color_trading as color_game,
    fly as fly_game,
    mines as mines_game,
    roulette as roulette_game,
    satta as satta_game,
)
from database import games as games_db
from handlers.common import ensure_user, safe_handler
from services import game_engine
from utils import messages as msgs
from utils.money import format_money
from utils.sender import answer_callback, edit_html, reply_html
from utils.validators import parse_amount_or_error

logger = logging.getLogger(__name__)

MINES_CB_PREFIX = "mines:"

NOT_CHANNEL = ~filters.channel & ~filters.bot


def _parse_mines_callback(data: str) -> tuple[str, str] | None:
    """Split ``mines:SESSION_ID:ACTION`` into (session_id, action)."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "mines":
        return None
    return parts[1], parts[2]


def register(app: Client) -> None:
    @app.on_message(filters.command("fly") & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_fly(client: Client, message: Message):
        await ensure_user(client, message)
        args = message.command[1:]
        if len(args) < 2:
            await reply_html(
                client, message,
                msgs.error("Usage: <code>/fly low|medium|high amount</code>"),
            )
            return
        difficulty = fly_game.parse_difficulty(args[0])
        bet, err = parse_amount_or_error(args[1])
        if err:
            await reply_html(client, message, msgs.error(err))
            return
        result = await fly_game.play(
            message.from_user.id, difficulty, bet, chat_id=message.chat.id
        )
        await reply_html(
            client, message,
            msgs.fly_result(
                result["difficulty"], result["bet"], result["won"],
                result["multiplier"], result["payout"], result["session_id"],
            ),
        )

    @app.on_message(filters.command(["coinflip", "cf"]) & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_coinflip(client: Client, message: Message):
        await ensure_user(client, message)
        args = message.command[1:]
        if len(args) < 2:
            await reply_html(
                client, message,
                msgs.error("Usage: <code>/cf heads|tails amount</code> (e.g. <code>/cf h 500k</code>)"),
            )
            return

        if args[0].lower() in ("h", "t", "head", "heads", "tail", "tails"):
            choice = args[0]
            amount_str = args[1]
        elif args[1].lower() in ("h", "t", "head", "heads", "tail", "tails"):
            choice = args[1]
            amount_str = args[0]
        else:
            await reply_html(
                client, message,
                msgs.error("Invalid call! Use <code>heads</code> (or <code>h</code>) / <code>tails</code> (or <code>t</code>)."),
            )
            return

        bet, err = parse_amount_or_error(amount_str)
        if err:
            await reply_html(client, message, msgs.error(err))
            return

        result = await coinflip_game.play(
            message.from_user.id, bet, choice, chat_id=message.chat.id
        )
        await reply_html(
            client, message,
            msgs.coinflip_result(
                result["bet"], result["picked"], result["flipped"],
                result["won"], result["multiplier"], result["payout"],
                result.get("session_id", ""),
            ),
        )

    @app.on_message(filters.command(["roulette", "roul"]) & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_roulette(client: Client, message: Message):
        await ensure_user(client, message)
        args = message.command[1:]
        if len(args) < 2:
            await reply_html(
                client, message,
                msgs.error(
                    "Usage: <code>/roul red|black|green|odd|even|0-36 amount</code>\n"
                    "Example: <code>/roul red 500k</code> or <code>/roul 17 100k</code>"
                ),
            )
            return

        valid_words = {"red", "r", "black", "b", "blk", "green", "g", "zero", "0", "odd", "odds", "even", "evens"}
        arg0_is_word = args[0].lower() in valid_words or (args[0].isdigit() and 0 <= int(args[0]) <= 36 and args[1].lower() not in valid_words)

        if arg0_is_word:
            selection = args[0]
            amount_str = args[1]
        else:
            selection = args[1]
            amount_str = args[0]

        bet, err = parse_amount_or_error(amount_str)
        if err:
            await reply_html(client, message, msgs.error(err))
            return

        result = await roulette_game.play(
            message.from_user.id, bet, selection, chat_id=message.chat.id
        )
        await reply_html(
            client, message,
            msgs.roulette_result(
                result["bet"], result["selection"], result["landed_number"],
                result["landed_color"], result["landed_emoji"], result["won"],
                result["multiplier"], result["payout"], result.get("session_id", ""),
            ),
        )

    @app.on_message(filters.command(["satta", "matka"]) & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_satta(client: Client, message: Message):
        await ensure_user(client, message)
        args = message.command[1:]
        if len(args) < 2:
            await reply_html(
                client, message,
                msgs.error(
                    "Usage: <code>/satta [bet_type/number] [amount]</code>\n"
                    "• Single Haruf (0-9): <code>/satta 7 50k</code> (9x payout)\n"
                    "• Jodi Jackpot (00-99): <code>/satta 47 10k</code> (90x payout!)\n"
                    "• Even / Odd: <code>/satta even 100k</code> (2x payout)\n"
                    "• High / Low: <code>/satta high 50k</code> (2x payout)"
                ),
            )
            return

        valid_words = {"even", "ev", "odd", "od", "high", "hi", "low", "lo"}
        arg0_is_choice = args[0].lower() in valid_words or (args[0].isdigit() and len(args[0]) in (1, 2) and args[1].lower() not in valid_words)

        if arg0_is_choice:
            selection = args[0]
            amount_str = args[1]
        else:
            selection = args[1]
            amount_str = args[0]

        bet, err = parse_amount_or_error(amount_str)
        if err:
            await reply_html(client, message, msgs.error(err))
            return

        result = await satta_game.play(
            message.from_user.id, bet, selection, chat_id=message.chat.id
        )
        await reply_html(
            client, message,
            msgs.satta_result(
                result["bet"], result["bet_type"], result["selection"],
                result["drawn_number"], result["open_digit"], result["close_digit"],
                result["sum_digit"], result["won"], result["multiplier"],
                result["payout"], result.get("session_id", ""),
            ),
        )

    @app.on_message(filters.command(["color", "trade", "wingo"]) & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_color(client: Client, message: Message):
        await ensure_user(client, message)
        args = message.command[1:]
        
        # If user types just `/color 50k` (amount only), show interactive Inline Buttons!
        if len(args) == 1:
            bet, err = parse_amount_or_error(args[0])
            if err is None and bet > 0:
                uid = message.from_user.id
                uname = message.from_user.username or message.from_user.first_name
                prompt_text = (
                    f"<b>🎨 {msgs.font_style('Color Trading & Big-Small')}</b>\n"
                    f"<blockquote>👤 <b>{msgs.font_style('Player')}:</b> <a href=\"tg://user?id={uid}\">{uname}</a>\n"
                    f"💵 <b>{msgs.font_style('Bet Amount')}:</b> <b>{format_money(bet)}</b></blockquote>\n"
                    f"<blockquote>🎯 <i>{msgs.font_style('Tap your prediction below to trade instantly')}:</i></blockquote>"
                )
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📈 Big (2.0x)", callback_data=f"color:{uid}:{bet}:big"),
                        InlineKeyboardButton("📉 Small (2.0x)", callback_data=f"color:{uid}:{bet}:small"),
                    ],
                    [
                        InlineKeyboardButton("🟢 Green (2x)", callback_data=f"color:{uid}:{bet}:green"),
                        InlineKeyboardButton("🟣 Violet (4.5x)", callback_data=f"color:{uid}:{bet}:violet"),
                        InlineKeyboardButton("🔴 Red (2x)", callback_data=f"color:{uid}:{bet}:red"),
                    ],
                    [
                        InlineKeyboardButton("0", callback_data=f"color:{uid}:{bet}:0"),
                        InlineKeyboardButton("1", callback_data=f"color:{uid}:{bet}:1"),
                        InlineKeyboardButton("2", callback_data=f"color:{uid}:{bet}:2"),
                        InlineKeyboardButton("3", callback_data=f"color:{uid}:{bet}:3"),
                        InlineKeyboardButton("4", callback_data=f"color:{uid}:{bet}:4"),
                    ],
                    [
                        InlineKeyboardButton("5", callback_data=f"color:{uid}:{bet}:5"),
                        InlineKeyboardButton("6", callback_data=f"color:{uid}:{bet}:6"),
                        InlineKeyboardButton("7", callback_data=f"color:{uid}:{bet}:7"),
                        InlineKeyboardButton("8", callback_data=f"color:{uid}:{bet}:8"),
                        InlineKeyboardButton("9", callback_data=f"color:{uid}:{bet}:9"),
                    ],
                ])
                await reply_html(client, message, prompt_text, reply_markup=keyboard)
                return

        if len(args) < 2:
            await reply_html(
                client, message,
                msgs.error(
                    "Usage: <code>/color [amount]</code> (for inline buttons)\n"
                    "Or: <code>/color [prediction] [amount]</code>\n"
                    "• <code>big</code> (5-9) / <code>small</code> (0-4) — 2x payout (e.g. <code>/color big 100k</code>)\n"
                    "• <code>green</code> / <code>red</code> — 2x payout (e.g. <code>/color red 50k</code>)\n"
                    "• <code>violet</code> (0 or 5) — 4.5x payout (e.g. <code>/color violet 20k</code>)\n"
                    "• Exact Number (0-9) — 9.0x payout (e.g. <code>/color 7 10k</code>)"
                ),
            )
            return

        valid_words = {"big", "b", "small", "s", "green", "g", "red", "r", "violet", "v", "purple", "bada", "chota", "hara", "lal"}
        arg0_is_choice = args[0].lower() in valid_words or (args[0].isdigit() and len(args[0]) == 1 and args[1].lower() not in valid_words)

        if arg0_is_choice:
            selection = args[0]
            amount_str = args[1]
        else:
            selection = args[1]
            amount_str = args[0]

        bet, err = parse_amount_or_error(amount_str)
        if err:
            await reply_html(client, message, msgs.error(err))
            return

        result = await color_game.play(
            message.from_user.id, bet, selection, chat_id=message.chat.id
        )
        await reply_html(
            client, message,
            msgs.color_trade_result(
                result["bet"], result["bet_type"], result["selection"],
                result["drawn_number"], result["color_emoji"], result["color_name"],
                result["size_name"], result["won"], result["multiplier"],
                result["payout"], result.get("session_id", ""),
            ),
        )

    @app.on_callback_query(filters.regex(r"^color:"))
    async def cb_color_choice(client: Client, query: CallbackQuery):
        parts = query.data.split(":")
        if len(parts) != 4:
            return
        user_id = int(parts[1])
        bet = int(parts[2])
        choice = parts[3]

        if query.from_user.id != user_id:
            await query.answer("⚠️ This is not your Color Trading session! Type /color [amount] to start your own.", show_alert=True)
            return

        try:
            result = await color_game.play(
                user_id, bet, choice, chat_id=query.message.chat.id
            )
            text = msgs.color_trade_result(
                result["bet"], result["bet_type"], result["selection"],
                result["drawn_number"], result["color_emoji"], result["color_name"],
                result["size_name"], result["won"], result["multiplier"],
                result["payout"], result.get("session_id", ""),
            )
            # Remove inline keyboard after choice is made to prevent multiple taps
            await edit_html(client, query.message, text, reply_markup=None)
            await query.answer()
        except Exception as e:
            await query.answer(f"⚠️ {e}", show_alert=True)

    @app.on_message(filters.command("bet") & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_bet(client: Client, message: Message):
        await ensure_user(client, message)
        bet, err = parse_amount_or_error(message.command[1] if len(message.command) > 1 else "")
        if err:
            await reply_html(client, message, msgs.error(f"Usage: <code>/bet amount</code>. {err}"))
            return
        result = await bet_game.play(message.from_user.id, bet, chat_id=message.chat.id)
        await reply_html(
            client, message,
            msgs.bet_result(result["bet"], result["won"], result["multiplier"], result["payout"], result["session_id"]),
        )

    @app.on_message(filters.command("mines") & NOT_CHANNEL)
    @safe_handler(feature="games")
    async def cmd_mines(client: Client, message: Message):
        await ensure_user(client, message)
        bet, err = parse_amount_or_error(message.command[1] if len(message.command) > 1 else "")
        if err:
            await reply_html(client, message, msgs.error(f"Usage: <code>/mines amount</code>. {err}"))
            return
        cfg = await mines_game.board_settings()
        session_id, state = await mines_game.start(
            message.from_user.id, bet, chat_id=message.chat.id
        )
        text = mines_game.game_header(
            bet,
            mines_game.multiplier_after(1, cfg["multipliers"]),
            mines_game.payout_for(bet, 1, cfg["multipliers"]),
            0,
        )
        text += f"\n<pre>{mines_game.render_board(state)}</pre>"
        sent = await reply_html(
            client, message, text,
            reply_markup=mines_game.board_keyboard(session_id, state),
        )
        if sent is not None:
            await games_db.bind_message(session_id, sent.id)

    @app.on_callback_query(filters.regex(rf"^{MINES_CB_PREFIX}"))
    async def cb_mines(client: Client, callback: CallbackQuery):
        parsed = _parse_mines_callback(callback.data)
        if parsed is None:
            await answer_callback(client, callback, "Invalid data.", show_alert=True)
            return
        session_id, action = parsed
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        message_id = callback.message.id
        try:
            if action == "cash":
                result = await mines_game.cashout(
                    session_id, user_id, chat_id=chat_id, message_id=message_id
                )
                session_doc = await games_db.get_session(session_id)
                bet = int(session_doc.get("bet", 0)) if session_doc else 0
                text = (
                    f"<b>💣 MINES — CASHED OUT</b>\n"
                    f"<blockquote>✅ Won: <b>{format_money(result['payout'])}</b>\n"
                    f"🧾 <code>#{session_id}</code></blockquote>\n"
                    f"<pre>{mines_game.render_board(result['state'], reveal_mines=True)}</pre>"
                )
                await edit_html(client, callback.message, text, reply_markup=None)
            else:
                tile = int(action)
                result = await mines_game.reveal(
                    session_id, user_id, tile, chat_id=chat_id, message_id=message_id
                )
                reveals = len(result["state"].get("revealed", []))
                if result["game_over"]:
                    if result["won"]:
                        text = (
                            f"<b>💣 MINES — COMPLETED</b>\n"
                            f"<blockquote>✅ Won: <b>{format_money(result['payout'])}</b>\n"
                            f"🧾 <code>#{session_id}</code></blockquote>\n"
                            f"<pre>{mines_game.render_board(result['state'], reveal_mines=True)}</pre>"
                        )
                    else:
                        session_doc = await games_db.get_session(session_id)
                        bet = int(session_doc.get("bet", 0)) if session_doc else 0
                        text = (
                            f"<b>💣 MINES — HIT A MINE</b>\n"
                            f"<blockquote>❌ Lost: {format_money(bet)}</blockquote>\n"
                            f"<pre>{mines_game.render_board(result['state'], reveal_mines=True)}</pre>"
                        )
                    await edit_html(client, callback.message, text, reply_markup=None)
                else:
                    session_doc = await games_db.get_session(session_id)
                    bet = int(session_doc.get("bet", 0)) if session_doc else 0
                    text = mines_game.game_header(
                        bet, result["multiplier"],
                        result["payout"], reveals,
                    )
                    text += f"\n<pre>{mines_game.render_board(result['state'])}</pre>"
                    await edit_html(
                        client, callback.message, text,
                        reply_markup=mines_game.board_keyboard(session_id, result["state"]),
                    )
            await answer_callback(client, callback, "Done.")
        except game_engine.NoActiveGame as exc:
            await answer_callback(client, callback, str(exc), show_alert=True)
        except game_engine.GameError as exc:
            await answer_callback(client, callback, str(exc), show_alert=True)
        except (ValueError, TypeError) as exc:
            logger.warning("bad mines callback %r: %s", callback.data, exc)
            await answer_callback(client, callback, "Invalid game data.", show_alert=True)
        except Exception as exc:  # noqa: BLE001
            logger.exception("mines callback crashed: %s", exc)
            await answer_callback(client, callback, "An error occurred.", show_alert=True)
