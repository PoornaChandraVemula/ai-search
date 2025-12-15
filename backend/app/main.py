"""
Main FastAPI application for Grok X Search.
"""
import logging
import json
import os
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from .config import settings
from .database import init_db, get_db, SessionLocal
from .models import (
    Post, Account, SearchQuery,
    PostResponse, PostCreate, AccountResponse, AccountCreate,
    SearchRequest, SearchResult, GrokAnalysisResponse
)
from .scraper import scraper
from .search import search_engine
from .grok_client import grok_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Path to sample data file (in app directory to avoid volume mount issues)
SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), "sample_posts.json")


def load_sample_data(db: Session) -> dict:
    """
    Load sample data from the local JSON file into the database.
    Returns stats about what was imported.
    """
    if not os.path.exists(SAMPLE_DATA_PATH):
        logger.warning(f"Sample data file not found: {SAMPLE_DATA_PATH}")
        return {"imported": 0, "skipped": 0, "error": "Sample data file not found"}
    
    try:
        with open(SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load sample data: {e}")
        return {"imported": 0, "skipped": 0, "error": str(e)}
    
    posts_data = data.get("posts", data) if isinstance(data, dict) else data
    
    if not isinstance(posts_data, list):
        return {"imported": 0, "skipped": 0, "error": "Invalid data format"}
    
    imported = 0
    skipped = 0
    
    for post_data in posts_data:
        try:
            created_at = post_data.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except:
                    created_at = datetime.utcnow()
            elif created_at is None:
                created_at = datetime.utcnow()
            
            post_id = post_data.get("post_id")
            if not post_id:
                import hashlib
                content = post_data.get("content", "")
                author = post_data.get("author_username", "unknown")
                post_id = hashlib.sha256(f"{author}:{content}".encode()).hexdigest()[:16]
            
            existing = db.query(Post).filter(Post.post_id == post_id).first()
            if existing:
                skipped += 1
                continue
            
            post = Post(
                post_id=post_id,
                author_username=post_data.get("author_username", "unknown"),
                author_display_name=post_data.get("author_display_name"),
                author_verified=post_data.get("author_verified", False),
                author_followers=post_data.get("author_followers", 0),
                content=post_data.get("content", ""),
                created_at=created_at,
                likes=post_data.get("likes", 0),
                retweets=post_data.get("retweets", 0),
                replies=post_data.get("replies", 0),
                views=post_data.get("views", 0),
                has_media=post_data.get("has_media", False),
                has_links=post_data.get("has_links", False),
                media_urls=post_data.get("media_urls", []),
                link_urls=post_data.get("link_urls", []),
                hashtags=post_data.get("hashtags", []),
                mentions=post_data.get("mentions", []),
                grok_summary=post_data.get("grok_summary"),
                grok_topics=post_data.get("grok_topics", []),
                grok_sentiment=post_data.get("grok_sentiment"),
                grok_entities=post_data.get("grok_entities", []),
                grok_keywords=post_data.get("grok_keywords", []),
                post_url=post_data.get("post_url")
            )
            db.add(post)
            imported += 1
        except Exception as e:
            logger.warning(f"Failed to import post: {e}")
            skipped += 1
    
    db.commit()
    return {"imported": imported, "skipped": skipped}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    logger.info("Database initialized")
    
    # Auto-populate with sample data if database is empty
    db = SessionLocal()
    try:
        post_count = db.query(Post).count()
        if post_count == 0:
            logger.info("Database is empty, loading sample data...")
            result = load_sample_data(db)
            if result.get("imported", 0) > 0:
                logger.info(f"Loaded {result['imported']} sample posts")
                # Build search index
                search_engine.build_index(db)
                logger.info("Search index built")
            else:
                logger.info("No sample data loaded (file may not exist)")
        else:
            logger.info(f"Database has {post_count} posts, skipping sample data load")
            # Ensure search index is built
            if search_engine.doc_count == 0:
                search_engine.build_index(db)
    finally:
        db.close()
    
    yield
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Grok-powered intelligent search system for X (Twitter) posts",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "grok_configured": bool(settings.XAI_API_KEY)
    }


