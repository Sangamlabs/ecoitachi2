"""Centralized HTML message builders.

Every user-facing Telegram message is built here as valid Telegram HTML and
sent through :mod:`utils.sender` with ``parse_mode=HTML``.  Dynamic content is
HTML-escaped before insertion.

Message content is kept separate from the send logic so future features
(e.g. wrapping cards in ``<blockquote>``) can be applied globally.
"""

from __future__ import annotations

import math
import time
from html import escape
from typing import Any

from utils.formatting import font_style, tg_link
from utils.money import format_money

CMD = font_style("Uno Itachi Economy")
OWNER_EMOJI = {1: "🥇", 2: "🥈", 3: "🥉"}


def _user_name(user: dict[str, Any]) -> str:
    if user.get("username"):
        return f"@{escape(user['username'])}"
    return escape(user.get("first_name") or "Unknown")


def _link(user_id: int, name: str) -> str:
    return tg_link(user_id, escape(name))


def success(text: str) -> str:
    return f"<b>✅ {text}</b>"


def error(text: str) -> str:
    return f"<b>❌ {text}</b>"


def warning(text: str) -> str:
    return f"<b>⚠️ {text}</b>"


def info(text: str) -> str:
    return f"<b>ℹ️ {text}</b>"


def start(user: dict[str, Any]) -> str:
    name = _user_name(user)
    return (
        f"<b>💰 {CMD}</b>\n\n"
        f"<blockquote>Welcome, <b>{name}</b>! You have joined the economy system.</blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Market & Banking')}:</b> Work, trade assets, invest in stocks and bank earnings.\n"
        f"🎁 <b>{font_style('Free Currency')}:</b> Claim <code>/daily</code>, <code>/weekly</code>, <code>/monthly</code>.</blockquote>\n"
        f"<blockquote>💡 <i>Use <code>/help</code> to explore all games and commands.</i></blockquote>"
    )


def balance(user: dict[str, Any], target: dict[str, Any]) -> str:
    name = _link(target["user_id"], _user_name(target))
    net = user.get("wallet", 0) + user.get("bank", 0)
    title = font_style("Balance Summary")
    return (
        f"<b>💰 {title}</b>\n"
        f"<blockquote>👤 <b>{font_style('User')}:</b> {name}\n"
        f"🆔 <b>{font_style('ID')}:</b> <code>{target['user_id']}</code></blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Wallet')}:</b> {format_money(user.get('wallet', 0))}\n"
        f"🏦 <b>{font_style('Bank')}:</b> {format_money(user.get('bank', 0))}</blockquote>\n"
        f"<blockquote>💎 <b>{font_style('Net Worth')}:</b> <b>{format_money(net)}</b></blockquote>"
    )


def profile(user: dict[str, Any]) -> str:
    rank = user.get("monthly_rank") or "—"
    stocks_value = user.get("stocks_value", 0)
    asset_value = user.get("asset_value", 0)
    net = user.get("wallet", 0) + user.get("bank", 0) + stocks_value + asset_value
    name = _user_name(user)
    if user.get("username"):
        ident_line = f"🆔 <b>{font_style('Username')}:</b> @{escape(user['username'])}"
    else:
        ident_line = f"🆔 <b>{font_style('User ID')}:</b> <code>{user['user_id']}</code>"
    return (
        f"<b>👤 {font_style('User Profile')}</b>\n"
        f"<blockquote>👤 <b>{font_style('Name')}:</b> {name}\n"
        f"{ident_line}</blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Wallet')}:</b> {format_money(user.get('wallet', 0))}\n"
        f"🏦 <b>{font_style('Bank')}:</b> {format_money(user.get('bank', 0))}\n"
        f"💎 <b>{font_style('Net Worth')}:</b> <b>{format_money(net)}</b></blockquote>\n"
        f"<blockquote>📈 <b>{font_style('Stocks')}:</b> {format_money(stocks_value)}\n"
        f"🏠 <b>{font_style('Assets')}:</b> {format_money(asset_value)}\n"
        f"🏆 <b>{font_style('Rank')}:</b> <b>{rank}</b></blockquote>"
    )


def payment(sender: dict[str, Any], receiver: dict[str, Any], amount: int, tx_id: str) -> str:
    return (
        f"<b>💸 {font_style('Payment Sent')}</b>\n"
        f"<blockquote>👤 <b>{font_style('Recipient')}:</b> {_link(receiver['user_id'], _user_name(receiver))}\n"
        f"💵 <b>{font_style('Amount')}:</b> <b>{format_money(amount)}</b></blockquote>\n"
        f"<blockquote>🧾 <b>{font_style('Transaction')}:</b> <code>#{tx_id}</code></blockquote>"
    )


def payment_received(sender: dict[str, Any], amount: int) -> str:
    return (
        f"<b>💸 {font_style('Payment Received')}</b>\n"
        f"<blockquote>👤 {_link(sender['user_id'], _user_name(sender))} sent you <b>{format_money(amount)}</b>.</blockquote>"
    )


def leaderboard(entries: list[tuple[int, str, int]]) -> str:
    title = font_style("Richest Leaderboard")
    top_block: list[str] = []
    rest_block: list[str] = []
    for idx, (user_id, name, net_worth) in enumerate(entries, start=1):
        medal = OWNER_EMOJI.get(idx, "")
        prefix = f"{medal} " if medal else f"<code>{idx:02d}</code>. "
        line = f"{prefix}{_link(user_id, escape(name))} — <b>{format_money(net_worth)}</b>"
        if idx <= 3:
            top_block.append(line)
        else:
            rest_block.append(line)

    res = [f"<b>🏆 {title}</b>"]
    if top_block:
        res.append("<blockquote>" + "\n".join(top_block) + "</blockquote>")
    if rest_block:
        res.append("<blockquote>" + "\n".join(rest_block) + "</blockquote>")
    return "\n".join(res)


def bank(user: dict[str, Any], settings: dict[str, Any], tax_pool: int) -> str:
    rate = settings.get("interest_rate", 2.0)
    interval = settings.get("interest_interval_hours", 24)
    tax = settings.get("withdrawal_tax_rate", 5.0)
    return (
        f"<b>🏦 {font_style('Central Bank')}</b>\n"
        f"<blockquote>💵 <b>{font_style('Bank Balance')}:</b> {format_money(user.get('bank', 0))}\n"
        f"💰 <b>{font_style('Wallet')}:</b> {format_money(user.get('wallet', 0))}</blockquote>\n"
        f"<blockquote>📈 <b>{font_style('Interest Rate')}:</b> <b>{rate}%</b> / {interval}h\n"
        f"🧾 <b>{font_style('Withdrawal Tax')}:</b> <b>{tax}%</b>\n"
        f"🏛️ <b>{font_style('Tax Pool')}:</b> {format_money(tax_pool)}</blockquote>\n"
        f"<blockquote><i>💡 Use <code>/deposit</code> and <code>/withdraw</code> to manage funds.</i></blockquote>"
    )


