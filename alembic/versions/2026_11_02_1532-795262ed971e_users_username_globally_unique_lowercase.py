"""users username globally unique lowercase

Login sends only a username, so it must identify one user across all shops.
Existing usernames are lower-cased first. If two users end up with the same
username, the unique constraint fails and the whole migration rolls back
(Postgres DDL is transactional); rename one of them and run it again.

Revision ID: 795262ed971e
Revises: 0c1243e4221f
Create Date: 2026-11-02 15:32:28.457055

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '795262ed971e'
down_revision: Union[str, Sequence[str], None] = '0c1243e4221f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE users SET username = lower(trim(username)) WHERE username <> lower(trim(username))")
    op.drop_constraint(op.f('uq_users_shop_id_username'), 'users', type_='unique')
    op.create_unique_constraint(op.f('uq_users_username'), 'users', ['username'])
    op.create_check_constraint(
        op.f('ck_users_username_lowercase'), 'users', 'username = lower(username)'
    )


def downgrade() -> None:
    """Downgrade schema. Usernames stay lower-case (the original casing is not stored)."""
    op.drop_constraint(op.f('ck_users_username_lowercase'), 'users', type_='check')
    op.drop_constraint(op.f('uq_users_username'), 'users', type_='unique')
    op.create_unique_constraint(op.f('uq_users_shop_id_username'), 'users', ['shop_id', 'username'])
