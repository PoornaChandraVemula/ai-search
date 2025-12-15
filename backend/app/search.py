"""
Search Engine Module with Token-Based and Embedding-Based Retrieval.

Supports:
- Token-Based (Keyword) Search: Using Whoosh with BM25F ranking
- Embedding-Based (Semantic) Search: Using sentence-transformers
- Hybrid Search: Combining both approaches with score fusion
"""
import os
import re
import logging
import time
import shutil
import pickle
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from whoosh import index
from whoosh.fields import Schema, TEXT, ID, NUMERIC, BOOLEAN, DATETIME, KEYWORD
from whoosh.qparser import MultifieldParser, OrGroup, AndGroup
from whoosh.analysis import StemmingAnalyzer
from whoosh.scoring import BM25F

from .models import Post, PostResponse, SearchRequest, SearchResult
from .grok_client import grok_client

logger = logging.getLogger(__name__)

# Constants
INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "search_index")
EMBEDDINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "embeddings")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"  # Fast and efficient model

# Global embedding model (lazy loaded)
_embedding_model = None
_embeddings_loaded = False


def get_embedding_model():
    """Lazy load the sentence transformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            _embedding_model = None
    return _embedding_model


def create_schema() -> Schema:
    """Define the search schema with stemming analyzer."""
    analyzer = StemmingAnalyzer()
    
    return Schema(
        post_id=ID(stored=True, unique=True),
        db_id=NUMERIC(stored=True),
        content=TEXT(analyzer=analyzer, stored=True),
        author_username=TEXT(stored=True),
        author_display_name=TEXT(stored=True),
        hashtags=KEYWORD(stored=True, lowercase=True, commas=True),
        grok_keywords=KEYWORD(stored=True, lowercase=True, commas=True),
        grok_topics=KEYWORD(stored=True, lowercase=True, commas=True),
        likes=NUMERIC(stored=True, sortable=True),
        retweets=NUMERIC(stored=True, sortable=True),
        views=NUMERIC(stored=True, sortable=True),
        has_media=BOOLEAN(stored=True),
        has_links=BOOLEAN(stored=True),
        created_at=DATETIME(stored=True, sortable=True)
    )


def parse_filters(query: str) -> Tuple[str, Dict[str, Any]]:
    """
    Extract filters from query string.
    
    Supports:
    - from:username
    - min_likes:N
    - has:media
    - has:links
    """
    filters = {}
    
    # from:username
    match = re.search(r'from:(\w+)', query, re.IGNORECASE)
    if match:
        filters['author'] = match.group(1)
        query = re.sub(r'from:\w+', '', query, flags=re.IGNORECASE)
    
    # min_likes:N
    match = re.search(r'min_likes:(\d+)', query, re.IGNORECASE)
    if match:
        filters['min_likes'] = int(match.group(1))
        query = re.sub(r'min_likes:\d+', '', query, flags=re.IGNORECASE)
    
    # has:media / has:links
    if re.search(r'has:media', query, re.IGNORECASE):
        filters['has_media'] = True
        query = re.sub(r'has:media', '', query, flags=re.IGNORECASE)
    
    if re.search(r'has:links', query, re.IGNORECASE):
        filters['has_links'] = True
        query = re.sub(r'has:links', '', query, flags=re.IGNORECASE)
    
    # Check for AND operator
    filters['use_and'] = ' AND ' in query.upper()
    
    return query.strip(), filters


class EmbeddingIndex:
    """
    Vector index for semantic search using embeddings.
    
    Features:
    - Efficient cosine similarity search
    - Persistent storage with pickle
    - Incremental updates
    """
    
    def __init__(self):
        self.embeddings: Dict[int, np.ndarray] = {}  # db_id -> embedding
        self.embedding_matrix: Optional[np.ndarray] = None
        self.id_to_idx: Dict[int, int] = {}
        self.idx_to_id: Dict[int, int] = {}
        self._load_embeddings()
    
    def _load_embeddings(self):
        """Load embeddings from disk."""
        global _embeddings_loaded
        embeddings_file = os.path.join(EMBEDDINGS_DIR, "post_embeddings.pkl")
        
        if os.path.exists(embeddings_file):
            try:
                with open(embeddings_file, 'rb') as f:
                    self.embeddings = pickle.load(f)
                self._build_matrix()
                _embeddings_loaded = True
                logger.info(f"Loaded {len(self.embeddings)} embeddings from disk")
            except Exception as e:
                logger.warning(f"Failed to load embeddings: {e}")
                self.embeddings = {}
    
    def _save_embeddings(self):
        """Save embeddings to disk."""
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        embeddings_file = os.path.join(EMBEDDINGS_DIR, "post_embeddings.pkl")
        
        try:
            with open(embeddings_file, 'wb') as f:
                pickle.dump(self.embeddings, f)
            logger.info(f"Saved {len(self.embeddings)} embeddings to disk")
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
    
    def _build_matrix(self):
        """Build the embedding matrix for efficient similarity search."""
        if not self.embeddings:
            self.embedding_matrix = None
            self.id_to_idx = {}
            self.idx_to_id = {}
            return
        
        ids = list(self.embeddings.keys())
        self.id_to_idx = {id_: idx for idx, id_ in enumerate(ids)}
        self.idx_to_id = {idx: id_ for idx, id_ in enumerate(ids)}
        
        # Stack embeddings into matrix and normalize for cosine similarity
        matrix = np.vstack([self.embeddings[id_] for id_ in ids])
        # Normalize to unit vectors
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        self.embedding_matrix = matrix / norms
    
    @property
    def doc_count(self) -> int:
        """Number of documents in the embedding index."""
        return len(self.embeddings)
    
    @property
    def is_available(self) -> bool:
        """Check if embedding search is available."""
        return get_embedding_model() is not None
    
    def add_post(self, post: Post):
        """Generate and store embedding for a post."""
        model = get_embedding_model()
        if model is None:
            return
        
        content = post.content or ""
        if not content.strip():
            return
        
        try:
            # Include author, hashtags, and Grok metadata for richer context
            text = f"{post.author_username}: {content}"
            if post.hashtags:
                text += " " + " ".join(f"#{tag}" for tag in post.hashtags)
            # Add Grok-extracted keywords and summary for better semantic matching
            if post.grok_keywords:
                text += " " + " ".join(post.grok_keywords)
            if post.grok_topics:
                text += " " + " ".join(post.grok_topics)
            if post.grok_summary:
                text += " " + post.grok_summary
            
            embedding = model.encode(text, convert_to_numpy=True)
            self.embeddings[post.id] = embedding
            
            # Rebuild matrix and save after adding new embedding
            self._build_matrix()
            self._save_embeddings()
        except Exception as e:
            logger.warning(f"Failed to generate embedding for post {post.id}: {e}")
    
    def build_index(self, db: Session):
        """Build embedding index from all posts in database."""
        model = get_embedding_model()
        if model is None:
            logger.warning("Embedding model not available, skipping embedding index build")
            return
        
        logger.info("Building embedding index...")
        start = time.time()
        
        posts = db.query(Post).all()
        texts = []
        db_ids = []
        
        for post in posts:
            content = post.content or ""
            if content.strip():
                text = f"{post.author_username}: {content}"
                if post.hashtags:
                    text += " " + " ".join(f"#{tag}" for tag in post.hashtags)
                # Add Grok-extracted keywords and summary for better semantic matching
                if post.grok_keywords:
                    text += " " + " ".join(post.grok_keywords)
                if post.grok_topics:
                    text += " " + " ".join(post.grok_topics)
                if post.grok_summary:
                    text += " " + post.grok_summary
                texts.append(text)
                db_ids.append(post.id)
        
        if not texts:
            self.embeddings = {}
            self._build_matrix()
            return
        
        # Batch encode for efficiency
        try:
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
            self.embeddings = {db_id: emb for db_id, emb in zip(db_ids, embeddings)}
            self._build_matrix()
            self._save_embeddings()
            logger.info(f"Built embedding index for {len(self.embeddings)} posts in {time.time() - start:.2f}s")
        except Exception as e:
            logger.error(f"Failed to build embedding index: {e}")
    
    def search(self, query: str, limit: int = 50) -> Dict[int, float]:
        """
        Search for similar posts using cosine similarity.
        
        Returns:
            Dict mapping db_id to similarity score (0-1)
        """
        if self.embedding_matrix is None or len(self.embeddings) == 0:
            return {}
        
        model = get_embedding_model()
        if model is None:
            return {}
        
        try:
            # Encode query
            query_embedding = model.encode(query, convert_to_numpy=True)
            
            # Normalize query vector
            query_norm = np.linalg.norm(query_embedding)
            if query_norm == 0:
                return {}
            query_embedding = query_embedding / query_norm
            
            # Compute cosine similarities (matrix already normalized)
            similarities = np.dot(self.embedding_matrix, query_embedding)
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:limit]
            
            # Build result dict with meaningful similarity threshold
            # Cosine similarity > 0.3 indicates reasonable semantic relevance
            MIN_SIMILARITY_THRESHOLD = 0.3
            results = {}
            for idx in top_indices:
                sim_score = similarities[idx]
                if sim_score >= MIN_SIMILARITY_THRESHOLD:
                    db_id = self.idx_to_id[idx]
                    results[db_id] = float(sim_score)
            
            return results
        except Exception as e:
            logger.error(f"Embedding search error: {e}")
            return {}


class SearchEngine:
    """
    Unified search engine supporting multiple retrieval modes.
    
    Modes:
    - keyword: BM25F-based token search (fast, exact matching)
    - semantic: Embedding-based similarity search (conceptual matching)
    
    Features:
    - BM25F ranking algorithm for keyword search
    - Sentence-transformer embeddings for semantic search
    - Persistent indices
    """
    
    def __init__(self):
        self.schema = create_schema()
        self.ix = None
        self.embedding_index = EmbeddingIndex()
        self._init_index()
    
    def _init_index(self):
        """Initialize or open the search index."""
        os.makedirs(INDEX_DIR, exist_ok=True)
        
        try:
            if index.exists_in(INDEX_DIR):
                self.ix = index.open_dir(INDEX_DIR)
                logger.info(f"Opened index with {self.ix.doc_count()} documents")
            else:
                self.ix = index.create_in(INDEX_DIR, self.schema)
                logger.info("Created new search index")
        except Exception as e:
            logger.warning(f"Index error, recreating: {e}")
            shutil.rmtree(INDEX_DIR, ignore_errors=True)
            os.makedirs(INDEX_DIR, exist_ok=True)
            self.ix = index.create_in(INDEX_DIR, self.schema)
    
    @property
    def doc_count(self) -> int:
        """Number of documents in the token index."""
        return self.ix.doc_count() if self.ix else 0
    
    @property
    def embedding_available(self) -> bool:
        """Check if embedding search is available."""
        return self.embedding_index.is_available
    
    def build_index(self, db: Session):
        """Build both token and embedding indices from all posts in database."""
        logger.info("Building search indices...")
        start = time.time()
        
        # Build token index
        shutil.rmtree(INDEX_DIR, ignore_errors=True)
        os.makedirs(INDEX_DIR, exist_ok=True)
        self.ix = index.create_in(INDEX_DIR, self.schema)
        
        posts = db.query(Post).all()
        writer = self.ix.writer()
        
        for post in posts:
            writer.add_document(
                post_id=post.post_id,
                db_id=post.id,
                content=post.content or "",
                author_username=post.author_username or "",
                author_display_name=post.author_display_name or "",
                hashtags=",".join(post.hashtags or []),
                grok_keywords=",".join(post.grok_keywords or []),
                grok_topics=",".join(post.grok_topics or []),
                likes=post.likes or 0,
                retweets=post.retweets or 0,
                views=post.views or 0,
                has_media=post.has_media or False,
                has_links=post.has_links or False,
                created_at=post.created_at
            )
        
        writer.commit()
        logger.info(f"Indexed {len(posts)} posts in token index in {time.time() - start:.2f}s")
        
        # Build embedding index
        self.embedding_index.build_index(db)
    
    def add_post(self, post: Post):
        """Add a single post to both indices."""
        # Add to token index
        writer = self.ix.writer()
        writer.update_document(
            post_id=post.post_id,
            db_id=post.id,
            content=post.content or "",
            author_username=post.author_username or "",
            author_display_name=post.author_display_name or "",
            hashtags=",".join(post.hashtags or []),
            grok_keywords=",".join(post.grok_keywords or []),
            grok_topics=",".join(post.grok_topics or []),
            likes=post.likes or 0,
            retweets=post.retweets or 0,
            views=post.views or 0,
            has_media=post.has_media or False,
            has_links=post.has_links or False,
            created_at=post.created_at
        )
        writer.commit()
        
        # Add to embedding index
        self.embedding_index.add_post(post)
    
    def keyword_search(self, query: str, limit: int = 50, use_and: bool = False) -> Dict[int, float]:
        """
        Token-based search using BM25F.
        
        Returns:
            Dict mapping db_id to BM25F score
        """
        if not query.strip():
            return {}
        
        with self.ix.searcher(weighting=BM25F()) as searcher:
            fields = ["content", "author_username", "hashtags", "grok_keywords", "grok_topics"]
            group = AndGroup if use_and else OrGroup
            parser = MultifieldParser(fields, self.schema, group=group)
            
            try:
                parsed = parser.parse(query)
                results = searcher.search(parsed, limit=limit)
                
                # Filter results: keep only those with meaningful BM25 scores
                # Use relative threshold: at least 20% of the top score
                scores = {hit["db_id"]: hit.score for hit in results}
                if not scores:
                    return {}
                
                max_score = max(scores.values())
                min_threshold = max_score * 0.2  # Keep results with at least 20% of top score
                
                return {db_id: score for db_id, score in scores.items() if score >= min_threshold}
            except Exception as e:
                logger.error(f"Keyword search error: {e}")
                return {}
    
    def semantic_search(self, query: str, limit: int = 50) -> Dict[int, float]:
        """
        Embedding-based semantic search.
        
        Returns:
            Dict mapping db_id to similarity score (0-1)
        """
        return self.embedding_index.search(query, limit)
    
    def search_posts(
        self, 
        query: str, 
        limit: int = 50, 
        use_and: bool = False,
        mode: str = "keyword"
    ) -> Dict[int, float]:
        """
        Search posts using the specified mode.
        
        Args:
            query: Search query
            limit: Maximum results
            use_and: Use AND operator for keyword search
            mode: Search mode - keyword or semantic
        
        Returns:
            Dict mapping db_id to relevance score
        """
        if mode == "semantic":
            return self.semantic_search(query, limit)
        else:  # keyword (default)
            return self.keyword_search(query, limit, use_and)
    
    async def search(self, db: Session, request: SearchRequest) -> SearchResult:
        """
        Main search method with Grok enhancement.
        """
        start = time.time()
        
        # Build index if empty or if embeddings are needed but missing
        needs_embeddings = request.search_mode == "semantic"
        if self.doc_count == 0:
            self.build_index(db)
        elif needs_embeddings and self.embedding_index.doc_count == 0 and self.embedding_available:
            logger.info("Embedding index is empty, rebuilding...")
            self.embedding_index.build_index(db)
        
        # Parse filters from query
        clean_query, filters = parse_filters(request.query)
        
        # Merge request filters with parsed filters
        author = request.author or filters.get('author')
        min_likes = request.min_likes or filters.get('min_likes')
        has_media = request.has_media if request.has_media is not None else filters.get('has_media')
        use_and = filters.get('use_and', False)
        
        # Determine search mode (fall back to keyword if embeddings not available)
        search_mode = request.search_mode
        if search_mode == "semantic" and not self.embedding_available:
            logger.warning("Embedding model not available, falling back to keyword search")
            search_mode = "keyword"
        
        # Grok query enhancement (for both keyword and semantic modes)
        enhanced_query = clean_query
        if request.use_grok_enhancement and clean_query:
            try:
                enhancement = await grok_client.enhance_query(request.query)
                if enhancement.get("enhanced_query"):
                    enhanced_query = enhancement["enhanced_query"]
            except Exception as e:
                logger.warning(f"Grok enhancement failed: {e}")
        
        # Search using the appropriate mode
        scores = self.search_posts(
            enhanced_query or clean_query, 
            limit=100, 
            use_and=use_and,
            mode=search_mode
        )
        matching_ids = list(scores.keys())
        
        logger.debug(f"Search mode: {search_mode}, query: '{enhanced_query or clean_query}', found {len(matching_ids)} matching posts")
        
        # Build database query
        db_query = db.query(Post)
        
        if matching_ids:
            db_query = db_query.filter(Post.id.in_(matching_ids))
        elif clean_query:
            # Fallback to LIKE search only if no index matches
            # Use exact phrase matching (more restrictive)
            pattern = f"%{request.query}%"
            db_query = db_query.filter(
                or_(Post.content.ilike(pattern), Post.author_username.ilike(pattern))
            )
            logger.debug(f"Falling back to LIKE search for: '{request.query}'")
        
        # Apply filters
        if author:
            db_query = db_query.filter(Post.author_username.ilike(f"%{author}%"))
        if request.date_from:
            db_query = db_query.filter(Post.created_at >= request.date_from)
        if request.date_to:
            db_query = db_query.filter(Post.created_at <= request.date_to)
        if has_media:
            db_query = db_query.filter(Post.has_media == True)
        if min_likes:
            db_query = db_query.filter(Post.likes >= min_likes)
        
        total_count = db_query.count()
        
        # Sorting
        if request.sort_by == "relevance" and scores:
            posts = db_query.all()
            posts = sorted(posts, key=lambda p: scores.get(p.id, 0), reverse=(request.sort_order == "desc"))
            posts = posts[request.offset:request.offset + request.limit]
        else:
            order_col = {"date": Post.created_at, "likes": Post.likes, "retweets": Post.retweets, "views": Post.views}
            col = order_col.get(request.sort_by, Post.created_at)
            order_fn = desc if request.sort_order == "desc" else asc
            posts = db_query.order_by(order_fn(col)).offset(request.offset).limit(request.limit).all()
        
        # Convert to response
        post_responses = []
        for post in posts:
            resp = PostResponse.model_validate(post)
            resp.relevance_score = scores.get(post.id, 0)
            post_responses.append(resp)
        
        search_time_ms = (time.time() - start) * 1000
        
        # Grok summarization
        summary = None
        key_insights = []
        related_topics = []
        
        if post_responses and request.use_grok_enhancement:
            try:
                posts_data = [p.model_dump() for p in post_responses[:10]]
                result = await grok_client.summarize_search_results(request.query, posts_data)
                summary = result.get("summary")
                key_insights = result.get("key_insights", [])
                related_topics = result.get("related_topics", [])
            except Exception as e:
                logger.warning(f"Grok summarization failed: {e}")
        
        return SearchResult(
            posts=post_responses,
            total_count=total_count,
            query=request.query,
            enhanced_query=enhanced_query if enhanced_query != clean_query else None,
            search_time_ms=search_time_ms,
            summary=summary,
            key_insights=key_insights,
            related_topics=related_topics,
            search_mode=search_mode,
            embedding_available=self.embedding_available
        )


# Global instance
search_engine = SearchEngine()
