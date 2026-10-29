"""Tests for pricing.vouchers — validation and fixed discount."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pricing.vouchers import validate_voucher, get_voucher_amount, apply_discount


def test_validate_known_voucher():
    assert validate_voucher("SAVE10") is True


def test_validate_case_insensitive():
    assert validate_voucher("save10") is True


def test_validate_unknown_voucher():
    assert validate_voucher("FAKECODE") is False


def test_get_voucher_amount_save25():
    assert get_voucher_amount("SAVE25") == 25.0


def test_get_voucher_amount_unknown_is_zero():
    assert get_voucher_amount("NONE") == 0.0


def test_apply_discount_subtracts_voucher():
    # total=50, SAVE10 takes 10 off → 40
    result = apply_discount(50.0, "SAVE10")
    assert result == 40.0


def test_apply_discount_never_goes_negative():
    # SAVE25 on total=5 → floor at 0
    result = apply_discount(5.0, "SAVE25")
    assert result == 0.0
