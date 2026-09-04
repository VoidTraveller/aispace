"""add unique constraint on room name

Revision ID: 5ba25211de56
Revises: e13b7e205502
Create Date: 2026-09-04 11:02:50.930453

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ba25211de56'
down_revision: Union[str, Sequence[str], None] = 'e13b7e205502'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_rooms_name', 'rooms', ['name'])


def downgrade() -> None:
    op.drop_constraint('uq_rooms_name', 'rooms', type_='unique')
