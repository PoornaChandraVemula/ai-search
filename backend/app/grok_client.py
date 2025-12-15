"""
Grok API client for query understanding, content analysis, and summarization.
"""
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

logger = logging.getLogger(__name__)


class GrokClient:
    """Client for interacting with Grok API."""
    
    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        self.base_url = settings.GROK_API_BASE_URL
        self.model = settings.GROK_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Make a chat completion request to Grok API."""
        if not self.api_key:
            logger.warning("Grok API key not configured, returning empty response")
            return ""
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 2000
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def enhance_query(self, query: str) -> Dict[str, Any]:
        """
        Use Grok to understand and enhance a search query.
        Returns enhanced query with expanded keywords and search intent.
        """
        system_prompt = """You are a search query enhancement assistant for a Twitter/X post search system.
Your task is to analyze the user's search query and enhance it for better search results.

Analyze the query and return a JSON object with:
1. "enhanced_query": An expanded version of the query with related keywords
2. "keywords": List of important keywords extracted from the query
3. "intent": The search intent (informational, opinion, news, entertainment, technical)
4. "filters": Any implicit filters (date range, author type, etc.)
5. "related_terms": Related terms that might help find relevant posts

Return ONLY valid JSON, no markdown or explanations."""

        user_message = f"Enhance this search query: {query}"
        
        try:
            response = await self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ], temperature=0.3)
            
            # Parse JSON response
            result = json.loads(response.strip())
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Grok response as JSON: {response}")
            return {
                "enhanced_query": query,
                "keywords": query.split(),
                "intent": "informational",
                "filters": {},
                "related_terms": []
            }
        except Exception as e:
            logger.error(f"Error enhancing query with Grok: {e}")
            return {
                "enhanced_query": query,
                "keywords": query.split(),
                "intent": "informational",
                "filters": {},
                "related_terms": []
            }
    
    async def analyze_post(self, content: str, author: str) -> Dict[str, Any]:
        """
        Use Grok to analyze a post and generate rich metadata.
        """
        system_prompt = """You are a content analysis assistant for Twitter/X posts.
Analyze the given post and extract meaningful metadata.

Return a JSON object with:
1. "summary": A concise one-sentence summary of the post
2. "topics": List of 2-5 main topics/themes
3. "sentiment": Overall sentiment (positive, negative, neutral, mixed)
4. "entities": Named entities mentioned (people, companies, products, places)
5. "keywords": 5-10 searchable keywords

Return ONLY valid JSON, no markdown or explanations."""

        user_message = f"Author: @{author}\nPost: {content}"
        
        try:
            response = await self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ], temperature=0.3)
            
            result = json.loads(response.strip())
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Grok analysis response: {response}")
            return {
                "summary": content[:100] + "..." if len(content) > 100 else content,
                "topics": [],
                "sentiment": "neutral",
                "entities": [],
                "keywords": content.split()[:5]
            }
        except Exception as e:
            logger.error(f"Error analyzing post with Grok: {e}")
            return {
                "summary": content[:100] + "..." if len(content) > 100 else content,
                "topics": [],
                "sentiment": "neutral",
                "entities": [],
                "keywords": content.split()[:5]
            }
    
    async def summarize_search_results(
        self,
        query: str,
        posts: List[Dict[str, Any]],
        max_posts: int = 10
    ) -> Dict[str, Any]:
        """
        Use Grok to generate a summary of search results.
        """
        system_prompt = """You are a search results summarization assistant.
Given a search query and a list of Twitter/X posts, provide an intelligent summary.

Return a JSON object with:
1. "summary": A comprehensive summary of what the search results reveal (2-3 paragraphs)
2. "key_insights": List of 3-5 key insights or takeaways from the posts
3. "common_themes": List of recurring themes across posts
4. "sentiment_overview": Overall sentiment of the discussion
5. "notable_posts": Brief highlights of 2-3 most relevant/interesting posts
6. "related_topics": Topics related to the query that users might want to explore

Return ONLY valid JSON, no markdown or explanations."""

        # Prepare posts summary for Grok
        posts_text = ""
        for i, post in enumerate(posts[:max_posts], 1):
            posts_text += f"\n{i}. @{post.get('author_username', 'unknown')}: {post.get('content', '')[:300]}"
            posts_text += f" [Likes: {post.get('likes', 0)}, Retweets: {post.get('retweets', 0)}]"
        
        user_message = f"Search Query: {query}\n\nPosts Found:{posts_text}"
        
        try:
            response = await self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ], temperature=0.5)
            
            result = json.loads(response.strip())
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse Grok summary response: {response}")
            return {
                "summary": f"Found {len(posts)} posts matching your query.",
                "key_insights": [],
                "common_themes": [],
                "sentiment_overview": "mixed",
                "notable_posts": [],
                "related_topics": []
            }
        except Exception as e:
            logger.error(f"Error summarizing results with Grok: {e}")
            return {
                "summary": f"Found {len(posts)} posts matching your query.",
                "key_insights": [],
                "common_themes": [],
                "sentiment_overview": "mixed",
                "notable_posts": [],
                "related_topics": []
            }
    
    async def clarify_ambiguous_query(self, query: str) -> Dict[str, Any]:
        """
        Handle ambiguous queries by suggesting clarifications.
        """
        system_prompt = """You are a search query clarification assistant.
Analyze if the query is ambiguous and suggest clarifications.

Return a JSON object with:
1. "is_ambiguous": Boolean indicating if the query is ambiguous
2. "possible_interpretations": List of possible query meanings
3. "clarifying_questions": Questions to ask the user for clarification
4. "suggested_queries": More specific query alternatives

Return ONLY valid JSON, no markdown or explanations."""

        try:
            response = await self._chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this search query: {query}"}
            ], temperature=0.3)
            
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Error clarifying query with Grok: {e}")
            return {
                "is_ambiguous": False,
                "possible_interpretations": [query],
                "clarifying_questions": [],
                "suggested_queries": []
            }


# Global client instance
grok_client = GrokClient()

