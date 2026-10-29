"""Tests for pricing.rules — tax, discount, and full pipeline."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pricing.rules import (
    get_discount,
    get_tax_rate,
    apply_discount,
    apply_tax,
    calculate_item_price,
)


def test_get_discount_standard():
    assert get_discount("standard") == 0.0


def test_get_discount_gold():
    assert get_discount("gold") == 0.10


def test_get_discount_platinum():
    assert get_discount("platinum") == 0.20


def test_get_discount_unknown_tier_returns_zero():
    assert get_discount("vip") == 0.0


def test_get_tax_rate_electronics():
    assert get_tax_rate("electronics") == 0.08


def test_get_tax_rate_food_zero():
    assert get_tax_rate("food") == 0.0


def test_get_tax_rate_unknown_uses_default():
    assert get_tax_rate("widgets") == 0.07


def test_apply_discount_gold_reduces_price():
    result = apply_discount(100.0, "gold")
    assert result == 90.0


def test_apply_discount_standard_unchanged():
    result = apply_discount(50.0, "standard")
    assert result == 50.0


def test_apply_tax_electronics():
    result = apply_tax(100.0, "electronics")
    assert result == 108.0


def test_apply_tax_food_no_tax():
    result = apply_tax(20.0, "food")
    assert result == 20.0


def test_calculate_item_price_platinum_electronics():
    # base=100, platinum 20% off = 80, electronics 8% tax = 86.4
    result = calculate_item_price(100.0, "electronics", "platinum")
    assert result == 86.4


def test_calculate_item_price_standard_food():
    # base=50, no discount, no tax
    result = calculate_item_price(50.0, "food", "standard")
    assert result == 50.0