def help_text() -> str:
    return (
        f"<b>📖 {CMD} — {font_style('Help & Commands Manual')}</b>\n\n"
        f"<blockquote>👤 <b>{font_style('Economy & Profile')}</b>\n"
        f"• <code>/bal</code> [user] — wallet & bank balance\n"
        f"• <code>/networth</code> (or <code>/nw</code>) — net worth breakdown\n"
        f"• <code>/pay @user amount</code> — send money (accepts <code>500k</code>, <code>1.5M</code>)\n"
        f"• <code>/rich</code> (or <code>/top</code>) — top richest tycoons\n"
        f"• <code>/profile</code> — full financial identity</blockquote>\n\n"
        f"<blockquote>🏦 <b>{font_style('Central Banking & Loans')}</b>\n"
        f"• <code>/deposit amount</code> — wallet → bank\n"
        f"• <code>/withdraw amount</code> — bank → wallet (tax applies)\n"
        f"• <code>/bank</code> — central bank status & interest\n"
        f"• <code>/loan [amount]</code> — borrow money from central bank\n"
        f"• <code>/repay [amount]</code> — repay your active loan\n"
        f"• <code>/interestbank</code> / <code>/interestasset</code> / <code>/stockinterest</code> — claim 24h yields\n"
        f"• <code>/transactions</code> — last 10 transaction receipts</blockquote>\n\n"
        f"<blockquote>🎮 <b>{font_style('Casino & Gambling')}</b>\n"
        f"• <code>/color big|small|red|green|0-9 amount</code> — Color Trading (up to 9x)\n"
        f"• <code>/satta [bet] [amount]</code> — Indian Satta Matka (up to 90x jackpot!)\n"
        f"• <code>/cf heads|tails amount</code> — coin flip (2x payout)\n"
        f"• <code>/roul red|black|green|0-36 amount</code> — roulette (up to 36x)\n"
        f"• <code>/mines amount</code> — minesweeper cash-out board\n"
        f"• <code>/fly low|medium|high amount</code> — crash rocket game\n"
        f"• <code>/bet amount</code> — 50/50 dice gamble\n"
        f"• <code>/blackjack amount</code> — card table vs bot dealer\n"
        f"• <code>/rob @user</code> — stealth robbery attempt</blockquote>\n\n"
        f"<blockquote>🎳 <b>{font_style('Emoji Duel Arenas')}</b>\n"
        f"• <code>/sball</code> / <code>/sarrow</code> / <code>/sbasketball</code> amount — solo emoji games\n"
        f"• <code>/ball</code> / <code>/arrow</code> / <code>/basketball</code> amount — 1v1 PvP duel\n"
        f"• <code>/join CODE</code> — join open duel lobby</blockquote>\n\n"
        f"<blockquote>📈 <b>{font_style('Markets & Armory')}</b>\n"
        f"• <code>/guns</code> (or <code>/armory</code>) — black market gun store\n"
        f"• <code>/myguns</code> (or <code>/arsenal</code>) — view your equipped weapons\n"
        f"• <code>/stocklist</code> / <code>/portfolio</code> / <code>/buystock</code> / <code>/sellstock</code>\n"
        f"• <code>/assets</code> / <code>/myassets</code> / <code>/buyasset</code> / <code>/sellasset</code>\n"
        f"• <code>/listings</code> / <code>/listasset</code> / <code>/buylisting</code></blockquote>\n\n"
        f"<blockquote>🎁 <b>{font_style('Daily Rewards & Free Grants')}</b>\n"
        f"• <code>/daily</code> / <code>/weekly</code> / <code>/monthly</code> — free claims\n"
        f"💡 <i>Tip: You can use short amounts like <code>100k</code>, <code>2.5m</code>, <code>1b</code>, <code>1t</code>!</i></blockquote>"
    )


