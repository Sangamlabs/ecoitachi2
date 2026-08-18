"""Bank handlers: /deposit, /withdraw, /bank, /transactions."""

from __future__ import annotations

from pyrogram import Client, filters
from pyrogram.types import Message

from database import users as users_db
from handlers.common import ensure_user, safe_handler
from services import bank as bank_service, transaction as tx_service
from utils import messages as msgs
from utils.money import format_money
from utils.sender import reply_html
from utils.validators import parse_amount_or_error

NOT_CHANNEL = ~filters.channel & ~filters.bot


def register(app: Client) -> None:
    @app.on_message(filters.command("bank") & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_bank(client: Client, message: Message):
        await ensure_user(client, message)
        view = await bank_service.get_bank_view(message.from_user.id)
        user = await users_db.get_user(message.from_user.id)
        await reply_html(client, message, msgs.bank(user, view["settings"], view["tax_pool"]))

    @app.on_message(filters.command("deposit") & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_deposit(client: Client, message: Message):
        await ensure_user(client, message)
        amount, err = parse_amount_or_error(message.command[1] if len(message.command) > 1 else "")
        if err:
            await reply_html(client, message, msgs.error(f"Usage: <code>/deposit amount</code>. {err}"))
            return
        result = await bank_service.deposit(message.from_user.id, amount)
        await reply_html(
            client, message,
            msgs.success(
                f"Deposited {format_money(amount)} into your bank.\n"
                f"Wallet: {format_money(result['wallet'])} · Bank: {format_money(result['bank'])}"
            ),
        )

    @app.on_message(filters.command("withdraw") & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_withdraw(client: Client, message: Message):
        await ensure_user(client, message)
        amount, err = parse_amount_or_error(message.command[1] if len(message.command) > 1 else "")
        if err:
            await reply_html(client, message, msgs.error(f"Usage: <code>/withdraw amount</code>. {err}"))
            return
        result = await bank_service.withdraw(message.from_user.id, amount)
        await reply_html(
            client, message,
            msgs.success(
                f"Withdrawal: {format_money(result['gross'])}\n"
                f"Tax: {format_money(result['tax'])}\n"
                f"Received: <b>{format_money(result['received'])}</b>"
            ),
        )

    @app.on_message(filters.command("transactions") & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_transactions(client: Client, message: Message):
        await ensure_user(client, message)
        recent = await tx_service.get_recent_transfers(message.from_user.id, 10)
        rows = [msgs.transaction_row(tx) for tx in recent]
        await reply_html(client, message, msgs.transactions_list(rows, not rows))

    @app.on_message(filters.command(["loan", "borrow"]) & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_loan(client: Client, message: Message):
        await ensure_user(client, message)
        from services import loan as loan_service
        args = message.command[1:]
        if not args:
            status = await loan_service.get_loan_status(message.from_user.id)
            await reply_html(client, message, msgs.loan_status_view(status))
            return

        amount, err = parse_amount_or_error(args[0])
        if err:
            await reply_html(client, message, msgs.error(f"Usage: <code>/loan amount</code>. {err}"))
            return

        try:
            res = await loan_service.take_loan(message.from_user.id, amount)
            await reply_html(
                client, message,
                msgs.loan_taken(res["principal"], res["interest_fee"], res["total_debt"], res["tx_id"])
            )
        except Exception as e:
            await reply_html(client, message, msgs.error(str(e)))

    @app.on_message(filters.command("repay") & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_repay(client: Client, message: Message):
        await ensure_user(client, message)
        from services import loan as loan_service
        args = message.command[1:]
        amount = None
        if args:
            parsed, err = parse_amount_or_error(args[0])
            if err:
                await reply_html(client, message, msgs.error(f"Usage: <code>/repay [amount]</code>. {err}"))
                return
            amount = parsed

        try:
            res = await loan_service.repay_loan(message.from_user.id, amount)
            await reply_html(
                client, message,
                msgs.loan_repaid(res["repaid"], res["remaining_debt"], res["is_fully_cleared"], res["tx_id"])
            )
        except Exception as e:
            await reply_html(client, message, msgs.error(str(e)))

    @app.on_message(filters.command(["loans", "loanstatus"]) & NOT_CHANNEL)
    @safe_handler(feature="economy")
    async def cmd_loanstatus(client: Client, message: Message):
        await ensure_user(client, message)
        from services import loan as loan_service
        status = await loan_service.get_loan_status(message.from_user.id)
        await reply_html(client, message, msgs.loan_status_view(status))

