from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel


class PersonalSearchFilters(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    role: Optional[Literal["user", "assistant"]] = None
    source: Optional[str] = None
    thread_id: Optional[str] = None
    tags: Optional[List[str]] = None


class SocialSearchFilters(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    platform: Optional[str] = None
    hashtags: Optional[List[str]] = None
    mentions: Optional[List[str]] = None


class PublishedSearchFilters(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None


class PersonalSnippet(BaseModel):
    snippet: str
    source: Literal["Personal"] = "Personal"
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str
    notes: str = ""
    thread_id: Optional[str] = None
    message_id: Optional[str] = None


class SocialSnippet(BaseModel):
    snippet: str
    source: Literal["Social"] = "Social"
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str
    notes: str = ""
    platform: Optional[str] = None


class PublishedSnippet(BaseModel):
    snippet: str
    source: Literal["Published"] = "Published"
    date: str
    tags: List[str] = []
    voice_terms: List[str] = []
    attribution: str
    notes: str = ""
    author: Optional[str] = None


class PersonalSearchResult(BaseModel):
    snippets: List[PersonalSnippet]


class SocialSearchResult(BaseModel):
    snippets: List[SocialSnippet]


class PublishedSearchResult(BaseModel):
    snippets: List[PublishedSnippet]


__all__ = [
    "PersonalSearchFilters",
    "SocialSearchFilters",
    "PublishedSearchFilters",
    "PersonalSnippet",
    "SocialSnippet",
    "PublishedSnippet",
    "PersonalSearchResult",
    "SocialSearchResult",
    "PublishedSearchResult",
]

