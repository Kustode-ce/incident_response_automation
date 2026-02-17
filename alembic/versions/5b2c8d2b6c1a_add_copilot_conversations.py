"""add_copilot_conversations

Revision ID: 5b2c8d2b6c1a
Revises: 3554c2b72f76
Create Date: 2026-01-30 11:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "5b2c8d2b6c1a"
down_revision = "3554c2b72f76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "copilot_conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("incident_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=True),
        sa.Column("channel_id", sa.String(length=128), nullable=True),
        sa.Column("latest_summary", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            "user_id",
            "channel_id",
            "source",
            name="uq_copilot_conversation_identity",
        ),
    )
    op.create_index(op.f("ix_copilot_conversations_channel_id"), "copilot_conversations", ["channel_id"], unique=False)
    op.create_index(op.f("ix_copilot_conversations_incident_id"), "copilot_conversations", ["incident_id"], unique=False)
    op.create_index(op.f("ix_copilot_conversations_source"), "copilot_conversations", ["source"], unique=False)
    op.create_index(op.f("ix_copilot_conversations_user_id"), "copilot_conversations", ["user_id"], unique=False)

    op.create_table(
        "copilot_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["copilot_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_copilot_messages_conversation_id"), "copilot_messages", ["conversation_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_copilot_messages_conversation_id"), table_name="copilot_messages")
    op.drop_table("copilot_messages")
    op.drop_index(op.f("ix_copilot_conversations_user_id"), table_name="copilot_conversations")
    op.drop_index(op.f("ix_copilot_conversations_source"), table_name="copilot_conversations")
    op.drop_index(op.f("ix_copilot_conversations_incident_id"), table_name="copilot_conversations")
    op.drop_index(op.f("ix_copilot_conversations_channel_id"), table_name="copilot_conversations")
    op.drop_table("copilot_conversations")
