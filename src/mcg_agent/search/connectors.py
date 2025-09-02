from __future__ import annotations

from datetime import datetime, timezone
from typing import List
import json

from sqlalchemy import select, func, text
from sqlalchemy.exc import SQLAlchemyError

from mcg_agent.db.session import get_session
from mcg_agent.db.models_personal import Message as PersonalMessage
from mcg_agent.db.models_social import Post as SocialPost
from mcg_agent.db.models_published import Article as PublishedArticle, Source as PublishedSource
from mcg_agent.search.models import (
    PersonalSearchFilters,
    PersonalSearchResult,
    PersonalSnippet,
    SocialSearchFilters,
    SocialSearchResult,
    SocialSnippet,
    PublishedSearchFilters,
    PublishedSearchResult,
    PublishedSnippet,
)
from mcg_agent.utils.cache import Cache


def _now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _trim(text: str, max_len: int = 240) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def query_personal(query: str, filters: PersonalSearchFilters, limit: int = 20) -> PersonalSearchResult:
    cache = Cache()
    ckey = Cache.key("personal", q=query, f=filters.model_dump(), l=limit)
    cached = cache.get(ckey)
    if cached:
        try:
            return PersonalSearchResult.model_validate(json.loads(cached))
        except Exception:
            pass

    snippets: List[PersonalSnippet] = []
    try:
        with get_session() as s:
            if s.bind and s.bind.dialect.name == "postgresql" and query:
                # Use FTS ranking in SQL
                stmt = (
                    select(
                        PersonalMessage.id,
                        PersonalMessage.thread_id,
                        PersonalMessage.role,
                        PersonalMessage.content,
                        PersonalMessage.ts,
                        text("ts_rank_cd(content_tsv, plainto_tsquery('english', :q)) AS rank"),
                    )
                    .where(text("content_tsv @@ plainto_tsquery('english', :q)")).params(q=query)
                    .order_by(text("rank DESC"), PersonalMessage.ts.desc())
                    .limit(limit)
                )
                rows = s.execute(stmt).all()
                for r in rows:
                    m_id, thread_id, role, content, ts, _rank = r
                    snippets.append(
                        PersonalSnippet(
                            snippet=_trim(content or ""),
                            date=(ts.date().isoformat() if ts else _now_date()),
                            tags=[],
                            voice_terms=[],
                            attribution=f"personal://messages/{m_id}",
                            notes="",
                            thread_id=thread_id,
                            message_id=str(m_id),
                        )
                    )
            else:
                # Fallback: ILIKE and recency
                stmt = select(PersonalMessage)
                if query:
                    like = f"%{query}%"
                    stmt = stmt.where(PersonalMessage.content.ilike(like))
                if filters.role:
                    stmt = stmt.where(PersonalMessage.role == filters.role)
                if filters.thread_id:
                    stmt = stmt.where(PersonalMessage.thread_id == filters.thread_id)
                if filters.date_from:
                    stmt = stmt.where(PersonalMessage.ts >= filters.date_from)
                if filters.date_to:
                    stmt = stmt.where(PersonalMessage.ts <= filters.date_to)
                stmt = stmt.order_by(PersonalMessage.ts.desc()).limit(limit)
                rows = s.execute(stmt).scalars().all()
                for m in rows:
                    snippets.append(
                        PersonalSnippet(
                            snippet=_trim(m.content or ""),
                            date=(m.ts.date().isoformat() if m.ts else _now_date()),
                            tags=[],
                            voice_terms=[],
                            attribution=f"personal://messages/{m.id}",
                            notes="",
                            thread_id=m.thread_id,
                            message_id=str(m.id),
                        )
                    )
    except SQLAlchemyError:
        # Fail closed: return empty result without raising to callers
        pass
    result = PersonalSearchResult(snippets=snippets)
    try:
        cache.set(ckey, result.model_dump_json())
    except Exception:
        pass
    return result


