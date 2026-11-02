from decimal import ROUND_HALF_UP, Decimal

RUPEE = Decimal("1")


def to_qty(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def rupees_from_qty_rate(qty: Decimal, rate: int) -> int:
    """Line total: qty (gaz/piece) times integer rupee rate, rounded to whole rupees."""
    return int((to_qty(qty) * Decimal(rate)).quantize(RUPEE, rounding=ROUND_HALF_UP))


def percent_of(amount: int, percent: int) -> int:
    """percent is a whole number (10 = 10%). Result is whole rupees."""
    return int((Decimal(amount) * Decimal(percent) / Decimal(100)).quantize(RUPEE, rounding=ROUND_HALF_UP))


def qty_str(value: Decimal) -> str:
    return f"{to_qty(value):.2f}"
