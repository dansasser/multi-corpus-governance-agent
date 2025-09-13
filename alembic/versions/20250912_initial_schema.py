"""Initial schema for personal, social, and published corpora

Revision ID: 20250912_initial
Revises: 
Create Date: 2025-09-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20250912_initial"
down_revision = None
branch_labels = None
depends_on = None


def _json_type():
    # Use JSONB on Postgres, JSON otherwise
    try:
        return postgresql.JSONB
    except Exception:  # pragma: no cover
        return sa.JSON


def upgrade() -> None:
    # Personal corpus: threads, messages, attachments
    op.create_table(
        "threads",
        sa.Column("thread_id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("participants", _json_type(), nullable=True),
        sa.Column("tags", _json_type(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("thread_id", sa.String(), sa.ForeignKey("threads.thread_id")),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(), index=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("channel", sa.String(), nullable=True),
        sa.Column("meta", _json_type(), nullable=True),
    )
    op.create_index("idx_messages_ts", "messages", ["ts"])  # for SQLite safety
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("messages.id")),
        sa.Column("kind", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("meta", _json_type(), nullable=True),
    )

    # Social corpus: posts, comments
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("platform", sa.String(), index=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(), index=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("hashtags", _json_type(), nullable=True),
        sa.Column("mentions", _json_type(), nullable=True),
        sa.Column("engagement", sa.Integer(), nullable=True),
        sa.Column("meta", _json_type(), nullable=True),
    )
    op.create_index("idx_posts_ts", "posts", ["ts"])  # for SQLite safety
    op.create_index("idx_posts_engagement", "posts", ["engagement"])  # for SQLite safety
    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id")),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime()),
        sa.Column("engagement", sa.Integer(), nullable=True),
    )

    # Published corpus: sources, articles
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("domain", sa.String(), unique=True),
        sa.Column("authority_score", sa.Float(), default=0.0),
    )
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(), index=True),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("tags", _json_type(), nullable=True),
        sa.Column("meta", _json_type(), nullable=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=True),
    )
    op.create_index("idx_articles_ts", "articles", ["ts"])  # for SQLite safety


def downgrade() -> None:
    # Reverse order for FK dependencies
    op.drop_table("articles")
    op.drop_table("sources")
    op.drop_table("comments")
    op.drop_index("idx_posts_engagement", table_name="posts")
    op.drop_index("idx_posts_ts", table_name="posts")
    op.drop_table("posts")
    op.drop_table("attachments")
    op.drop_index("idx_messages_ts", table_name="messages")
    op.drop_table("messages")
    op.drop_table("threads")

