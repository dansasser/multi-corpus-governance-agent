from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from mcg_agent.db.base import Base


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[Optional[str]] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(String)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hashtags: Mapped[Optional[list]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    mentions: Mapped[Optional[list]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    engagement: Mapped[Optional[int]] = mapped_column(Integer, default=0, index=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    comments: Mapped[list["Comment"]] = relationship(back_populates="post")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("posts.id"))
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[str] = mapped_column(String)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    engagement: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    post: Mapped[Post] = relationship(back_populates="comments")


__all__ = ["Post", "Comment"]