def income_claim(source: str, result: dict[str, Any]) -> str:
    """Reply for /interestbank, /interestasset and /stockinterest."""
    emoji = {
        "bank": "🏦",
        "asset": "🏠",
        "stock": "📈",
    }.get(source, "💰")
    labels = {
        "bank": font_style("Bank Daily Interest"),
        "asset": font_style("Asset Daily Income"),
        "stock": font_style("Stock Market Yield"),
    }
    label = labels.get(source, font_style(source.upper()))
    amount = int(result.get("amount", 0))
    value = int(result.get("value", 0))
    rate = float(result.get("rate", 0.0))
    days = int(result.get("days", 0))

    if result.get("already_claimed"):
        return f"<b>{emoji} {label}</b>\n<blockquote>⚠️ <i>{font_style('You already claimed today — next claim available in 24h')}.</i></blockquote>"

    if result.get("started"):
        return (
            f"<b>{emoji} {label}</b>\n"
            f"<blockquote>📈 <b>{font_style('Tracking Started')}</b>\n"
            f"💰 <b>{font_style('Holding Base')}:</b> {format_money(value)}\n"
            f"📊 <b>{font_style('Daily Rate')}:</b> <b>{rate}%</b> / 24h</blockquote>\n"
            f"<blockquote>⏳ <i>{font_style('Check back in 24h to claim your returns')}.</i></blockquote>"
        )

    if amount <= 0:
        wait = int(result.get("next_in", 86_400))
        hours = max(1, wait // 3600)
        return (
            f"<b>{emoji} {label}</b>\n"
            f"<blockquote>💰 <b>{font_style('Holding Base')}:</b> {format_money(value)}\n"
            f"📊 <b>{font_style('Rate')}:</b> <b>{rate}%</b> / 24h</blockquote>\n"
            f"<blockquote>⏳ <i>{font_style('Next claim available in')} ~{hours}h.</i></blockquote>"
        )

    return (
        f"<b>{emoji} {label}</b>\n"
        f"<blockquote>💵 <b>{font_style('Claimed Earnings')}:</b> <b>{format_money(amount)}</b>\n"
        f"📅 <b>{font_style('Accrued Days')}:</b> {days}</blockquote>\n"
        f"<blockquote>💰 <b>{font_style('Base')}:</b> {format_money(value)} · 📊 <b>{font_style('Rate')}:</b> <b>{rate}%</b> / 24h</blockquote>\n"
        f"<blockquote><i>💡 {font_style('Credited directly to your wallet')}.</i></blockquote>"
    )


def transaction_row(tx: dict[str, Any]) -> str:
    direction = tx.get("metadata", {}).get("direction")
    if tx.get("type") == "PAY" and direction == "in":
        sign, label = "←", "RECEIVED"
    elif tx.get("type") == "PAY":
        sign, label = "→", "SENT"
    else:
        sign = {"GAME_LOSS": "−", "ADMIN_REMOVE": "−", "STOCK_BUY": "−",
                "WITHDRAW": "−", "TAX": "−", "ROBBED": "−"}.get(tx.get("type", ""), "＋")
        label = tx.get("type", "UNKNOWN")
    amount = tx.get("amount", 0)
    return (
        f"<code>{escape(label)}</code> {sign} "
        f"<b>{format_money(amount)}</b> · <code>#{tx.get('transaction_id', '')[:10]}</code>"
    )


def transactions_list(rows: list[str], empty: bool) -> str:
    title = font_style("Transaction History")
    if empty:
        return f"<b>🧾 {title}</b>\n<blockquote><i>{font_style('No transactions recorded yet')}.</i></blockquote>"
    return f"<b>🧾 {title}</b>\n<blockquote>" + "\n".join(rows) + "</blockquote>"


def stock_list(assets: list[dict[str, Any]]) -> str:
    title = font_style("Stock Market Overview")
    lines = [f"<b>📈 {title}</b>", "<blockquote>"]
    for a in assets:
        arrow = "▲" if a.get("change_percent", 0) >= 0 else "▼"
        lines.append(
            f"<code>{escape(a['symbol'])}</code> "
            f"<b>{format_money(a.get('price', 0))}</b> "
            f"{arrow} {abs(a.get('change_percent', 0)):.2f}%"
        )
    lines.append("</blockquote>")
    lines.append(f"<blockquote><i>💡 {font_style('Use /buystock SYMBOL qty to invest')}</i></blockquote>")
    return "\n".join(lines)


def stock_detail(asset: dict[str, Any]) -> str:
    arrow = "▲" if asset.get("change_percent", 0) >= 0 else "▼"
    return (
        f"<b>📈 {font_style(asset['symbol'])} — {escape(asset.get('name', ''))}</b>\n"
        f"<blockquote>💵 <b>{font_style('Current Price')}:</b> <b>{format_money(asset.get('price', 0))}</b> {arrow} {asset.get('change_percent', 0):.2f}%</blockquote>\n"
        f"<blockquote>📊 <b>24h High:</b> {format_money(asset.get('high_price', 0))}\n"
        f"📉 <b>24h Low:</b> {format_money(asset.get('low_price', 0))}\n"
        f"📈 <b>{font_style('Volatility')}:</b> {asset.get('volatility', 0):.1%}</blockquote>"
    )


def stock_trade(action: str, symbol: str, qty: float, total: int, tx_id: str) -> str:
    verb = font_style("Shares Purchased") if action == "buy" else font_style("Shares Sold")
    return (
        f"<b>✅ {verb} — {escape(symbol)}</b>\n"
        f"<blockquote>🔢 <b>{font_style('Quantity')}:</b> <b>{qty}</b>\n"
        f"💵 <b>{font_style('Total Value')}:</b> <b>{format_money(total)}</b></blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def portfolio(rows: list[str], total_value: int, total_cost: int) -> str:
    pnl = total_value - total_cost
    sign = "+" if pnl >= 0 else ""
    title = font_style("Stocks Portfolio")
    return (
        f"<b>📊 {title}</b>\n"
        f"<blockquote>" + "\n".join(rows) + "</blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Total Stock Value')}:</b> <b>{format_money(total_value)}</b>\n"
        f"📈 <b>{font_style('Total P/L')}:</b> <b>{sign}{format_money(pnl)}</b></blockquote>"
    )


def fly_result(difficulty: str, bet: int, won: bool, multiplier: float, payout: int, tx_id: str) -> str:
    head = f"✈️ {font_style('Fly Multiplier Game')}" if won else f"💥 {font_style('Plane Crashed')}"
    if won:
        outcome = f"✅ <b>{font_style('You Won')}!</b> <b>{format_money(payout)}</b> ({multiplier:.2f}x)"
    else:
        outcome = f"❌ <b>{font_style('Crash Loss')}!</b> {format_money(bet)}"
    return (
        f"<b>{head}</b>\n"
        f"<blockquote>🎯 <b>{font_style('Difficulty')}:</b> {escape(difficulty.title())}\n"
        f"💰 <b>{font_style('Bet Amount')}:</b> {format_money(bet)}</blockquote>\n"
        f"<blockquote>{outcome}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def bet_result(bet: int, won: bool, multiplier: float, payout: int, tx_id: str) -> str:
    result = (
        f"✅ <b>{font_style('You Won')}!</b> <b>{format_money(payout)}</b> ({multiplier:.2f}x)"
        if won
        else f"❌ <b>{font_style('You Lost')}!</b> {format_money(bet)}"
    )
    return (
        f"<b>🎲 {font_style('Dice Gamble')}</b>\n"
        f"<blockquote>💰 <b>{font_style('Bet')}:</b> {format_money(bet)}</blockquote>\n"
        f"<blockquote>{result}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def coinflip_result(
    bet: int, picked: str, flipped: str, won: bool, multiplier: float, payout: int, tx_id: str
) -> str:
    picked_str = font_style("Heads") + " (👑)" if picked == "heads" else font_style("Tails") + " (🦅)"
    flipped_str = font_style("Heads") + " (👑)" if flipped == "heads" else font_style("Tails") + " (🦅)"
    if won:
        res = f"✅ <b>{font_style('You Won')}!</b> <b>{format_money(payout)}</b> ({multiplier:.2f}x)"
    else:
        res = f"❌ <b>{font_style('You Lost')}!</b> {format_money(bet)}"

    return (
        f"<b>🪙 {font_style('Coin Flip Challenge')}</b>\n"
        f"<blockquote>🎯 <b>{font_style('Your Choice')}:</b> {picked_str}\n"
        f"🪙 <b>{font_style('Coin Landed')}:</b> {flipped_str}</blockquote>\n"
        f"<blockquote>{res}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def roulette_result(
    bet: int, selection: str, landed_number: int, landed_color: str, landed_emoji: str,
    won: bool, multiplier: float, payout: int, tx_id: str
) -> str:
    if won:
        res = f"✅ <b>{font_style('Jackpot Win')}!</b> <b>{format_money(payout)}</b> ({multiplier:.1f}x)"
    else:
        res = f"❌ <b>{font_style('No Match')}!</b> {format_money(bet)}"

    return (
        f"<b>🎡 {font_style('European Roulette')}</b>\n"
        f"<blockquote>🎯 <b>{font_style('Your Bet')}:</b> {escape(selection.upper())}\n"
        f"📍 <b>{font_style('Outcome')}:</b> {landed_emoji} <b>{landed_number} ({landed_color.upper()})</b></blockquote>\n"
        f"<blockquote>{res}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def satta_result(
    bet: int, bet_type: str, selection: str, drawn_number: str, open_digit: int,
    close_digit: int, sum_digit: int, won: bool, multiplier: float, payout: int, tx_id: str
) -> str:
    title = font_style("Satta Matka Jackpot")
    if won:
        if bet_type == "jodi":
            outcome = f"👑 <b>{font_style('Jackpot Jodi Win')}!</b> <b>{format_money(payout)}</b> (90.0x)"
        elif bet_type == "single":
            outcome = f"✅ <b>{font_style('Haruf Single Win')}!</b> <b>{format_money(payout)}</b> (9.0x)"
        else:
            outcome = f"✅ <b>{font_style('You Won')}!</b> <b>{format_money(payout)}</b> ({multiplier:.1f}x)"
    else:
        outcome = f"❌ <b>{font_style('No Match')}!</b> Lost: {format_money(bet)}"

    return (
        f"<b>🎰 {title}</b>\n"
        f"<blockquote>🎯 <b>{font_style('Your Bet')}:</b> <b>{escape(selection.upper())}</b> ({bet_type.title()})\n"
        f"🎲 <b>{font_style('Satta Draw')}:</b> <b>[{open_digit} + {close_digit} = {sum_digit}] ➔ {drawn_number}</b></blockquote>\n"
        f"<blockquote>{outcome}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def color_trade_result(
    bet: int, bet_type: str, selection: str, drawn_number: int,
    color_emoji: str, color_name: str, size_name: str,
    won: bool, multiplier: float, payout: int, tx_id: str
) -> str:
    title = font_style("Color Trading & Big-Small")
    if won:
        outcome = f"✅ <b>{font_style('Prediction Success')}!</b> <b>{format_money(payout)}</b> ({multiplier:.1f}x)"
    else:
        outcome = f"❌ <b>{font_style('Prediction Failed')}!</b> Lost: {format_money(bet)}"

    return (
        f"<b>🎨 {title}</b>\n"
        f"<blockquote>🎯 <b>{font_style('Your Prediction')}:</b> <b>{escape(selection.upper())}</b> ({bet_type.title()})\n"
        f"🎲 <b>{font_style('Win Go Outcome')}:</b> {color_emoji} <b>Number {drawn_number}</b> · {color_name} · {size_name}</blockquote>\n"
        f"<blockquote>{outcome}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def format_duration(seconds: int) -> str:
    """Human-readable countdown timer, e.g. 90 -> '1m 30s', 3725 -> '1h 2m 5s'."""
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86_400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def game_cooldown(game: str, remaining: int) -> str:
    return (
        f"<b>⏳ {font_style(game.title())} is on cooldown.</b>\n"
        f"<blockquote><i>Try again in <b>{format_duration(remaining)}</b>.</i></blockquote>"
    )


def reward_claimed(kind: str, amount: int, cooldown: int) -> str:
    title = font_style(f"{kind.title()} Reward")
    return (
        f"<b>🎁 {title}</b>\n"
        f"<blockquote>💵 <b>{font_style('Claimed')}:</b> <b>{format_money(amount)}</b></blockquote>\n"
        f"<blockquote>⏳ <b>{font_style('Next Claim')}:</b> in {format_duration(cooldown)}</blockquote>"
    )


def rob_result(result: dict[str, Any], robber: dict[str, Any], victim: dict[str, Any]) -> str:
    victim_name = _user_name(victim)
    next_rob = format_duration(result.get("cooldown", 0))
    if result["success"]:
        return (
            f"<b>🦹 ROBBERY SUCCESS</b>\n"
            f"<blockquote>You stole <b>{format_money(result['stolen'])}</b> from {victim_name}.\n"
            f"They had {format_money(result['target_bank_before'])} banked.</blockquote>\n"
            f"<i>Next robbery in {next_rob}.</i>"
        )
    return (
        f"<b>🚔 ROBBERY FAILED</b>\n"
        f"<blockquote>The police caught you robbing {victim_name}.\n"
        f"You got nothing.</blockquote>\n"
        f"<i>Next robbery in {next_rob}.</i>"
    )


def robbery_notice(victim: dict[str, Any], robber: dict[str, Any], stolen: int) -> str:
    return (
        f"<b>🦹 YOU WERE ROBBED</b>\n"
        f"{_link(robber['user_id'], _user_name(robber))} stole "
        f"<b>{format_money(stolen)}</b> from your bank!"
    )


def admin_help() -> str:
    return (
        f"<b>🛠 {CMD} — ADMIN HELP</b>\n"
        f"<i>Owner + sudo admins only.</i>\n\n"
        f"<b>🛡 Permissions</b>\n"
        f"<code>/addsudo @user</code> — add sudo (owner only)\n"
        f"<code>/rsudo @user</code> — remove sudo (owner only)\n\n"
        f"<b>💰 Economy</b>\n"
        f"<code>/give @user amount</code> — give money\n"
        f"<code>/remove @user amount</code> — take money\n"
        f"<code>/getcoin amount</code> — credit yourself coins\n\n"
        f"<b>🏦 Bank</b>\n"
        f"<code>/setinterest rate</code> — interest % per 24h\n"
        f"<code>/settax rate</code> — withdrawal tax %\n"
        f"<code>/banksettings</code> — view bank settings\n"
        f"<code>/dtax</code> — manually distribute the tax pool now\n"
        f"<code>/addtax system rate</code> — tax % for a system's transactions\n"
        f"<code>/taxinfo</code> — all tax rates + pool\n"
        f"<code>/track TX_ID</code> — full transaction detail\n\n"
        f"<b>💰 Daily Income</b>\n"
        f"<code>/setincome bank|asset|stock rate</code> — daily income % per 24h\n\n"
        f"<b>🎮 Games</b>\n"
        f"<code>/flyset low|medium|high field value</code>\n"
        f"<code>/flytrap difficulty 8 values</code>\n"
        f"<code>/betset win_prob multiplier min_bet max_bet [cooldown]</code>\n"
        f"<code>/minestrap ...</code> — mines tuning\n"
        f"<code>/robset field value</code> — rob tuning\n\n"
        f"<b>🎳 Emoji Games</b>\n"
        f"<code>/emojiset GAME field value</code> — one field at a time\n"
        f"<code>/emojitrap GAME key=value ...</code> — bulk set\n"
        f"<code>/emojigameinfo GAME</code> — current config\n"
        f"<code>/emojigames</code> — overview of all emoji games\n"
        f"<code>/bjset field value</code> — blackjack config\n"
        f"<code>/bjinfo</code> — blackjack config\n"
        f"<i>Fields: cooldown, min_bet, max_bet, multiplier, rule, target, "
        f"single, duel, enabled, expiry.</i>\n\n"
        f"<b>📈 Stock Market</b>\n"
        f"<code>/addstock SYMBOL name price volatility</code> — list a stock\n"
        f"<code>/rmstock SYMBOL</code> — delist a stock\n\n"
        f"<b>🏠 Asset Market</b>\n"
        f"<code>/addasset SYMBOL name CATEGORY price volatility</code> — list an asset\n"
        f"<code>/editasset SYMBOL field value</code> — edit asset fields\n"
        f"<code>/assetset SYMBOL field value</code> — asset config\n"
        f"<code>/assetprice SYMBOL price</code> — manual price set\n"
        f"<code>/assetvolatility SYMBOL v</code> — volatility set\n"
        f"<code>/rmasset SYMBOL</code> — delist\n"
        f"<code>/restoreasset SYMBOL</code> — relist\n"
        f"<code>/assetinfo SYMBOL</code> / <code>/assetlist [page]</code>\n"
        f"<code>/assetsearch query</code> — search assets\n"
        f"<code>/assetowners SYMBOL [page]</code> — top holders\n"
        f"<code>/assetadminstats</code> — market admin stats\n"
        f"<code>/listinginfo LISTING_ID</code> — listing details\n"
        f"<code>/forcelisting LISTING_ID</code> — force-cancel any listing\n\n"
        f"<b>🎁 Rewards</b>\n"
        f"<code>/setreward daily|weekly|monthly amount</code>\n\n"
        f"<b>🎁 Promo Codes</b>\n"
        f"<code>/addpromo CODE EXPIRY LIMIT REWARD [REWARD...]</code> — create\n"
        f"<code>/rmpromo CODE</code> — disable (history kept)\n"
        f"<code>/editpromo CODE FIELD VALUE [VALUE...]</code> — expiry|limit|active|reward\n"
        f"<code>/promoinfo CODE</code> / <code>/promolist [status] [page]</code>\n"
        f"<code>/promostats CODE</code> — redemption statistics\n"
        f"<i>Rewards: rs:AMOUNT, stock:SYMBOL:QTY, asset:ASSET_ID:QTY. Expiry: "
        f"lifetime or a number + min/hr/day/week/month/year.</i>\n\n"
        f"<b>👥 Users</b>\n"
        f"<code>/freeze @user</code> / <code>/unfreeze @user</code>\n"
        f"<code>/ban @user</code> / <code>/unban @user</code>\n"
        f"<code>/userinfo @user</code> — user details\n\n"
        f"<b>⚙️ Group config</b>\n"
        f"<code>/setchat [chat_id] [setting] [on|off]</code>\n\n"
        f"<b>📊 Stats</b>\n"
        f"<code>/econstats</code> — economy stats"
    )


def admin_stats(stats: dict[str, Any]) -> str:
    title = font_style("Central Economy Analytics")
    return (
        f"<b>📊 {title}</b>\n"
        f"<blockquote>👥 <b>{font_style('Active Citizens')}:</b> <b>{stats['users']}</b>\n"
        f"🧾 <b>{font_style('Ledger Transactions')}:</b> <b>{stats['transactions']}</b></blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Circulating Currency')}:</b> {format_money(stats['total_wallet'])}\n"
        f"🏦 <b>{font_style('Total Bank Vault')}:</b> {format_money(stats['total_bank'])}</blockquote>\n"
        f"<blockquote>🏛️ <b>{font_style('Federal Tax Pool')}:</b> <b>{format_money(stats['tax_pool'])}</b>\n"
        f"📈 <b>{font_style('Live Market Stocks')}:</b> <b>{stats['stocks']}</b></blockquote>"
    )


def tx_track_detail(tx: dict[str, Any]) -> str:
    """Full audit detail for one transaction (used by /track)."""
    meta = tx.get("metadata") or {}
    meta_lines = [
        f"<code>{escape(str(k))}</code>: <b>{escape(str(v))}</b>"
        for k, v in meta.items()
    ]
    title = font_style("Transaction Audit Tracker")
    return (
        f"<b>🧾 {title}</b>\n"
        f"<blockquote>🆔 <b>{font_style('Tx ID')}:</b> <code>#{tx.get('transaction_id', '')}</code>\n"
        f"👤 <b>{font_style('User')}:</b> <code>{tx.get('user_id', '')}</code>\n"
        f"📦 <b>{font_style('Category')}:</b> <b>{escape(str(tx.get('type', '')))}</b></blockquote>\n"
        f"<blockquote>💰 <b>{font_style('Amount')}:</b> <b>{format_money(int(tx.get('amount', 0)))}</b>\n"
        f"💵 <b>{font_style('Pre-Balance')}:</b> {format_money(int(tx.get('balance_before', 0)))}\n"
        f"💵 <b>{font_style('Post-Balance')}:</b> {format_money(int(tx.get('balance_after', 0)))}</blockquote>"
        + ("\n<blockquote>📎 <b>Metadata:</b>\n" + "\n".join(meta_lines) + "</blockquote>" if meta_lines else "")
    )


def taxinfo(taxes: dict[str, Any], pool: int, bank_settings: dict[str, Any]) -> str:
    """Admin view of every per-system tax rate + tax pool size."""
    rows = [f"• <code>{k}</code>: <b>{v}%</b>" for k, v in taxes.items()]
    bank_rate = bank_settings.get("withdrawal_tax_rate", 5.0)
    title = font_style("Federal Tax System Overview")
    return (
        f"<b>🏛️ {title}</b>\n"
        f"<blockquote>💰 <b>{font_style('Central Tax Pool')}:</b> <b>{format_money(pool)}</b>\n"
        f"🏦 <b>{font_style('Withdrawal Tax')}:</b> <b>{bank_rate}%</b></blockquote>\n"
        f"<blockquote>📊 <b>{font_style('Sector Tax Rates')}:</b>\n" + "\n".join(rows) + "</blockquote>"
    )


def tax_distribution(result: dict[str, Any]) -> str:
    """Report for a manual /dtax (or monthly) tax pool distribution."""
    rows = [
        f"<code>#{r['rank']}</code> · User <code>{r['user_id']}</code> — <b>{format_money(r['amount'])}</b>"
        for r in result.get("results", [])
    ]
    title = font_style("Tax Pool Monthly Dividend")
    return (
        f"<b>🏛️ {title}</b>\n"
        f"<blockquote>💰 <b>{font_style('Total Pool')}:</b> {format_money(result['pool'])}\n"
        f"💸 <b>{font_style('Distributed')}:</b> <b>{format_money(result['distributed'])}</b>\n"
        f"👥 <b>{font_style('Beneficiaries')}:</b> {len(result.get('results', []))}</blockquote>\n"
        f"<blockquote>" + "\n".join(rows) + "</blockquote>"
    )


def userinfo(user: dict[str, Any], stats: dict[str, Any]) -> str:
    name = _user_name(user)
    net = (
        user.get("wallet", 0)
        + user.get("bank", 0)
        + user.get("stocks_value", 0)
        + user.get("asset_value", 0)
    )
    badges = []
    if user.get("is_banned"):
        badges.append("<s>BANNED</s>")
    if user.get("is_frozen"):
        badges.append("<s>FROZEN</s>")
    badge_text = " " + " ".join(badges) if badges else ""
    title = font_style("Citizen dossier")
    return (
        f"<b>👤 {title}</b>{badge_text}\n"
        f"<blockquote>👤 {_link(user['user_id'], name)} (<code>{user['user_id']}</code>)</blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Wallet')}:</b> {format_money(user.get('wallet', 0))}\n"
        f"🏦 <b>{font_style('Bank')}:</b> {format_money(user.get('bank', 0))}\n"
        f"💎 <b>{font_style('Net Worth')}:</b> <b>{format_money(net)}</b></blockquote>\n"
        f"<blockquote>📈 <b>{font_style('Stocks')}:</b> {format_money(user.get('stocks_value', 0))}\n"
        f"🏠 <b>{font_style('Assets')}:</b> {format_money(user.get('asset_value', 0))}</blockquote>\n"
        f"<blockquote>🏆 <b>{font_style('Monthly Rank')}:</b> <b>{user.get('monthly_rank') or '—'}</b>\n"
        f"🧾 <b>{font_style('Transactions')}:</b> {stats['transactions']}</blockquote>"
    )


def banksettings(settings: dict[str, Any], tax_pool: int) -> str:
    title = font_style("Banking Policy & Rates")
    return (
        f"<b>🏦 {title}</b>\n"
        f"<blockquote>📈 <b>{font_style('Daily Interest')}:</b> <b>{settings.get('interest_rate', 2.0)}%</b> / {settings.get('interest_interval_hours', 24)}h\n"
        f"🧾 <b>{font_style('Withdrawal Fee')}:</b> <b>{settings.get('withdrawal_tax_rate', 5.0)}%</b></blockquote>\n"
        f"<blockquote>🏛️ <b>{font_style('Accumulated Tax Pool')}:</b> <b>{format_money(tax_pool)}</b></blockquote>"
    )


def tax_reward_notice(rank: int, amount: int) -> str:
    title = font_style("Monthly Tax Dividend Reward")
    return (
        f"<b>🏆 {title}</b>\n"
        f"<blockquote>👑 You placed <b>#{rank}</b> on the monthly leaderboard!\n"
        f"💰 Dividend Received: <b>{format_money(amount)}</b> from the Central Tax Pool.</blockquote>"
    )


def interest_notice(amount: int) -> str:
    title = font_style("Bank Daily Interest Credited")
    return (
        f"<b>🏦 {title}</b>\n"
        f"<blockquote>💵 Your savings deposit earned <b>{format_money(amount)}</b> in daily yield.</blockquote>"
    )


def group_config_status(chat_id: int, cfg: dict[str, Any]) -> str:
    def mark(value: Any) -> str:
        return "✅ ON" if value else "⛔ OFF"

    return (
        f"<b>⚙️ GROUP CONFIG</b>\n"
        f"<blockquote>"
        f"🆔 Chat: <code>{chat_id}</code>\n"
        f"🤖 Bot: {mark(cfg.get('group_enabled', True))}\n"
        f"💰 Economy: {mark(cfg.get('economy_enabled', True))}\n"
        f"🎮 Games: {mark(cfg.get('games_enabled', True))}\n"
        f"🏆 Leaderboard: {mark(cfg.get('leaderboard_enabled', True))}\n"
        f"🛠 Admin Commands: {mark(cfg.get('admin_commands_enabled', True))}"
        f"</blockquote>\n"
        f"<i>Change with <code>/setchat setting on|off</code>.</i>"
    )


def asset_list(assets: list[dict[str, Any]], title: str = "ASSET MARKET") -> str:
    styled_title = font_style(title)
    lines = [f"<b>🏠 {styled_title}</b>", "<blockquote>"]
    for a in assets:
        arrow = "▲" if a.get("change_percent", 0) >= 0 else "▼"
        emoji = a.get("emoji", "📦")
        lines.append(
            f"{emoji} <code>{escape(a['symbol'])}</code> "
            f"<b>{format_money(a.get('price', 0))}</b> "
            f"{arrow} {abs(a.get('change_percent', 0)):.2f}%"
        )
    lines.append("</blockquote>")
    lines.append(f"<blockquote><i>💡 {font_style('Use /buyasset SYMBOL qty to acquire properties & assets')}</i></blockquote>")
    return "\n".join(lines)


def asset_detail(asset: dict[str, Any]) -> str:
    arrow = "▲" if asset.get("change_percent", 0) >= 0 else "▼"
    emoji = asset.get("emoji", "📦")
    frac = "Fractional" if asset.get("allow_fractional") else "Whole units"
    return (
        f"<b>{emoji} {font_style(asset['symbol'])} — {escape(asset.get('name', ''))}</b>\n"
        f"<blockquote>💵 <b>{font_style('Current Price')}:</b> <b>{format_money(asset.get('price', 0))}</b> {arrow} {asset.get('change_percent', 0):.2f}%\n"
        f"📋 <b>{font_style('Category')}:</b> {escape(str(asset.get('category', 'OTHER')))}</blockquote>\n"
        f"<blockquote>📈 <b>24h High:</b> {format_money(asset.get('high_price', 0))}\n"
        f"📉 <b>24h Low:</b> {format_money(asset.get('low_price', 0))}\n"
        f"📊 <b>{font_style('Volatility')}:</b> {asset.get('volatility', 0):.1%}</blockquote>\n"
        f"<blockquote>📝 <i>{escape(asset.get('description', 'Prime real-estate & luxury asset'))}</i></blockquote>"
    )


def asset_trade(action: str, result: dict[str, Any]) -> str:
    verb = font_style("Asset Acquired") if action == "buy" else font_style("Asset Liquidated")
    return (
        f"<b>✅ {verb} — {escape(result['symbol'])}</b>\n"
        f"<blockquote>🔢 <b>{font_style('Quantity')}:</b> <b>{result['quantity']:g}</b>\n"
        f"💵 <b>{font_style('Total Value')}:</b> <b>{format_money(result['total'] if action == 'buy' else result['received'])}</b></blockquote>\n"
        f"<blockquote>🧾 <code>#{result['tx_id']}</code></blockquote>"
    )


def asset_confirm_buy(symbol: str, name: str, emoji: str, qty: float, price: int, total: int) -> str:
    return (
        f"<b>🛒 {font_style('Confirm Asset Purchase')}</b>\n"
        f"<blockquote>{emoji} <code>{escape(symbol)}</code> — {escape(name)}\n"
        f"🔢 <b>{font_style('Quantity')}:</b> <b>{qty:g}</b>\n"
        f"💵 <b>{font_style('Unit Price')}:</b> <b>{format_money(price)}</b></blockquote>\n"
        f"<blockquote>💰 <b>{font_style('Total Payable')}:</b> <b>{format_money(total)}</b></blockquote>"
    )


def asset_portfolio(rows: list[str], total_value: int, total_invested: int) -> str:
    pnl = total_value - total_invested
    sign = "+" if pnl >= 0 else ""
    title = font_style("Real-Estate & Asset Holdings")
    return (
        f"<b>🏠 {title}</b>\n"
        f"<blockquote>" + "\n".join(rows) + "</blockquote>\n"
        f"<blockquote>💵 <b>{font_style('Total Asset Value')}:</b> <b>{format_money(total_value)}</b>\n"
        f"📈 <b>{font_style('Total P/L')}:</b> <b>{sign}{format_money(pnl)}</b></blockquote>"
    )


def asset_buy_info(info: dict[str, Any]) -> str:
    asset = info["asset"]
    arrow = "▲" if asset.get("change_percent", 0) >= 0 else "▼"
    emoji = asset.get("emoji", "📦")
    return (
        f"<b>{emoji} {font_style(asset['symbol'])} — {escape(asset.get('name', ''))}</b>\n"
        f"<blockquote>💵 <b>{font_style('Price')}:</b> <b>{format_money(asset.get('price', 0))}</b> {arrow} {asset.get('change_percent', 0):.2f}%\n"
        f"🏛️ <b>{font_style('Market Cap')}:</b> {format_money(info['market_cap'])}</blockquote>\n"
        f"<blockquote>👥 <b>{font_style('Active Holders')}:</b> {info['holders']} · 📦 <b>{font_style('Circulating')}:</b> {info['total_held']:g}\n"
        f"🧾 <b>{font_style('Total Trades')}:</b> {info['trades']}</blockquote>\n"
        f"<blockquote><i>💡 Use <code>/buyasset {asset['symbol']} qty</code> to purchase.</i></blockquote>"
    )


def asset_market_stats(stats: dict[str, Any]) -> str:
    title = font_style("Asset Market Overview")
    return (
        f"<b>📊 {title}</b>\n"
        f"<blockquote>📈 <b>{font_style('Listed Assets')}:</b> <b>{stats['active']}</b> / {stats['total']}\n"
        f"💹 <b>{font_style('Total Valuation')}:</b> <b>{format_money(stats['total_market_value'])}</b></blockquote>\n"
        f"<blockquote>🧾 <b>{font_style('24h Trading Volume')}:</b> {format_money(stats['total_volume'])}\n"
        f"🟢 <b>Gainers:</b> {stats['gainers']} · 🔴 <b>Losers:</b> {stats['losers']} · ⚪ <b>Flat:</b> {stats['unchanged']}</blockquote>"
    )


def listings_list(listings: list[dict[str, Any]], symbol: str | None, page: int, pages: int) -> str:
    title = font_style("P2P Resale Marketplace")
    lines = [f"<b>🛒 {title}</b> (pg {page}/{pages})", "<blockquote>"]
    for listing in listings:
        lines.append(
            f"{listing.get('emoji', '📦')} <code>#{listing['listing_id']}</code> "
            f"{escape(listing['symbol'])} × <b>{listing['quantity']:g}</b> "
            f"→ <b>{format_money(listing['total_price'])}</b>"
        )
    lines.append("</blockquote>")
    lines.append(f"<blockquote><i>💡 {font_style('Buy via /buylisting ID or list via /listasset')}</i></blockquote>")
    return "\n".join(lines)


def my_listings(listings: list[dict[str, Any]]) -> str:
    title = font_style("My Active Listings")
    if not listings:
        return f"<b>🛒 {title}</b>\n<blockquote><i>{font_style('You currently have no active listings')}.</i></blockquote>"
    lines = [f"<b>🛒 {title}</b>", "<blockquote>"]
    for listing in listings:
        status = {
            "active": "🟢",
            "pending": "🕐",
            "sold": "✅",
            "cancelled": "❌",
        }.get(listing["status"], "•")
        lines.append(
            f"{status} <code>#{listing['listing_id']}</code> "
            f"{escape(listing['symbol'])} × <b>{listing['quantity']:g}</b> "
            f"→ <b>{format_money(listing['total_price'])}</b>"
        )
    lines.append("</blockquote>")
    return "\n".join(lines)


def emoji_lobby(game_label: str, emoji: str, bet: int, game_id: str, expiry: int) -> str:
    title = font_style(f"{game_label} 1v1 Duel Lobby")
    return (
        f"<b>⚔️ {emoji} {title}</b>\n"
        f"<blockquote>🎰 <b>{font_style('Lobby Code')}:</b> <code>{game_id}</code>\n"
        f"💰 <b>{font_style('Entry Bet')}:</b> <b>{format_money(bet)}</b></blockquote>\n"
        f"<blockquote>⏳ <b>{font_style('Lobby Expires')}:</b> in <b>{format_duration(expiry)}</b>\n"
        f"👉 <i>{font_style('Join with')} <code>/join {game_id}</code></i></blockquote>"
    )


def emoji_single_result(
    game_label: str,
    emoji: str,
    result: int,
    outcome: str,
    bet: int,
    payout: int,
    tx_id: str,
) -> str:
    title = font_style(f"{game_label} Challenge")
    if outcome == "win":
        body = f"✅ <b>{font_style('Target Hit')}!</b> <b>{format_money(payout)}</b> (Profit: {format_money(payout - bet)})"
    else:
        body = f"❌ <b>{font_style('Missed Shot')}!</b> Lost: {format_money(bet)}"
    return (
        f"<b>{emoji} {title}</b>\n"
        f"<blockquote>🎯 <b>{font_style('Score Rolled')}:</b> <b>{result}</b></blockquote>\n"
        f"<blockquote>{body}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def emoji_duel_result(
    game_label: str,
    emoji: str,
    player1: tuple[str, int],
    player2: tuple[str, int],
    winner: tuple[str, int] | None,
    bet: int,
    payout: int,
    tx_id: str | None,
) -> str:
    name1, result1 = player1
    name2, result2 = player2
    title = font_style(f"{game_label} Duel Result")
    
    if winner is None:
        outcome_block = f"🤝 <b>{font_style('Draw Match')}!</b> Both bets ({format_money(bet)}) refunded."
    else:
        winner_name, _ = winner
        outcome_block = f"🏆 <b>{escape(winner_name)} {font_style('Wins the Duel')}!</b>\n💰 <b>{font_style('Total Pot')}:</b> <b>{format_money(payout)}</b>"

    tx_line = f"\n<blockquote>🧾 <code>#{tx_id}</code></blockquote>" if tx_id else ""
    return (
        f"<b>⚔️ {emoji} {title}</b>\n"
        f"<blockquote>🔴 {escape(name1)}: <b>{result1}</b>\n"
        f"🔵 {escape(name2)}: <b>{result2}</b></blockquote>\n"
        f"<blockquote>{outcome_block}</blockquote>"
        f"{tx_line}"
    )


def blackjack_result(
    user_cards: list[str],
    bot_cards: list[str],
    user_total: int,
    bot_total: int,
    outcome: str,
    bet: int,
    payout: int,
    tx_id: str,
) -> str:
    title = font_style("Blackjack Table")
    if outcome == "win":
        verdict = f"✅ <b>{font_style('Dealer Defeated')}!</b> <b>{format_money(payout)}</b> (Profit: {format_money(payout - bet)})"
    elif outcome == "loss":
        verdict = f"❌ <b>{font_style('Dealer Won')}!</b> Lost: {format_money(bet)}"
    else:
        verdict = f"🤝 <b>{font_style('Push (Draw)')}!</b> Bet returned ({format_money(bet)})"
    return (
        f"<b>🃏 {title}</b>\n"
        f"<blockquote>🫵 <b>{font_style('Your Hand')}:</b> {' '.join(user_cards)} → <b>{user_total}</b>\n"
        f"🤖 <b>{font_style('Bot Dealer')}:</b> {' '.join(bot_cards)} → <b>{bot_total}</b></blockquote>\n"
        f"<blockquote>{verdict}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def emoji_game_info(game_type: str, emoji: str, label: str, config: dict[str, Any]) -> str:
    lines = [
        f"<b>🎮 {emoji} {label} ({escape(game_type)})</b>",
        "",
        f"🟢 Enabled: <b>{'yes' if config.get('enabled', True) else 'no'}</b>",
        f"🔴 Single-player: <b>{'yes' if config.get('single_enabled', True) else 'no'}</b>",
        f"⚔️ Duels: <b>{'yes' if config.get('duel_enabled', True) else 'no'}</b>",
        f"⏳ Cooldown: <b>{config.get('cooldown', 60)}s</b>",
        f"💰 Bet range: <b>{format_money(config.get('minimum_bet', 0))} – {format_money(config.get('maximum_bet', 0))}</b>",
        f"🎯 Win rule: <b>{escape(config.get('win_rule', 'gte'))}</b> on <b>{config.get('win_target', '-')}</b>",
        f"💥 Multiplier: <b>{config.get('multiplier', 1.0):.2f}x</b>",
        f"⏲️ Lobby expiry: <b>{config.get('lobby_expiry', 300)}s</b>",
    ]
    return "\n".join(lines)


def emoji_games_list(configs: dict[str, Any], defs: dict[str, Any]) -> str:
    lines = ["<b>🎲 EMOJI GAMES</b>", ""]
    for game_type, game_def in defs.items():
        cfg = configs.get(game_type, {})
        status = "🟢" if cfg.get("enabled", True) else "🔴"
        lines.append(
            f"{status} {game_def.emoji} <code>{game_def.label}</code> "
            f"· single {format_money(cfg.get('minimum_bet', 0))}–{format_money(cfg.get('maximum_bet', 0))}"
            f" · duel bet {format_money(cfg.get('minimum_bet', 0))}–{format_money(cfg.get('maximum_bet', 0))}"
            f" · cooldown {cfg.get('cooldown', 60)}s"
        )
    lines.append(
        "",
        "<i>Play solo with <code>/sball /sarrow /sbasketball</code> or duel with "
        "<code>/ball /arrow /basketball</code> + <code>/join CODE</code>.</i>",
    )
    return "\n".join(lines)


def blackjack_info(config: dict[str, Any]) -> str:
    return (
        f"<b>🃏 BLACKJACK</b>\n"
        f"<blockquote>🟢 Enabled: <b>{'yes' if config.get('enabled', True) else 'no'}</b>\n"
        f"⏳ Cooldown: <b>{config.get('cooldown', 60)}s</b>\n"
        f"💰 Bet range: <b>{format_money(config.get('minimum_bet', 0))} – {format_money(config.get('maximum_bet', 0))}</b>\n"
        f"💥 Payout multiplier: <b>{config.get('multiplier', 1.0):.2f}x</b></blockquote>\n"
        f"<i>2 cards each, A=11/1, J/Q/K=10, highest total wins, ties refund the bet.</i>"
    )


# --------------------------------------------------------------------------- #
# Promo system
# --------------------------------------------------------------------------- #


def _fmt_qty(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text or "0"


def _reward_line(reward: dict[str, Any]) -> str:
    kind = reward.get("type")
    if kind == "currency":
        return f"💰 {format_money(int(reward.get('amount', 0)))}"
    if kind == "stock":
        return f"📈 {escape(str(reward.get('symbol', '')))} × {_fmt_qty(float(reward.get('quantity', 0)))}"
    if kind == "asset":
        return f"🏠 {escape(str(reward.get('asset_id', '')))} × {_fmt_qty(float(reward.get('quantity', 0)))}"
    return f"🎁 {escape(str(reward))}"


def _promo_status(doc: dict[str, Any], now: int) -> str:
    if not doc.get("is_active"):
        return "Inactive"
    expires_at = doc.get("expires_at")
    if expires_at is not None and now >= int(expires_at):
        return "Expired"
    return "Active"


def _expiry_text(doc: dict[str, Any]) -> str:
    label = doc.get("expiry_label") or "Lifetime"
    expires_at = doc.get("expires_at")
    if expires_at is not None:
        remaining = int(expires_at) - int(time.time())
        if remaining > 0:
            label += f" ({format_duration(remaining)} left)"
        else:
            label += " (expired)"
    return label


def _uses_text(doc: dict[str, Any]) -> str:
    used = int(doc.get("redeemed_count", 0))
    mx = doc.get("max_redemptions")
    return f"{used} / {mx}" if mx is not None else f"{used} / ∞"


def promo_created(doc: dict[str, Any]) -> str:
    lines = [
        f"🎟 Code: <code>{escape(doc['code'])}</code>",
        f"⏰ Expiry: {_expiry_text(doc)}",
        f"👥 Limit: {_uses_text(doc)}",
        "🎁 Rewards:",
    ]
    lines.extend(f"  {_reward_line(r)}" for r in doc.get("rewards", []))
    return f"<b>✅ PROMO CREATED</b>\n<blockquote>{chr(10).join(lines)}</blockquote>"


def promo_redeemed(result: dict[str, Any]) -> str:
    lines = [
        f"🎟 Code: <code>{escape(result['promo']['code'])}</code>",
        "🎁 Rewards:",
    ]
    lines.extend(f"  {g['description']}" for g in result.get("granted", []))
    return (
        f"<b>🎁 PROMO REDEEMED</b>\n"
        f"<blockquote>{chr(10).join(lines)}</blockquote>\n"
        f"<b>✅ Rewards added successfully.</b>"
    )


def promo_already_used() -> str:
    return (
        "<b>⚠️ PROMO ALREADY USED</b>\n"
        "<blockquote>You have already redeemed this promo code. Each user can redeem once.</blockquote>"
    )


def promo_expired() -> str:
    return "<b>⌛ PROMO EXPIRED</b>\n<blockquote>This promo code has expired.</blockquote>"


def promo_inactive() -> str:
    return "<b>🚫 PROMO INACTIVE</b>\n<blockquote>This promo code is no longer active.</blockquote>"


def promo_limit_reached() -> str:
    return (
        "<b>❌ PROMO LIMIT REACHED</b>\n"
        "<blockquote>This promo code has reached its maximum redemption limit.</blockquote>"
    )


def promo_info(doc: dict[str, Any]) -> str:
    now = int(time.time())
    lines = [
        f"🎟 Code: <code>{escape(doc['code'])}</code>",
        f"📊 Status: <b>{_promo_status(doc, now)}</b>",
        f"⏰ Expiry: {_expiry_text(doc)}",
        f"👥 Uses: {_uses_text(doc)}",
        "👤 Per user: 1",
        "🎁 Rewards:",
    ]
    lines.extend(f"  {_reward_line(r)}" for r in doc.get("rewards", []))
    return f"<b>🎁 PROMO INFO</b>\n<blockquote>{chr(10).join(lines)}</blockquote>"


def promo_list(docs: list[dict[str, Any]], total: int, page: int, per_page: int) -> str:
    if not docs:
        return "<b>🎁 PROMO LIST</b>\n<blockquote>No promos found.</blockquote>"
    now = int(time.time())
    lines = [
        f"{idx}. <code>{escape(doc['code'])}</code> — <b>{_promo_status(doc, now)}</b> · "
        f"{_expiry_text(doc)} · {_uses_text(doc)}"
        for idx, doc in enumerate(docs, start=1)
    ]
    pages = max(1, math.ceil(total / per_page))
    return (
        f"<b>🎁 PROMO LIST</b>\n<blockquote>{chr(10).join(lines)}</blockquote>\n"
        f"<i>Page {page} of {pages} · Total {total}</i>"
    )


def promo_stats(stats: dict[str, Any]) -> str:
    promo = stats["promo"]
    lines = [
        f"🎟 Code: <code>{escape(promo['code'])}</code>",
        f"✅ Redemptions: {stats['total_redemptions']}",
        f"👥 Unique users: {stats['unique_users']}",
    ]
    remaining = stats["remaining"]
    lines.append(f"♻️ Remaining: <b>{'∞' if remaining is None else remaining}</b>")
    if stats["currency_total"]:
        lines.append(f"💰 Currency given: {format_money(int(stats['currency_total']))}")
    for symbol, qty in stats["stock_rows"]:
        lines.append(f"📈 Stock given: {_fmt_qty(qty)} × {escape(symbol)}")
    for asset_id, qty in stats["asset_rows"]:
        lines.append(f"🏠 Asset given: {_fmt_qty(qty)} × {escape(asset_id)}")
    if stats.get("last_redeemed_at"):
        ago = int(time.time()) - int(stats["last_redeemed_at"])
        lines.append(f"🕒 Last redemption: {format_duration(ago)} ago")
    return f"<b>📊 PROMO STATS</b>\n<blockquote>{chr(10).join(lines)}</blockquote>"


def loan_taken(principal: int, interest_fee: int, total_debt: int, tx_id: str) -> str:
    title = font_style("Bank Loan Approved")
    return (
        f"<b>🏦 {title}</b>\n"
        f"<blockquote>💵 <b>{font_style('Principal Borrowed')}:</b> <b>{format_money(principal)}</b>\n"
        f"🧾 <b>{font_style('Interest Fee')}:</b> {format_money(interest_fee)} (5%)\n"
        f"💳 <b>{font_style('Total Debt Due')}:</b> <b>{format_money(total_debt)}</b></blockquote>\n"
        f"<blockquote>💡 <i>{font_style('Funds added to wallet. Repay anytime via')} <code>/repay</code>.</i></blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def loan_repaid(repaid: int, remaining_debt: int, is_cleared: bool, tx_id: str) -> str:
    title = font_style("Bank Loan Repayment")
    if is_cleared:
        status_line = f"🎉 <b>{font_style('Loan Fully Cleared')}!</b> You have zero outstanding debt."
    else:
        status_line = f"💳 <b>{font_style('Remaining Debt')}:</b> <b>{format_money(remaining_debt)}</b>"

    return (
        f"<b>🏦 {title}</b>\n"
        f"<blockquote>💵 <b>{font_style('Amount Repaid')}:</b> <b>{format_money(repaid)}</b>\n"
        f"{status_line}</blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )


def loan_status_view(status: dict[str, Any]) -> str:
    title = font_style("Central Bank Credit & Loans")
    if not status["has_active_loan"]:
        return (
            f"<b>🏦 {title}</b>\n"
            f"<blockquote>🟢 <b>{font_style('Credit Status')}:</b> <b>{font_style('No Active Debt')}</b>\n"
            f"💰 <b>{font_style('Borrowing Limit')}:</b> <b>{format_money(status['max_limit'])}</b>\n"
            f"📈 <b>{font_style('Loan Interest Rate')}:</b> <b>{status['interest_rate']}%</b></blockquote>\n"
            f"<blockquote>💡 <i>{font_style('Borrow funds with')} <code>/loan amount</code>.</i></blockquote>"
        )

    return (
        f"<b>🏦 {title}</b>\n"
        f"<blockquote>🔴 <b>{font_style('Active Loan Debt')}:</b> <b>{format_money(status['active_debt'])}</b>\n"
        f"💵 <b>{font_style('Initial Principal')}:</b> {format_money(status['principal'])}\n"
        f"🧾 <b>{font_style('Interest Accrued')}:</b> {format_money(status['interest'])}</blockquote>\n"
        f"<blockquote>👉 <i>{font_style('Repay using')} <code>/repay [amount]</code> {font_style('from your wallet')}.</i></blockquote>"
    )


def armory_catalog(guns: dict[str, dict[str, Any]], user_guns: list[str]) -> str:
    title = font_style("Black Market Armory & Gun Store")
    items = list(guns.items())
    half = len(items) // 2

    b1_lines = []
    for gid, g in items[:half]:
        owned = " [EQUIPPED ✅]" if gid in user_guns else ""
        b1_lines.append(
            f"{g['emoji']} <b>{g['name']}</b>{owned}\n"
            f"💵 <b>{format_money(g['price'])}</b> · ⚔️ <b>+{int(g['attack_buff']*100)}% Atk</b> · 🛡️ <b>+{int(g['defense_buff']*100)}% Def</b>\n"
            f"<i>{g['desc']}</i>"
        )

    b2_lines = []
    for gid, g in items[half:]:
        owned = " [EQUIPPED ✅]" if gid in user_guns else ""
        b2_lines.append(
            f"{g['emoji']} <b>{g['name']}</b>{owned}\n"
            f"💵 <b>{format_money(g['price'])}</b> · ⚔️ <b>+{int(g['attack_buff']*100)}% Atk</b> · 🛡️ <b>+{int(g['defense_buff']*100)}% Def</b>\n"
            f"<i>{g['desc']}</i>"
        )

    return (
        f"<b>🔫 {title}</b>\n\n"
        f"<blockquote>🏛️ <b>{font_style('Underground Weapons Exchange')}</b>\n"
        f"<i>Equip military firepower to boost robbery raids and protect your wealth!</i></blockquote>\n\n"
        f"<blockquote>" + "\n\n".join(b1_lines) + "</blockquote>\n\n"
        f"<blockquote>" + "\n\n".join(b2_lines) + "</blockquote>\n\n"
        f"<blockquote>💡 <i>{font_style('Tap inline buttons below to purchase & equip instantly!')}</i></blockquote>"
    )


def armory_inventory(user_doc: dict[str, Any], guns: dict[str, dict[str, Any]], owned_ids: list[str]) -> str:
    title = font_style("Personal Weapon Armory")
    username = user_doc.get("username") or user_doc.get("first_name", "User")
    if not owned_ids:
        return (
            f"<b>🎒 {title}</b>\n\n"
            f"<blockquote>👤 <b>{font_style('Arsenal of')}:</b> @{username}\n"
            f"❌ <b>{font_style('Empty Armory')}:</b> You don't own any firearms yet!</blockquote>\n\n"
            f"<blockquote>💡 <i>{font_style('Browse the black market with')} <code>/guns</code></i></blockquote>"
        )

    lines = []
    total_val = 0
    max_atk = 0
    max_def = 0
    for gid in owned_ids:
        g = guns.get(gid)
        if g:
            total_val += g["price"]
            max_atk = max(max_atk, int(g["attack_buff"] * 100))
            max_def = max(max_def, int(g["defense_buff"] * 100))
            lines.append(f"• {g['emoji']} <b>{g['name']}</b> ({format_money(g['price'])})")

    items_text = "\n".join(lines)
    return (
        f"<b>🎒 {title}</b>\n\n"
        f"<blockquote>👤 <b>{font_style('Arsenal of')}:</b> @{username}\n"
        f"{items_text}</blockquote>\n\n"
        f"<blockquote>⚔️ <b>{font_style('Active Rob Attack Buff')}:</b> <b>+{max_atk}%</b>\n"
        f"🛡️ <b>{font_style('Active Rob Defense Buff')}:</b> <b>+{max_def}%</b>\n"
        f"💎 <b>{font_style('Armory Valuation')}:</b> <b>{format_money(total_val)}</b></blockquote>"
    )


def gun_purchased(gun: dict[str, Any], price: int, tx_id: str) -> str:
    title = font_style("Firearm Acquired & Equipped")
    return (
        f"<b>🔫 {title}</b>\n"
        f"<blockquote>{gun['emoji']} <b>{font_style('Weapon')}:</b> <b>{gun['name']}</b>\n"
        f"💵 <b>{font_style('Price Paid')}:</b> <b>{format_money(price)}</b>\n"
        f"⚔️ <b>{font_style('Rob Attack')}:</b> +{int(gun['attack_buff']*100)}% | 🛡️ <b>{font_style('Rob Defense')}:</b> +{int(gun['defense_buff']*100)}%</blockquote>\n"
        f"<blockquote>💡 <i>{gun['desc']}</i></blockquote>\n"
        f"<blockquote>🧾 <code>#{tx_id}</code></blockquote>"
    )