# Search endpoints
@app.post("/api/search", response_model=SearchResult)
async def search_posts(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search posts with Grok-powered query enhancement and summarization.
    
    Supports:
    - Natural language queries
    - Boolean operators (AND, OR)
    - Filters: from:username, min_likes:N, has:media, has:links
    - Quoted phrases for exact matching
    """
    try:
        result = await search_engine.search(db, request)
        
        # Log search query for analytics
        search_log = SearchQuery(
            query=request.query,
            enhanced_query=result.enhanced_query,
            results_count=result.total_count,
            search_time_ms=result.search_time_ms
        )
        db.add(search_log)
        db.commit()
        
        return result
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on partial query."""
    try:
        # Get recent similar queries
        recent_queries = db.query(SearchQuery).filter(
            SearchQuery.query.ilike(f"%{query}%")
        ).order_by(SearchQuery.created_at.desc()).limit(5).all()
        
        suggestions = [q.query for q in recent_queries]
        
        # Get matching authors
        authors = db.query(Account.username).filter(
            Account.username.ilike(f"%{query}%")
        ).limit(5).all()
        suggestions.extend([f"from:{a[0]}" for a in authors])
        
        # Get matching hashtags from posts
        posts_with_hashtags = db.query(Post.hashtags).filter(
            Post.content.ilike(f"%#{query}%")
        ).limit(10).all()
        
        for post in posts_with_hashtags:
            if post.hashtags:
                for tag in post.hashtags:
                    if query.lower() in tag.lower():
                        suggestions.append(f"#{tag}")
        
        return {"suggestions": list(set(suggestions))[:10]}
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return {"suggestions": []}


@app.post("/api/search/clarify")
async def clarify_query(query: str = Query(..., min_length=1)):
    """Get clarification for ambiguous queries using Grok."""
    try:
        result = await grok_client.clarify_ambiguous_query(query)
        return result
    except Exception as e:
        logger.error(f"Clarification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Post endpoints
@app.get("/api/posts", response_model=List[PostResponse])
async def get_posts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    author: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get paginated list of posts."""
    query = db.query(Post)
    
    if author:
        query = query.filter(Post.author_username.ilike(f"%{author}%"))
    
    posts = query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
    return [PostResponse.model_validate(p) for p in posts]


@app.get("/api/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: str, db: Session = Depends(get_db)):
    """Get a specific post by ID."""
    post = db.query(Post).filter(Post.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse.model_validate(post)


class PostImport(BaseModel):
    """Schema for importing a post."""
    content: str
    author_username: str
    author_display_name: Optional[str] = None
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    has_media: bool = False


class BulkPostImport(BaseModel):
    """Schema for bulk importing posts."""
    posts: List[PostImport]


@app.post("/api/posts/import", response_model=PostResponse)
async def import_post(
    post_data: PostImport,
    db: Session = Depends(get_db)
):
    """
    Import a single post manually.
    Use this to add posts for testing or from external sources.
    """
    post_create = scraper.create_post_from_data(
        content=post_data.content,
        author_username=post_data.author_username,
        author_display_name=post_data.author_display_name,
        likes=post_data.likes,
        retweets=post_data.retweets,
        replies=post_data.replies,
        views=post_data.views,
        has_media=post_data.has_media
    )
    
    # Check if already exists
    existing = db.query(Post).filter(Post.post_id == post_create.post_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Post already exists")
    
    post = Post(**post_create.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    
    # Add to search index
    search_engine.add_post(post)
    
    return PostResponse.model_validate(post)


@app.post("/api/posts/import/bulk")
async def import_posts_bulk(
    data: BulkPostImport,
    db: Session = Depends(get_db)
):
    """
    Import multiple posts at once.
    """
    imported = 0
    skipped = 0
    
    for post_data in data.posts:
        post_create = scraper.create_post_from_data(
            content=post_data.content,
            author_username=post_data.author_username,
            author_display_name=post_data.author_display_name,
            likes=post_data.likes,
            retweets=post_data.retweets,
            replies=post_data.replies,
            views=post_data.views,
            has_media=post_data.has_media
        )
        
        existing = db.query(Post).filter(Post.post_id == post_create.post_id).first()
        if existing:
            skipped += 1
            continue
        
        post = Post(**post_create.model_dump())
        db.add(post)
        imported += 1
    
    db.commit()
    
    # Rebuild search index
    search_engine.build_index(db)
    
    return {
        "message": f"Imported {imported} posts, skipped {skipped} duplicates",
        "imported": imported,
        "skipped": skipped
    }


@app.post("/api/posts/{post_id}/analyze", response_model=GrokAnalysisResponse)
async def analyze_post(post_id: str, db: Session = Depends(get_db)):
    """Analyze a post using Grok to generate rich metadata."""
    post = db.query(Post).filter(Post.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    try:
        analysis = await grok_client.analyze_post(post.content, post.author_username)
        
        # Update post with analysis
        post.grok_summary = analysis.get("summary")
        post.grok_topics = analysis.get("topics", [])
        post.grok_sentiment = analysis.get("sentiment")
        post.grok_entities = analysis.get("entities", [])
        post.grok_keywords = analysis.get("keywords", [])
        
        db.commit()
        
        # Update search index
        search_engine.add_post(post)
        
        return GrokAnalysisResponse(**analysis)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/posts/analyze-all")
async def analyze_all_posts(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    Batch analyze posts that don't have Grok metadata yet.
    Extracts keywords, topics, summary for each post.
    """
    # Find posts without Grok analysis (check grok_summary which is a simple Text field)
    unanalyzed = db.query(Post).filter(
        Post.grok_summary == None
    ).limit(limit).all()
    
    analyzed_count = 0
    failed_count = 0
    
    for post in unanalyzed:
        try:
            analysis = await grok_client.analyze_post(post.content, post.author_username)
            post.grok_summary = analysis.get("summary")
            post.grok_topics = analysis.get("topics", [])
            post.grok_sentiment = analysis.get("sentiment")
            post.grok_entities = analysis.get("entities", [])
            post.grok_keywords = analysis.get("keywords", [])
            analyzed_count += 1
            logger.info(f"Analyzed post {post.post_id}")
        except Exception as e:
            logger.warning(f"Failed to analyze post {post.post_id}: {e}")
            failed_count += 1
    
    db.commit()
    
    # Rebuild search index to include new metadata
    search_engine.build_index(db)
    
    remaining = db.query(Post).filter(Post.grok_summary == None).count()
    
    return {
        "message": f"Analyzed {analyzed_count} posts, {failed_count} failed",
        "analyzed": analyzed_count,
        "failed": failed_count,
        "remaining": remaining
    }


# Account endpoints
@app.get("/api/accounts", response_model=List[AccountResponse])
async def get_accounts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get paginated list of scraped accounts."""
    accounts = db.query(Account).order_by(Account.followers.desc()).offset(offset).limit(limit).all()
    return [AccountResponse.model_validate(a) for a in accounts]


@app.get("/api/accounts/popular")
async def get_popular_accounts():
    """Get list of popular accounts available for scraping."""
    return {"accounts": scraper.get_popular_accounts()}


@app.get("/api/accounts/{username}", response_model=AccountResponse)
async def get_account(username: str, db: Session = Depends(get_db)):
    """Get a specific account by username."""
    account = db.query(Account).filter(Account.username.ilike(username)).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.model_validate(account)


@app.get("/api/accounts/{username}/posts", response_model=List[PostResponse])
async def get_account_posts(
    username: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get posts from a specific account."""
    posts = db.query(Post).filter(
        Post.author_username.ilike(username)
    ).order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
    return [PostResponse.model_validate(p) for p in posts]


# Scraping endpoints
@app.post("/api/scrape/{username}")
async def scrape_account(
    username: str,
    background_tasks: BackgroundTasks,
    max_posts: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Scrape posts from an X account.
    Note: Uses simulated data for demo purposes.
    """
    try:
        account_data, posts_data = await scraper.scrape_account(username, max_posts)
        
        # Save account
        existing_account = db.query(Account).filter(
            Account.username.ilike(account_data.username)
        ).first()
        
        if existing_account:
            for key, value in account_data.model_dump().items():
                setattr(existing_account, key, value)
            existing_account.last_scraped = datetime.utcnow()
            account = existing_account
        else:
            account = Account(**account_data.model_dump())
            account.last_scraped = datetime.utcnow()
            db.add(account)
        
        # Save posts
        new_posts = 0
        new_post_objects = []
        for post_data in posts_data:
            existing_post = db.query(Post).filter(
                Post.post_id == post_data.post_id
            ).first()
            
            if not existing_post:
                post = Post(**post_data.model_dump())
                db.add(post)
                new_post_objects.append(post)
                new_posts += 1
        
        db.commit()
        
        # Analyze new posts with Grok and add to search index
        for post in new_post_objects:
            try:
                # Analyze post with Grok to extract keywords, topics, summary
                analysis = await grok_client.analyze_post(post.content, post.author_username)
                post.grok_summary = analysis.get("summary")
                post.grok_topics = analysis.get("topics", [])
                post.grok_sentiment = analysis.get("sentiment")
                post.grok_entities = analysis.get("entities", [])
                post.grok_keywords = analysis.get("keywords", [])
                db.commit()
                logger.info(f"Analyzed post {post.post_id} with Grok")
            except Exception as e:
                logger.warning(f"Grok analysis failed for post {post.post_id}: {e}")
            
            # Add to search index (with Grok metadata if available)
            search_engine.add_post(post)
        
        # Update account post count
        account.posts_count = db.query(Post).filter(
            Post.author_username.ilike(username)
        ).count()
        db.commit()
        
        return {
            "message": f"Scraped {len(posts_data)} posts from @{username}",
            "new_posts": new_posts,
            "total_posts": account.posts_count,
            "account": AccountResponse.model_validate(account)
        }
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape/batch")
async def scrape_multiple_accounts(
    usernames: List[str],
    background_tasks: BackgroundTasks,
    max_posts_per_account: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Scrape posts from multiple accounts."""
    results = []
    
    for username in usernames[:10]:  # Limit to 10 accounts
        try:
            account_data, posts_data = await scraper.scrape_account(
                username, max_posts_per_account
            )
            
            # Save account
            existing_account = db.query(Account).filter(
                Account.username.ilike(account_data.username)
            ).first()
            
            if existing_account:
                for key, value in account_data.model_dump().items():
                    setattr(existing_account, key, value)
                existing_account.last_scraped = datetime.utcnow()
            else:
                account = Account(**account_data.model_dump())
                account.last_scraped = datetime.utcnow()
                db.add(account)
            
            # Save posts
            new_posts = 0
            new_post_objects = []
            for post_data in posts_data:
                existing_post = db.query(Post).filter(
                    Post.post_id == post_data.post_id
                ).first()
                
                if not existing_post:
                    post = Post(**post_data.model_dump())
                    db.add(post)
                    new_post_objects.append(post)
                    new_posts += 1
            
            db.commit()
            
            # Analyze new posts with Grok
            for post in new_post_objects:
                try:
                    analysis = await grok_client.analyze_post(post.content, post.author_username)
                    post.grok_summary = analysis.get("summary")
                    post.grok_topics = analysis.get("topics", [])
                    post.grok_sentiment = analysis.get("sentiment")
                    post.grok_entities = analysis.get("entities", [])
                    post.grok_keywords = analysis.get("keywords", [])
                except Exception as e:
                    logger.warning(f"Grok analysis failed for post {post.post_id}: {e}")
            
            db.commit()
            
            results.append({
                "username": username,
                "posts_scraped": len(posts_data),
                "new_posts": new_posts,
                "status": "success"
            })
            
        except Exception as e:
            logger.error(f"Error scraping @{username}: {e}")
            results.append({
                "username": username,
                "error": str(e),
                "status": "failed"
            })
    
    db.commit()
    
    # Rebuild search index in background
    background_tasks.add_task(search_engine.build_index, db)
    
    return {
        "message": f"Batch scraping completed for {len(usernames)} accounts",
        "results": results
    }


# Analytics endpoints
@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    total_posts = db.query(Post).count()
    total_accounts = db.query(Account).count()
    total_searches = db.query(SearchQuery).count()
    
    # Top authors by post count
    from sqlalchemy import func
    top_authors = db.query(
        Post.author_username,
        func.count(Post.id).label('count')
    ).group_by(Post.author_username).order_by(func.count(Post.id).desc()).limit(10).all()
    
    # Recent searches
    recent_searches = db.query(SearchQuery).order_by(
        SearchQuery.created_at.desc()
    ).limit(10).all()
    
    return {
        "total_posts": total_posts,
        "total_accounts": total_accounts,
        "total_searches": total_searches,
        "top_authors": [{"username": a[0], "post_count": a[1]} for a in top_authors],
        "recent_searches": [
            {
                "query": s.query,
                "results_count": s.results_count,
                "search_time_ms": s.search_time_ms,
                "created_at": s.created_at.isoformat()
            }
            for s in recent_searches
        ],
        "index_size": search_engine.doc_count
    }


# Admin endpoints
@app.delete("/api/admin/reset")
async def reset_database(db: Session = Depends(get_db)):
    """
    Clear all data from the database.
    WARNING: This deletes all posts, accounts, and search history!
    """
    try:
        # Delete all records
        db.query(Post).delete()
        db.query(Account).delete()
        db.query(SearchQuery).delete()
        db.commit()
        
        # Rebuild empty search index
        search_engine.build_index(db)
        
        logger.info("Database reset complete")
        return {
            "message": "Database cleared successfully",
            "posts_deleted": True,
            "accounts_deleted": True,
            "search_history_deleted": True
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Reset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Data Export/Import endpoints
@app.get("/api/data/export")
async def export_data(
    db: Session = Depends(get_db),
    format: str = Query(default="json", pattern="^(json)$")
):
    """
    Export all posts as a JSON file.
    
    This creates a downloadable file that can be:
    - Hosted on GitHub for others to use
    - Used as a backup
    - Shared with others
    """
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    
    export_data = {
        "version": settings.APP_VERSION,
        "exported_at": datetime.utcnow().isoformat(),
        "total_posts": len(posts),
        "posts": []
    }
    
    for post in posts:
        post_dict = {
            "post_id": post.post_id,
            "author_username": post.author_username,
            "author_display_name": post.author_display_name,
            "author_verified": post.author_verified,
            "author_followers": post.author_followers,
            "content": post.content,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "likes": post.likes,
            "retweets": post.retweets,
            "replies": post.replies,
            "views": post.views,
            "has_media": post.has_media,
            "has_links": post.has_links,
            "media_urls": post.media_urls or [],
            "link_urls": post.link_urls or [],
            "hashtags": post.hashtags or [],
            "mentions": post.mentions or [],
            "grok_summary": post.grok_summary,
            "grok_topics": post.grok_topics or [],
            "grok_sentiment": post.grok_sentiment,
            "grok_entities": post.grok_entities or [],
            "grok_keywords": post.grok_keywords or [],
            "post_url": post.post_url
        }
        export_data["posts"].append(post_dict)
    
    json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=grok_x_search_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )


class ImportFromURLRequest(BaseModel):
    """Schema for importing data from URL."""
    url: str
    replace_existing: bool = False


# Sample data is loaded from local file: data/sample_posts.json
# Can also be hosted on GitHub and imported via /api/data/import-url


@app.post("/api/data/import-url")
async def import_from_url(
    request: ImportFromURLRequest,
    db: Session = Depends(get_db)
):
    """
    Import posts from a JSON file hosted at a URL (e.g., GitHub raw file).
    
    This allows users to quickly populate the database with shared datasets.
    
    Example URLs:
    - GitHub raw: https://raw.githubusercontent.com/username/repo/main/data/posts.json
    - Any public JSON endpoint
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(request.url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in the response")
    
    # Handle both formats: {"posts": [...]} or [...]
    posts_data = data.get("posts", data) if isinstance(data, dict) else data
    
    if not isinstance(posts_data, list):
        raise HTTPException(status_code=400, detail="Expected a list of posts or {posts: [...]}")
    
    if request.replace_existing:
        db.query(Post).delete()
        db.commit()
    
    imported = 0
    skipped = 0
    
    for post_data in posts_data:
        try:
            # Parse created_at if it's a string
            created_at = post_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            elif created_at is None:
                created_at = datetime.utcnow()
            
            post_id = post_data.get("post_id")
            if not post_id:
                # Generate post_id if not provided
                import hashlib
                content = post_data.get("content", "")
                author = post_data.get("author_username", "unknown")
                post_id = hashlib.sha256(f"{author}:{content}".encode()).hexdigest()[:16]
            
            # Check for existing
            existing = db.query(Post).filter(Post.post_id == post_id).first()
            if existing:
                skipped += 1
                continue
            
            post = Post(
                post_id=post_id,
                author_username=post_data.get("author_username", "unknown"),
                author_display_name=post_data.get("author_display_name"),
                author_verified=post_data.get("author_verified", False),
                author_followers=post_data.get("author_followers", 0),
                content=post_data.get("content", ""),
                created_at=created_at,
                likes=post_data.get("likes", 0),
                retweets=post_data.get("retweets", 0),
                replies=post_data.get("replies", 0),
                views=post_data.get("views", 0),
                has_media=post_data.get("has_media", False),
                has_links=post_data.get("has_links", False),
                media_urls=post_data.get("media_urls", []),
                link_urls=post_data.get("link_urls", []),
                hashtags=post_data.get("hashtags", []),
                mentions=post_data.get("mentions", []),
                grok_summary=post_data.get("grok_summary"),
                grok_topics=post_data.get("grok_topics", []),
                grok_sentiment=post_data.get("grok_sentiment"),
                grok_entities=post_data.get("grok_entities", []),
                grok_keywords=post_data.get("grok_keywords", []),
                post_url=post_data.get("post_url")
            )
            db.add(post)
            imported += 1
        except Exception as e:
            logger.warning(f"Failed to import post: {e}")
            skipped += 1
    
    db.commit()
    
    # Rebuild search index
    search_engine.build_index(db)
    
    return {
        "message": f"Successfully imported {imported} posts from URL",
        "imported": imported,
        "skipped": skipped,
        "source_url": request.url
    }


@app.post("/api/data/load-sample")
async def load_sample_data_endpoint(
    db: Session = Depends(get_db),
    replace_existing: bool = Query(default=False, description="Replace all existing posts")
):
    """
    Load sample posts from the local data/sample_posts.json file.
    
    This is the easiest way to populate the database with test data.
    The sample data includes posts from tech leaders, AI companies, and
    influential accounts with pre-analyzed Grok metadata.
    """
    if replace_existing:
        db.query(Post).delete()
        db.commit()
        logger.info("Cleared existing posts for sample data load")
    
    result = load_sample_data(db)
    
    if result.get("imported", 0) > 0:
        # Rebuild search index
        search_engine.build_index(db)
    
    return {
        "message": f"Loaded {result.get('imported', 0)} sample posts",
        "imported": result.get("imported", 0),
        "skipped": result.get("skipped", 0),
        "source": "data/sample_posts.json"
    }


@app.get("/api/data/sample-info")
async def get_sample_data_info():
    """
    Get information about the available sample data.
    """
    sample_exists = os.path.exists(SAMPLE_DATA_PATH)
    post_count = 0
    authors = []
    
    if sample_exists:
        try:
            with open(SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            posts = data.get("posts", [])
            post_count = len(posts)
            authors = list(set(p.get("author_username", "") for p in posts))
        except:
            pass
    
    return {
        "sample_file_exists": sample_exists,
        "sample_file_path": "data/sample_posts.json",
        "post_count": post_count,
        "authors": authors,
        "description": "Sample dataset with tech leaders, AI companies, and influential accounts",
        "usage": "POST /api/data/load-sample to load into database"
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

