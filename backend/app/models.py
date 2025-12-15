"""
Database models for the Grok X Search application.
"""
from datetime import datetime
from typing import Optional, List, Any, Union
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field

Base = declarative_base()


# SQLAlchemy Models
class Post(Base):
    """X Post database model."""
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), unique=True, nullable=False, index=True)
    author_username = Column(String(64), nullable=False, index=True)
    author_display_name = Column(String(128))
    author_verified = Column(Boolean, default=False)
    author_followers = Column(Integer, default=0)
    
    content = Column(Text, nullable=False)
    content_tokens = Column(Text)  # Space-separated tokens for search
    
    created_at = Column(DateTime, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    views = Column(Integer, default=0)
    
    has_media = Column(Boolean, default=False)
    has_links = Column(Boolean, default=False)
    media_urls = Column(JSON, default=list)
    link_urls = Column(JSON, default=list)
    hashtags = Column(JSON, default=list)
    mentions = Column(JSON, default=list)
    
    # Grok-generated metadata
    grok_summary = Column(Text)
    grok_topics = Column(JSON, default=list)
    grok_sentiment = Column(String(32))
    grok_entities = Column(JSON, default=list)
    grok_keywords = Column(JSON, default=list)
    
    post_url = Column(String(256))
    
    __table_args__ = (
        Index('ix_posts_content_tokens', 'content_tokens'),
        Index('ix_posts_created_at', 'created_at'),
        Index('ix_posts_engagement', 'likes', 'retweets', 'replies'),
    )


class Account(Base):
    """X Account database model for tracking scraped accounts."""
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128))
    bio = Column(Text)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    profile_image_url = Column(String(512))
    
    last_scraped = Column(DateTime)
    posts_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SearchQuery(Base):
    """Search query history for analytics."""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    enhanced_query = Column(Text)
    results_count = Column(Integer, default=0)
    search_time_ms = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models for API
class PostCreate(BaseModel):
    """Schema for creating a post."""
    post_id: str
    author_username: str
    author_display_name: Optional[str] = None
    author_verified: bool = False
    author_followers: int = 0
    content: str
    created_at: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    has_media: bool = False
    has_links: bool = False
    media_urls: List[str] = []
    link_urls: List[str] = []
    hashtags: List[str] = []
    mentions: List[str] = []
    post_url: Optional[str] = None


class PostResponse(BaseModel):
    """Schema for post response."""
    id: int
    post_id: str
    author_username: str
    author_display_name: Optional[str]
    author_verified: bool
    author_followers: int
    content: str
    created_at: datetime
    scraped_at: datetime
    likes: int
    retweets: int
    replies: int
    views: int
    has_media: bool
    has_links: bool
    media_urls: List[str]
    link_urls: List[str]
    hashtags: List[str]
    mentions: List[str]
    grok_summary: Optional[str]
    grok_topics: List[str]
    grok_sentiment: Optional[str]
    grok_entities: Union[List[str], dict, None]  # Can be list or structured dict
    grok_keywords: List[str]
    post_url: Optional[str]
    relevance_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class AccountCreate(BaseModel):
    """Schema for creating an account."""
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    followers: int = 0
    following: int = 0
    verified: bool = False
    profile_image_url: Optional[str] = None


class AccountResponse(BaseModel):
    """Schema for account response."""
    id: int
    username: str
    display_name: Optional[str]
    bio: Optional[str]
    followers: int
    following: int
    verified: bool
    profile_image_url: Optional[str]
    last_scraped: Optional[datetime]
    posts_count: int
    is_active: bool
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Schema for search request."""
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="relevance", pattern="^(relevance|date|likes|retweets|views)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    author: Optional[str] = None
    has_media: Optional[bool] = None
    min_likes: Optional[int] = None
    use_grok_enhancement: bool = True
    # Search mode: keyword (BM25) or semantic (embeddings)
    search_mode: str = Field(default="keyword", pattern="^(keyword|semantic)$")


class SearchResult(BaseModel):
    """Schema for search result."""
    posts: List[PostResponse]
    total_count: int
    query: str
    enhanced_query: Optional[str]
    search_time_ms: float
    summary: Optional[str]
    key_insights: List[str] = []
    related_topics: List[str] = []
    search_mode: str = "keyword"  # keyword or semantic
    embedding_available: bool = True  # Whether embedding search is available


class GrokAnalysisResponse(BaseModel):
    """Schema for Grok analysis of a post."""
    summary: str
    topics: List[str]
    sentiment: str
    entities: List[str]
    keywords: List[str]

