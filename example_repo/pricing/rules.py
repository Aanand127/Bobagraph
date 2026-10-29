"""Pricing rules: discounts, taxes, and final price calculation."""
from __future__ import annotations

# Discount rates by customer tier
TIER_DISCOUNT = {
    "standard": 0.0,
    "gold": 0.10,
    "platinum": 0.20,
}

# Tax rate by product category
CATEGORY_TAX = {
    "electronics": 0.08,
    "food": 0.0,
    "clothing": 0.05,
    "default": 0.07,
}


def get_discount(tier: str) -> float:
    """Return the fractional discount for a customer loyalty tier."""
    return TIER_DISCOUNT.get(tier, 0.0)


def get_tax_rate(category: str) -> float:
    """Return the applicable tax rate for a product category."""
    return CATEGORY_TAX.get(category, CATEGORY_TAX["default"])


def apply_discount(price: float, tier: str) -> float:
    """Reduce price by the tier discount.  Returns the discounted price."""
    discount = get_discount(tier)
    return round(price * (1 - discount), 2)


def apply_tax(price: float, category: str) -> float:
    """Add category tax to a price.  Returns the final taxed price."""
    rate = get_tax_rate(category)
    return round(price * (1 + rate), 2)


def calculate_item_price(base_price: float, category: str, tier: str) -> float:
    """Full price pipeline: base → discount → tax."""
    discounted = apply_discount(base_price, tier)
    return apply_tax(discounted, category)
