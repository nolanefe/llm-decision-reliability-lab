"""add experiment selection columns

Revision ID: 4c2bfe8b12e3
Revises: 9dff1dadb0ff
Create Date: 2026-07-27 23:05:54.599872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c2bfe8b12e3'
down_revision: Union[str, Sequence[str], None] = '9dff1dadb0ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Manually adjusted: SQLite requires a server_default for NOT NULL columns
    # added to an existing table, and batch mode for the ALTER TABLE to work.
    with op.batch_alter_table('experiments') as batch_op:
        batch_op.add_column(
            sa.Column(
                'dataset_item_ids', sa.JSON(), nullable=False, server_default='[]'
            )
        )
        batch_op.add_column(
            sa.Column(
                'prompt_version_ids', sa.JSON(), nullable=False, server_default='[]'
            )
        )
        batch_op.add_column(
            sa.Column('model_names', sa.JSON(), nullable=False, server_default='[]')
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('experiments') as batch_op:
        batch_op.drop_column('model_names')
        batch_op.drop_column('prompt_version_ids')
        batch_op.drop_column('dataset_item_ids')
