"""add maintenance_tickets table

Revision ID: a1b2c3d4e5f6
Revises: c6a296383dbf
Create Date: 2026-08-05 11:15:00.000000

Creates the maintenance_tickets table which stores AI-generated and manual
maintenance work orders for transformers.

Key design decisions:
  - transformer_id stored as VARCHAR(64) string (no FK constraint) to avoid
    UUID dialect differences between SQLite (dev) and PostgreSQL (prod).
  - dedup_key has a UNIQUE constraint — prevents duplicate open tickets
    for the same transformer + priority combination.
  - dedup_key is cleared (set to NULL) when ticket is resolved, allowing
    a fresh ticket to be raised if the transformer degrades again.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c6a296383dbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'maintenance_tickets',

        # Primary key
        sa.Column('id', sa.UUID(), nullable=False),

        # Which transformer
        sa.Column('transformer_id', sa.String(length=64), nullable=False),

        # Ticket state
        sa.Column('status', sa.String(length=16), nullable=False, server_default='OPEN'),
        sa.Column('priority', sa.String(length=16), nullable=False, server_default='HIGH'),

        # Content
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('trigger_type', sa.String(length=16), nullable=False, server_default='AUTO'),
        sa.Column('health_score', sa.Numeric(precision=5, scale=2), nullable=True),

        # Resolution
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('outcome', sa.String(length=32), nullable=True),

        # Deduplication — prevents duplicate open tickets per transformer+priority
        sa.Column('dedup_key', sa.String(length=256), nullable=True),

        # Timestamps (auto-managed)
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dedup_key', name='uq_maintenance_tickets_dedup_key'),
    )

    # Index on transformer_id for fast lookups by transformer
    op.create_index(
        'idx_maintenance_tickets_transformer_id',
        'maintenance_tickets',
        ['transformer_id'],
        unique=False,
    )

    # Index on status for fast OPEN/RESOLVED filtering
    op.create_index(
        'idx_maintenance_tickets_status',
        'maintenance_tickets',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('idx_maintenance_tickets_status', table_name='maintenance_tickets')
    op.drop_index('idx_maintenance_tickets_transformer_id', table_name='maintenance_tickets')
    op.drop_table('maintenance_tickets')
