"""Bank Loan service.

Enables citizens to take loans from the Central Bank with interest fee,
enforces maximum borrowing limits based on net worth, and tracks active debt.
"""

from __future__ import annotations

import time
from typing import Any

from database import users as users_db
from database.mongo import mongo
from services import leaderboard as leaderboard_service, tax as tax_service, transaction as tx_service
from utils.money import UNIT, format_money

LOAN_INTEREST_RATE = 5.0  # 5% fixed loan interest fee
BASE_MAX_LOAN = 1_000_000 * UNIT  # ₹1,000,000 base max loan limit


async def get_max_loan_limit(user_id: int) -> int:
    """Maximum loan a user is eligible to borrow based on net worth."""
    user = await users_db.get_user(user_id)
    if not user:
        return BASE_MAX_LOAN
    nw = await leaderboard_service.net_worth(user)
    # 50% of net worth or base limit (whichever is higher, capped at 100M)
    limit = max(BASE_MAX_LOAN, nw // 2)
    return min(limit, 100_000_000 * UNIT)


async def take_loan(user_id: int, amount: int) -> dict[str, Any]:
    """Borrow money from the Central Bank."""
    if amount <= 0:
        raise ValueError("Loan amount must be positive.")

    user = await users_db.get_or_create_user(user_id)
    active_debt = int(user.get("loan_debt", 0))
    if active_debt > 0:
        raise ValueError(
            f"You already have an active loan debt of {format_money(active_debt)}. "
            "Please repay it using <code>/repay</code> before applying for a new loan."
        )

    max_limit = await get_max_loan_limit(user_id)
    if amount > max_limit:
        raise ValueError(
            f"Requested amount exceeds your maximum borrowing limit of {format_money(max_limit)}."
        )

    interest_fee = int(amount * (LOAN_INTEREST_RATE / 100.0))
    total_debt = amount + interest_fee
    now = int(time.time())

    # Atomically credit wallet and set debt
    await mongo.db[users_db.COLLECTION].update_one(
        {"user_id": user_id},
        {
            "$inc": {"wallet": amount, "total_earned": amount},
            "$set": {
                "loan_debt": total_debt,
                "loan_principal": amount,
                "loan_interest": interest_fee,
                "loan_taken_at": now,
                "updated_at": now,
            },
        },
    )

    updated_user = await users_db.get_user(user_id)
    tx_id = await tx_service.record(
        user_id=user_id,
        ttype="LOAN_TAKEN",
        amount=amount,
        balance_before=updated_user.get("wallet", 0) - amount,
        balance_after=updated_user.get("wallet", 0),
        metadata={"principal": amount, "interest_fee": interest_fee, "total_debt": total_debt},
    )

    return {
        "principal": amount,
        "interest_fee": interest_fee,
        "total_debt": total_debt,
        "wallet": updated_user.get("wallet", 0),
        "tx_id": tx_id,
    }


async def repay_loan(user_id: int, amount: int | None = None) -> dict[str, Any]:
    """Repay active loan from wallet."""
    user = await users_db.get_or_create_user(user_id)
    active_debt = int(user.get("loan_debt", 0))
    if active_debt <= 0:
        raise ValueError("You do not have any active bank loans to repay.")

    repay_amount = min(amount if amount and amount > 0 else active_debt, active_debt)
    wallet = int(user.get("wallet", 0))
    if wallet < repay_amount:
        raise ValueError(
            f"Insufficient wallet balance. You need {format_money(repay_amount)} to repay this loan, "
            f"but you only have {format_money(wallet)}."
        )

    now = int(time.time())
    new_debt = active_debt - repay_amount

    # Deduct from wallet and reduce debt
    res = await mongo.db[users_db.COLLECTION].find_one_and_update(
        {"user_id": user_id, "wallet": {"$gte": repay_amount}},
        {
            "$inc": {"wallet": -repay_amount, "total_spent": repay_amount},
            "$set": {
                "loan_debt": new_debt,
                "updated_at": now,
            },
        },
        return_document=True,
    )
    if res is None:
        raise ValueError("Payment failed due to balance update mismatch.")

    # If fully paid, clear loan fields and feed interest to tax pool
    if new_debt == 0:
        interest_paid = int(user.get("loan_interest", 0))
        if interest_paid > 0:
            await tax_service.collect(user_id, interest_paid)

        await mongo.db[users_db.COLLECTION].update_one(
            {"user_id": user_id},
            {
                "$unset": {
                    "loan_principal": "",
                    "loan_interest": "",
                    "loan_taken_at": "",
                }
            },
        )

    tx_id = await tx_service.record(
        user_id=user_id,
        ttype="LOAN_REPAID",
        amount=repay_amount,
        balance_before=wallet,
        balance_after=res.get("wallet", 0),
        metadata={"repaid": repay_amount, "remaining_debt": new_debt},
    )

    return {
        "repaid": repay_amount,
        "remaining_debt": new_debt,
        "is_fully_cleared": new_debt == 0,
        "wallet": res.get("wallet", 0),
        "tx_id": tx_id,
    }


async def get_loan_status(user_id: int) -> dict[str, Any]:
    """Get active loan status and borrowing limit."""
    user = await users_db.get_or_create_user(user_id)
    active_debt = int(user.get("loan_debt", 0))
    principal = int(user.get("loan_principal", 0))
    interest = int(user.get("loan_interest", 0))
    taken_at = user.get("loan_taken_at")
    max_limit = await get_max_loan_limit(user_id)

    return {
        "has_active_loan": active_debt > 0,
        "active_debt": active_debt,
        "principal": principal,
        "interest": interest,
        "taken_at": taken_at,
        "max_limit": max_limit,
        "interest_rate": LOAN_INTEREST_RATE,
    }
