"""Voucher validation and redemption.

Intentional duplicate symbol: `apply_discount` also exists in pricing.rules
with different semantics (percentage off a price vs. a fixed voucher amount).
"""
from __future__ import annotations

VOUCHERS: dict[str, float] = {
    "SAVE10": 10.0,
    "SAVE25": 25.0,
    "WELCOME": 5.0,
}


def validate_voucher(code: str) -> bool:
    """Return True if the voucher code is known and active."""
    return code.upper() in VOUCHERS


def get_voucher_amount(code: str) -> float:
    """Return the fixed-currency discount for a voucher, or 0 if invalid."""
    return VOUCHERS.get(code.upper(), 0.0)


def apply_discount(total: float, code: str) -> float:
    """Subtract the voucher amount from total; never go below 0."""
    amount = get_voucher_amount(code)
    return max(0.0, round(total - amount, 2))
