"""Armory & Weapons handlers: /guns, /armory, /myguns, /buygun."""

from __future__ import annotations

import logging

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import users as users_db
from handlers.common import ensure_user, safe_handler
from services import armory as armory_service
from utils import messages as msgs
from utils.money import format_money
from utils.sender import answer_callback, edit_html, reply_html

logger = logging.getLogger(__name__)

NOT_CHANNEL = ~filters.channel & ~filters.bot


def armory_keyboard(user_id: int, user_guns: list[str]) -> InlineKeyboardMarkup:
    all_guns = armory_service.get_all_guns()
    buttons = []

    row: list[InlineKeyboardButton] = []
    for gid, g in all_guns.items():
        is_owned = gid in user_guns
        short_name = g["name"].split()[0]
        if is_owned:
            label = f"✅ {short_name}"
            cb_data = f"armory:owned:{gid}"
        else:
            label = f"{g['emoji']} {short_name} ({format_money(g['price'])})"
            cb_data = f"armory:buy:{user_id}:{gid}"
        row.append(InlineKeyboardButton(label, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🎒 View My Arsenal", callback_data=f"armory:my:{user_id}"),
        InlineKeyboardButton("🔄 Refresh Store", callback_data=f"armory:store:{user_id}"),
    ])
    return InlineKeyboardMarkup(buttons)


def register(app: Client) -> None:
    @app.on_message(filters.command(["guns", "gun", "armory", "gunshop", "weapons"]) & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_guns(client: Client, message: Message):
        await ensure_user(client, message)
        user_id = message.from_user.id
        all_guns = armory_service.get_all_guns()
        user_guns = await armory_service.get_user_guns(user_id)

        text = msgs.armory_catalog(all_guns, user_guns)
        keyboard = armory_keyboard(user_id, user_guns)
        await reply_html(client, message, text, reply_markup=keyboard)

    @app.on_message(filters.command(["myguns", "myarmory", "arsenal"]) & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_my_guns(client: Client, message: Message):
        await ensure_user(client, message)
        user_id = message.from_user.id
        user_doc = await users_db.get_user(user_id)
        all_guns = armory_service.get_all_guns()
        user_guns = await armory_service.get_user_guns(user_id)

        text = msgs.armory_inventory(user_doc, all_guns, user_guns)
        await reply_html(client, message, text)

    @app.on_message(filters.command("buygun") & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_buy_gun(client: Client, message: Message):
        await ensure_user(client, message)
        if len(message.command) < 2:
            await reply_html(
                client, message,
                msgs.error("Usage: <code>/buygun ak47|awp|deagle|glock|m4a1|minigun</code> or use <code>/guns</code> for inline shop."),
            )
            return
        gun_id = message.command[1].lower().strip()
        result = await armory_service.buy_gun(message.from_user.id, gun_id)
        text = msgs.gun_purchased(result["gun"], result["price"], result["tx_id"])
        await reply_html(client, message, text)

    @app.on_callback_query(filters.regex(r"^armory:"))
    async def cb_armory(client: Client, query: CallbackQuery):
        parts = query.data.split(":")
        action = parts[1]

        if action == "owned":
            await answer_callback(client, query, "✅ You already own and have equipped this firearm!", alert=True)
            return

        user_id = int(parts[2])
        if query.from_user.id != user_id:
            await answer_callback(client, query, "⚠️ This is not your armory session!", alert=True)
            return

        if action == "buy":
            gun_id = parts[3]
            try:
                result = await armory_service.buy_gun(user_id, gun_id)
                text = msgs.gun_purchased(result["gun"], result["price"], result["tx_id"])
                user_guns = await armory_service.get_user_guns(user_id)
                kb = armory_keyboard(user_id, user_guns)
                await edit_html(client, query.message, text, reply_markup=kb)
                await answer_callback(client, query, f"🎉 Successfully equipped {result['gun']['name']}!")
            except Exception as e:
                await answer_callback(client, query, str(e), alert=True)

        elif action == "my":
            user_doc = await users_db.get_user(user_id)
            all_guns = armory_service.get_all_guns()
            user_guns = await armory_service.get_user_guns(user_id)
            text = msgs.armory_inventory(user_doc, all_guns, user_guns)
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back to Armory Store", callback_data=f"armory:store:{user_id}")]])
            await edit_html(client, query.message, text, reply_markup=kb)
            await answer_callback(client, query)

        elif action == "store":
            all_guns = armory_service.get_all_guns()
            user_guns = await armory_service.get_user_guns(user_id)
            text = msgs.armory_catalog(all_guns, user_guns)
            kb = armory_keyboard(user_id, user_guns)
            await edit_html(client, query.message, text, reply_markup=kb)
            await answer_callback(client, query)
