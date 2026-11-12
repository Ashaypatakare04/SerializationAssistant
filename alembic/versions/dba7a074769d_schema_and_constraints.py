"""schema_and_constraints

Revision ID: dba7a074769d
Revises: 5d971c9c3a00
Create Date: 2026-11-03 21:57:24.949815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dba7a074769d'
down_revision: Union[str, Sequence[str], None] = '5d971c9c3a00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with cross-database partial unique index for panel assets."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("assets"):
        # Initial schema creation is handled by Base.metadata.create_all in init_db()
        return
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_panel_asset_type "
        "ON assets(panel_id, asset_type) WHERE panel_id IS NOT NULL;"
    )


def downgrade() -> None:
    """Downgrade schema."""
    try:
        op.drop_index('uq_panel_asset_type', table_name='assets')
    except Exception:
        pass
