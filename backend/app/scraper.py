"""
X (Twitter) Web Scraper using Playwright.

Uses headless Chromium browser to scrape real posts from x.com.
Playwright handles JavaScript rendering required by X.

Libraries:
- playwright: Headless browser automation
- beautifulsoup4: HTML parsing
"""
import asyncio
import logging
import hashlib
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from .config import settings
from .models import PostCreate, AccountCreate

logger = logging.getLogger(__name__)


# Popular accounts
POPULAR_ACCOUNTS = [
    {"username": "elonmusk", "display_name": "Elon Musk", "verified": True},
    {"username": "BillGates", "display_name": "Bill Gates", "verified": True},
    {"username": "BarackObama", "display_name": "Barack Obama", "verified": True},
    {"username": "OpenAI", "display_name": "OpenAI", "verified": True},
    {"username": "sama", "display_name": "Sam Altman", "verified": True},
    {"username": "satyanadella", "display_name": "Satya Nadella", "verified": True},
    {"username": "JeffBezos", "display_name": "Jeff Bezos", "verified": True},
    {"username": "tim_cook", "display_name": "Tim Cook", "verified": True},
    {"username": "Google", "display_name": "Google", "verified": True},
    {"username": "naval", "display_name": "Naval", "verified": True},
]


class XScraper:
    """
    Web scraper for X posts using Playwright headless browser.
    Renders JavaScript to get actual tweet content from x.com.
    """
    
    def __init__(self):
        self.delay = settings.SCRAPE_DELAY
        self.max_posts = settings.MAX_POSTS_PER_ACCOUNT
        self._last_request: Optional[datetime] = None
    
    async def _rate_limit_wait(self):
        """Wait between requests to respect rate limits."""
        if self._last_request:
            elapsed = (datetime.utcnow() - self._last_request).total_seconds()
            if elapsed < self.delay:
                await asyncio.sleep(self.delay - elapsed)
        self._last_request = datetime.utcnow()
    
    async def scrape_user_posts(self, username: str, max_posts: int = 50) -> List[Dict[str, Any]]:
        """
        Scrape posts from a user's X profile using Playwright.
        
        Args:
            username: X/Twitter username (without @)
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of post dictionaries
        """
        await self._rate_limit_wait()
        
        posts = []
        url = f"https://x.com/{username}"
        
        logger.info(f"Scraping @{username} from {url} using Playwright")
        
        try:
            async with async_playwright() as p:
                # Launch headless browser
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # Navigate to profile
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Wait for tweets to load
                await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)
                
                # Scroll to load more tweets
                for _ in range(3):
                    await page.evaluate('window.scrollBy(0, 1000)')
                    await asyncio.sleep(1)
                
                # Get page content
                html = await page.content()
                
                await browser.close()
                
                # Parse the HTML
                posts = self._parse_x_html(html, username, max_posts)
                
                logger.info(f"Scraped {len(posts)} posts from @{username}")
                
        except PlaywrightTimeout:
            logger.warning(f"Timeout loading @{username} - profile may be private or not exist")
        except Exception as e:
            logger.error(f"Error scraping @{username}: {type(e).__name__}: {e}")
        
        return posts
    
    def _parse_x_html(self, html: str, username: str, max_posts: int) -> List[Dict[str, Any]]:
        """
        Parse tweets from X.com HTML.
        """
        posts = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Find tweet articles
        tweet_articles = soup.find_all('article', {'data-testid': 'tweet'})
        logger.info(f"Found {len(tweet_articles)} tweet articles")
        
        for article in tweet_articles[:max_posts]:
            post = self._parse_tweet_article(article, username)
            if post:
                posts.append(post)
        
        return posts
    
    def _parse_tweet_article(self, article, username: str) -> Optional[Dict[str, Any]]:
        """Parse a single tweet article element."""
        try:
            # Find tweet text
            text_elem = article.find('div', {'data-testid': 'tweetText'})
            if not text_elem:
                return None
            
            content = text_elem.get_text(separator=' ', strip=True)
            if not content or len(content) < 3:
                return None
            
            # Get engagement stats
            likes = 0
            retweets = 0
            replies = 0
            
            # Like button
            like_btn = article.find('button', {'data-testid': 'like'})
            if like_btn:
                like_text = like_btn.get_text(strip=True)
                likes = self._parse_count(like_text)
            
            # Retweet button
            retweet_btn = article.find('button', {'data-testid': 'retweet'})
            if retweet_btn:
                retweet_text = retweet_btn.get_text(strip=True)
                retweets = self._parse_count(retweet_text)
            
            # Reply button
            reply_btn = article.find('button', {'data-testid': 'reply'})
            if reply_btn:
                reply_text = reply_btn.get_text(strip=True)
                replies = self._parse_count(reply_text)
            
            # Check for media
            has_media = bool(article.find('div', {'data-testid': 'tweetPhoto'})) or \
                       bool(article.find('div', {'data-testid': 'videoPlayer'}))
            
            # Get timestamp
            time_elem = article.find('time')
            created_at = datetime.utcnow()
            if time_elem and time_elem.get('datetime'):
                try:
                    created_at = datetime.fromisoformat(time_elem['datetime'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Get tweet link for ID
            tweet_id = None
            links = article.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                match = re.search(r'/status/(\d+)', href)
                if match:
                    tweet_id = match.group(1)
                    break
            
            return {
                'content': content,
                'author_username': username,
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
                'views': 0,
                'has_media': has_media,
                'created_at': created_at,
                'tweet_id': tweet_id,
            }
            
        except Exception as e:
            logger.debug(f"Error parsing tweet article: {e}")
            return None
    
    def _parse_count(self, text: str) -> int:
        """Parse count with K/M suffixes."""
        if not text:
            return 0
        
        text = text.strip().replace(',', '')
        match = re.search(r'([\d.]+)\s*([KMB])?', text, re.IGNORECASE)
        if not match:
            return 0
        
        try:
            num = float(match.group(1))
            suffix = (match.group(2) or '').upper()
            
            multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
            return int(num * multipliers.get(suffix, 1))
        except:
            return 0
    
    async def scrape_account(
        self,
        username: str,
        max_posts: Optional[int] = None
    ) -> Tuple[AccountCreate, List[PostCreate]]:
        """
        Scrape posts from an X account.
        """
        max_posts = max_posts or self.max_posts
        
        # Get account info
        account_info = self._get_account_info(username)
        account = AccountCreate(
            username=account_info["username"],
            display_name=account_info["display_name"],
            verified=account_info["verified"],
            followers=0,
            following=0
        )
        
        # Scrape posts
        raw_posts = await self.scrape_user_posts(username, max_posts)
        
        # Convert to PostCreate objects
        posts = []
        for raw in raw_posts:
            post = self._create_post(raw, account_info)
            posts.append(post)
        
        logger.info(f"Returning {len(posts)} posts for @{username}")
        return account, posts
    
    def _get_account_info(self, username: str) -> Dict[str, Any]:
        """Get account info from known accounts or create default."""
        for acc in POPULAR_ACCOUNTS:
            if acc["username"].lower() == username.lower():
                return acc
        
        return {
            "username": username,
            "display_name": username,
            "verified": False
        }
    
    def _create_post(self, raw: Dict[str, Any], account: Dict[str, Any]) -> PostCreate:
        """Convert raw data to PostCreate."""
        created_at = raw.get('created_at') or datetime.utcnow()
        content = raw['content']
        
        post_id = raw.get('tweet_id') or self._generate_id(content, account['username'], created_at)
        
        return PostCreate(
            post_id=post_id,
            author_username=account['username'],
            author_display_name=account['display_name'],
            author_verified=account['verified'],
            author_followers=0,
            content=content,
            created_at=created_at,
            likes=raw.get('likes', 0),
            retweets=raw.get('retweets', 0),
            replies=raw.get('replies', 0),
            views=raw.get('views', 0),
            has_media=raw.get('has_media', False),
            has_links=bool(re.search(r'https?://\S+', content)),
            hashtags=re.findall(r'#(\w+)', content),
            mentions=re.findall(r'@(\w+)', content),
            post_url=f"https://x.com/{account['username']}/status/{post_id}"
        )
    
    def _generate_id(self, content: str, username: str, timestamp: datetime) -> str:
        """Generate unique ID."""
        data = f"{username}_{content}_{timestamp.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def get_popular_accounts(self) -> List[Dict[str, Any]]:
        """Get list of popular accounts."""
        return POPULAR_ACCOUNTS.copy()
    
    def create_post_from_data(
        self,
        content: str,
        author_username: str,
        author_display_name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        likes: int = 0,
        retweets: int = 0,
        replies: int = 0,
        views: int = 0,
        has_media: bool = False
    ) -> PostCreate:
        """Create PostCreate from manual data."""
        created_at = created_at or datetime.utcnow()
        post_id = self._generate_id(content, author_username, created_at)
        
        return PostCreate(
            post_id=post_id,
            author_username=author_username,
            author_display_name=author_display_name or author_username,
            author_verified=False,
            author_followers=0,
            content=content,
            created_at=created_at,
            likes=likes,
            retweets=retweets,
            replies=replies,
            views=views,
            has_media=has_media,
            has_links=bool(re.search(r'https?://\S+', content)),
            hashtags=re.findall(r'#(\w+)', content),
            mentions=re.findall(r'@(\w+)', content),
            post_url=f"https://x.com/{author_username}/status/{post_id}"
        )


# Global instance
scraper = XScraper()