def query_social(query: str, filters: SocialSearchFilters, limit: int = 30) -> SocialSearchResult:
    cache = Cache()
    ckey = Cache.key("social", q=query, f=filters.model_dump(), l=limit)
    cached = cache.get(ckey)
    if cached:
        try:
            return SocialSearchResult.model_validate(json.loads(cached))
        except Exception:
            pass
    snippets: List[SocialSnippet] = []
    try:
        with get_session() as s:
            if s.bind and s.bind.dialect.name == "postgresql" and query:
                rank = text("ts_rank_cd(content_tsv, plainto_tsquery('english', :q)) + 0.05 * log(1 + coalesce(engagement,0))")
                stmt = (
                    select(
                        SocialPost.id,
                        SocialPost.platform,
                        SocialPost.content,
                        SocialPost.ts,
                        SocialPost.url,
                        SocialPost.hashtags,
                        rank.label("rank"),
                    )
                    .where(text("content_tsv @@ plainto_tsquery('english', :q)")).params(q=query)
                    .order_by(text("rank DESC"), SocialPost.ts.desc())
                    .limit(limit)
                )
                rows = s.execute(stmt).all()
                for r in rows:
                    p_id, platform, content, ts, url, hashtags, _rank = r
                    snippets.append(
                        SocialSnippet(
                            snippet=_trim(content or "", 180),
                            date=(ts.date().isoformat() if ts else _now_date()),
                            tags=hashtags or [],
                            voice_terms=[],
                            attribution=url or f"social://posts/{p_id}",
                            notes="",
                            platform=platform,
                        )
                    )
            else:
                stmt = select(SocialPost)
                if query:
                    like = f"%{query}%"
                    stmt = stmt.where(SocialPost.content.ilike(like))
                if filters.platform:
                    stmt = stmt.where(SocialPost.platform == filters.platform)
                if filters.date_from:
                    stmt = stmt.where(SocialPost.ts >= filters.date_from)
                if filters.date_to:
                    stmt = stmt.where(SocialPost.ts <= filters.date_to)
                stmt = stmt.order_by(SocialPost.ts.desc(), SocialPost.engagement.desc()).limit(limit)
                rows = s.execute(stmt).scalars().all()
                for p in rows:
                    snippets.append(
                        SocialSnippet(
                            snippet=_trim(p.content or "", 180),
                            date=(p.ts.date().isoformat() if p.ts else _now_date()),
                            tags=(p.hashtags or []),
                            voice_terms=[],
                            attribution=p.url or f"social://posts/{p.id}",
                            notes="",
                            platform=p.platform,
                        )
                    )
    except SQLAlchemyError:
        pass
    result = SocialSearchResult(snippets=snippets)
    try:
        cache.set(ckey, result.model_dump_json())
    except Exception:
        pass
    return result


def query_published(
    query: str, filters: PublishedSearchFilters, limit: int = 20
) -> PublishedSearchResult:
    cache = Cache()
    ckey = Cache.key("published", q=query, f=filters.model_dump(), l=limit)
    cached = cache.get(ckey)
    if cached:
        try:
            return PublishedSearchResult.model_validate(json.loads(cached))
        except Exception:
            pass
    snippets: List[PublishedSnippet] = []
    try:
        with get_session() as s:
            if s.bind and s.bind.dialect.name == "postgresql" and query:
                rank = text(
                    "ts_rank_cd(articles.content_tsv, plainto_tsquery('english', :q)) + 0.1 * coalesce(sources.authority_score,0)"
                )
                stmt = (
                    select(
                        PublishedArticle.id,
                        PublishedArticle.title,
                        PublishedArticle.content,
                        PublishedArticle.ts,
                        PublishedArticle.author,
                        PublishedArticle.url,
                        PublishedArticle.tags,
                        rank.label("rank"),
                    )
                    .select_from(PublishedArticle.__table__.join(PublishedSource.__table__, PublishedArticle.source_id == PublishedSource.id, isouter=True))
                    .where(text("articles.content_tsv @@ plainto_tsquery('english', :q)")).params(q=query)
                    .order_by(text("rank DESC"), PublishedArticle.ts.desc())
                    .limit(limit)
                )
                rows = s.execute(stmt).all()
                for r in rows:
                    a_id, title, content, ts, author, url, tags, _rank = r
                    snippets.append(
                        PublishedSnippet(
                            snippet=_trim(content or "", 360),
                            date=(ts.date().isoformat() if ts else _now_date()),
                            tags=tags or [],
                            voice_terms=[],
                            attribution=url or f"published://articles/{a_id}",
                            notes="",
                            author=author,
                        )
                    )
            else:
                stmt = select(PublishedArticle)
                if query:
                    like = f"%{query}%"
                    stmt = stmt.where(PublishedArticle.content.ilike(like))
                if filters.author:
                    stmt = stmt.where(PublishedArticle.author == filters.author)
                if filters.date_from:
                    stmt = stmt.where(PublishedArticle.ts >= filters.date_from)
                if filters.date_to:
                    stmt = stmt.where(PublishedArticle.ts <= filters.date_to)
                stmt = stmt.order_by(PublishedArticle.ts.desc()).limit(limit)
                rows = s.execute(stmt).scalars().all()
                for a in rows:
                    snippets.append(
                        PublishedSnippet(
                            snippet=_trim(a.content or "", 360),
                            date=(a.ts.date().isoformat() if a.ts else _now_date()),
                            tags=a.tags or [],
                            voice_terms=[],
                            attribution=a.url or f"published://articles/{a.id}",
                            notes="",
                            author=a.author,
                        )
                    )
    except SQLAlchemyError:
        pass
    result = PublishedSearchResult(snippets=snippets)
    try:
        cache.set(ckey, result.model_dump_json())
    except Exception:
        pass
    return result


__all__ = [
    "query_personal",
    "query_social",
    "query_published",
]
