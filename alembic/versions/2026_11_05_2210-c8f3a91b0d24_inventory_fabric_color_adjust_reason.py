"""inventory fabric color adjust_reason supplier_name

Revision ID: c8f3a91b0d24
Revises: 795262ed971e
Create Date: 2026-11-05 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8f3a91b0d24"
down_revision: Union[str, Sequence[str], None] = "795262ed971e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("fabric_type", sa.String(length=60), nullable=True))
    op.add_column("products", sa.Column("color", sa.String(length=40), nullable=True))
    op.add_column("stock_movements", sa.Column("supplier_name", sa.String(length=100), nullable=True))
    op.add_column("stock_movements", sa.Column("adjust_reason", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        op.f("ck_stock_movements_adjust_reason_matches_reason"),
        "stock_movements",
        "(reason = 'adjust' AND adjust_reason IN "
        "('damaged', 'missing', 'measurement', 'supplier_return', 'count_correction'))"
        " OR (reason <> 'adjust' AND adjust_reason IS NULL)",
    )
    op.create_index(
        "ix_stock_movements_shop_id_product_id_created_at",
        "stock_movements",
        ["shop_id", "product_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_stock_movements_shop_id_product_id_created_at", table_name="stock_movements")
    op.drop_constraint(
        op.f("ck_stock_movements_adjust_reason_matches_reason"),
        "stock_movements",
        type_="check",
    )
    op.drop_column("stock_movements", "adjust_reason")
    op.drop_column("stock_movements", "supplier_name")
    op.drop_column("products", "color")
    op.drop_column("products", "fabric_type")
