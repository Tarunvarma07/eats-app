"""add_is_approved_to_users

Revision ID: 092f64a2dff2
Revises: c820737b101c
Create Date: 2026-06-23 17:03:01.433231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '092f64a2dff2'
down_revision: Union[str, Sequence[str], None] = 'c820737b101c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_approved')
