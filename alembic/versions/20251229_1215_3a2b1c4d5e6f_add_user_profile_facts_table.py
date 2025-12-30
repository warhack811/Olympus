"""add_user_profile_facts_table

Revision ID: 3a2b1c4d5e6f
Revises: 8ff1f9138cea
Create Date: 2025-12-29 12:15:00.000000+00:00

Blueprint v1 Section 8 Layer 2: User Profile Layer (PostgreSQL)
- Versioned facts with LLM confirmation
- Cross-validation support
- Version history tracking
"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# Revision identifiers, used by Alembic.
revision: str = '3a2b1c4d5e6f'
down_revision: Union[str, None] = '8ff1f9138cea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_profile_facts table."""
    op.create_table(
        'user_profile_facts',
        # Primary key
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        
        # Fact data
        sa.Column('category', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('key', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        
        # LLM Confirmation
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False, server_default='inferred'),
        sa.Column('confirmed_by', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        
        # Versioning
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('superseded_by', sa.Integer(), nullable=True),
        sa.Column('supersedes', sa.Integer(), nullable=True),
        
        # Cross-validation
        sa.Column('conflicting_fact_id', sa.Integer(), nullable=True),
        sa.Column('conflict_resolved', sa.Boolean(), nullable=False, server_default='1'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        
        # Extra data (renamed from metadata - SQLAlchemy reserved)
        sa.Column('extra_data', sa.JSON(), nullable=True, server_default='{}'),
    )
    
    # Indexes for common queries
    op.create_index('ix_user_profile_facts_user_id', 'user_profile_facts', ['user_id'])
    op.create_index('ix_user_profile_facts_category', 'user_profile_facts', ['category'])
    op.create_index('ix_user_profile_facts_key', 'user_profile_facts', ['key'])
    op.create_index('ix_user_profile_facts_is_active', 'user_profile_facts', ['is_active'])
    op.create_index('ix_user_profile_facts_superseded_by', 'user_profile_facts', ['superseded_by'])
    
    # Composite index for common lookup pattern
    op.create_index(
        'ix_user_profile_facts_user_category_active', 
        'user_profile_facts', 
        ['user_id', 'category', 'is_active']
    )


def downgrade() -> None:
    """Drop user_profile_facts table."""
    # Drop indexes first
    op.drop_index('ix_user_profile_facts_user_category_active', 'user_profile_facts')
    op.drop_index('ix_user_profile_facts_superseded_by', 'user_profile_facts')
    op.drop_index('ix_user_profile_facts_is_active', 'user_profile_facts')
    op.drop_index('ix_user_profile_facts_key', 'user_profile_facts')
    op.drop_index('ix_user_profile_facts_category', 'user_profile_facts')
    op.drop_index('ix_user_profile_facts_user_id', 'user_profile_facts')
    
    # Drop table
    op.drop_table('user_profile_facts')
