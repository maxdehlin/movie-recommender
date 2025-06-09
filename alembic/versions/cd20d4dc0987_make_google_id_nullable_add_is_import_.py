"""Make google_id nullable & add is_import flag

Revision ID: cd20d4dc0987
Revises: 
Create Date: 2025-06-09 14:32:15.003902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd20d4dc0987'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) add with a default so no existing NULLs
    op.add_column(
        'users',
        sa.Column(
            'is_import',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )
    # 2) alter the other two columns to become nullable
    op.alter_column('users', 'google_id',
                    existing_type=sa.String(),
                    nullable=True)
    op.alter_column('users', 'email',
                    existing_type=sa.String(),
                    nullable=True)
