"""merge heads

Revision ID: b43f64a9f01f
Revises: a91cae554ed3
Create Date: 2025-12-17 20:44:01.082621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b43f64a9f01f'
down_revision: Union[str, Sequence[str], None] = 'a91cae554ed3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
