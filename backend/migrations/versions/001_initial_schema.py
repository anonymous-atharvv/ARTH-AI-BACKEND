"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-06-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), nullable=True),
        sa.Column('business_type', sa.String(length=100), nullable=True),
        sa.Column('business_location', sa.String(length=200), nullable=True),
        sa.Column('onboarding_complete', sa.Boolean(), nullable=True),
        sa.Column('whatsapp_session_state', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('updated_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )

    # Categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name_en', sa.String(length=100), nullable=False),
        sa.Column('name_hi', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('parent_code', sa.String(length=50), nullable=True),
        sa.Column('icon', sa.String(length=10), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # Transactions table
    op.create_table(
        'transactions',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('user_id', sa.CHAR(length=36), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('category_code', sa.String(length=50), nullable=True),
        sa.Column('counterparty', sa.String(length=200), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('payment_method', sa.String(length=20), nullable=True),
        sa.Column('transaction_date', sa.String(length=10), nullable=False),
        sa.Column('transaction_time', sa.String(length=8), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('raw_input', sa.Text(), nullable=True),
        sa.Column('extracted_data', sa.JSON(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('updated_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_transactions_user_date', 'transactions', ['user_id', 'transaction_date'], unique=False)
    op.create_index(op.f('ix_transactions_category_code'), 'transactions', ['category_code'], unique=False)
    op.create_index(op.f('ix_transactions_transaction_date'), 'transactions', ['transaction_date'], unique=False)
    op.create_index(op.f('ix_transactions_user_id'), 'transactions', ['user_id'], unique=False)

    # WhatsApp Sessions table
    op.create_table(
        'whatsapp_sessions',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('user_id', sa.CHAR(length=36), nullable=True),
        sa.Column('phone_number', sa.String(length=15), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False),
        sa.Column('pending_transaction', sa.JSON(), nullable=True),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('last_activity', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )
    op.create_index('idx_whatsapp_sessions_phone', 'whatsapp_sessions', ['phone_number'], unique=False)

    # Documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('user_id', sa.CHAR(length=36), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('period_start', sa.String(), nullable=True),
        sa.Column('period_end', sa.String(), nullable=True),
        sa.Column('arthascore_at_generation', sa.Integer(), nullable=True),
        sa.Column('summary_data', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.String(), nullable=True),
        sa.Column('expires_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # ArthScoreHistory table
    op.create_table(
        'arthascore_history',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('user_id', sa.CHAR(length=36), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('income_regularity', sa.Integer(), nullable=True),
        sa.Column('growth_trajectory', sa.Integer(), nullable=True),
        sa.Column('expense_control', sa.Integer(), nullable=True),
        sa.Column('transaction_volume', sa.Integer(), nullable=True),
        sa.Column('business_longevity', sa.Integer(), nullable=True),
        sa.Column('payment_consistency', sa.Integer(), nullable=True),
        sa.Column('data_completeness', sa.Integer(), nullable=True),
        sa.Column('data_points', sa.Integer(), nullable=True),
        sa.Column('period_days', sa.Integer(), nullable=True),
        sa.Column('snapshot_data', sa.JSON(), nullable=True),
        sa.Column('calculated_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Analytics Cache table
    op.create_table(
        'analytics_cache',
        sa.Column('user_id', sa.CHAR(length=36), nullable=False),
        sa.Column('mtd_income', sa.Float(), nullable=True),
        sa.Column('mtd_expenses', sa.Float(), nullable=True),
        sa.Column('mtd_net_profit', sa.Float(), nullable=True),
        sa.Column('wtd_income', sa.Float(), nullable=True),
        sa.Column('wtd_expenses', sa.Float(), nullable=True),
        sa.Column('total_transactions', sa.Integer(), nullable=True),
        sa.Column('first_transaction_date', sa.String(), nullable=True),
        sa.Column('current_arthascore', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # Insights Log table
    op.create_table(
        'insights_log',
        sa.Column('id', sa.CHAR(length=36), nullable=False),
        sa.Column('user_id', sa.CHAR(length=36), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=True),
        sa.Column('insight_data', sa.JSON(), nullable=True),
        sa.Column('sent_at', sa.String(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_table('insights_log')
    op.drop_table('analytics_cache')
    op.drop_table('arthascore_history')
    op.drop_table('documents')
    op.drop_index('idx_whatsapp_sessions_phone', table_name='whatsapp_sessions')
    op.drop_table('whatsapp_sessions')
    op.drop_index(op.f('ix_transactions_user_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_transaction_date'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_category_code'), table_name='transactions')
    op.drop_index('idx_transactions_user_date', table_name='transactions')
    op.drop_table('transactions')
    op.drop_table('categories')
    op.drop_table('users')
