from decimal import Decimal

from app.core.money import percent_of, rupees_from_qty_rate


def test_gaz_line_total_rounds_half_up() -> None:
    assert rupees_from_qty_rate(Decimal("3.5"), 480) == 1680
    assert rupees_from_qty_rate(Decimal("3.5"), 101) == 354


def test_percent_discount_rounds_to_rupees() -> None:
    assert percent_of(1000, 10) == 100
    assert percent_of(105, 10) == 11
