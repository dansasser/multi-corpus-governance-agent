"""Create FTS generated columns and indexes

Revision ID: 20250902_fts
Revises: 
Create Date: 2025-09-02
"""
from __future__ import annotations

from alembic import op


revision = "20250902_fts"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only apply to PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # Personal.messages FTS
    op.execute(
        """
        ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_tsv ON messages USING GIN (content_tsv);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages (ts);")

    # Social.posts FTS
    op.execute(
        """
        ALTER TABLE posts
        ADD COLUMN IF NOT EXISTS content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_tsv ON posts USING GIN (content_tsv);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_posts_ts ON posts (ts);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_engagement ON posts (engagement);")
    # Hashtags/tags jsonb GIN
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_hashtags_gin ON posts USING GIN ((hashtags) jsonb_path_ops);"
    )

    # Published.articles FTS
    op.execute(
        """
        ALTER TABLE articles
        ADD COLUMN IF NOT EXISTS content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_tsv ON articles USING GIN (content_tsv);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_articles_ts ON articles (ts);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_tags_gin ON articles USING GIN ((tags) jsonb_path_ops);"
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    # We don't drop columns to avoid data loss; drop indexes only
    op.execute("DROP INDEX IF EXISTS idx_messages_tsv;")
    op.execute("DROP INDEX IF EXISTS idx_messages_ts;")
    op.execute("DROP INDEX IF EXISTS idx_posts_tsv;")
    op.execute("DROP INDEX IF EXISTS idx_posts_ts;")
    op.execute("DROP INDEX IF EXISTS idx_posts_engagement;")
    op.execute("DROP INDEX IF EXISTS idx_posts_hashtags_gin;")
    op.execute("DROP INDEX IF EXISTS idx_articles_tsv;")
    op.execute("DROP INDEX IF EXISTS idx_articles_ts;")
    op.execute("DROP INDEX IF EXISTS idx_articles_tags_gin;")

