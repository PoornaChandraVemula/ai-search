import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import './Sidebar.css';

function Sidebar({ stats, onQuickSearch }) {
  const [popularAccounts, setPopularAccounts] = useState([]);
  const [scrapeUsername, setScrapeUsername] = useState('');
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState(null);

  useEffect(() => {
    fetchPopularAccounts();
  }, []);

  const fetchPopularAccounts = async () => {
    try {
      const response = await fetch('/api/accounts/popular');
      if (response.ok) {
        const data = await response.json();
        setPopularAccounts(data.accounts || []);
      }
    } catch (err) {
      console.error('Failed to fetch popular accounts:', err);
    }
  };

  const handleScrape = async (username) => {
    setIsScraping(true);
    setScrapeStatus({ type: 'loading', message: `Scraping @${username}...` });
    
    try {
      const response = await fetch(`/api/scrape/${username}?max_posts=20`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        setScrapeStatus({ 
          type: 'success', 
          message: `Found ${data.new_posts} new posts from @${username}` 
        });
        // Refresh page to update stats
        setTimeout(() => window.location.reload(), 1500);
      } else {
        throw new Error('Scrape failed');
      }
    } catch (err) {
      setScrapeStatus({ type: 'error', message: 'Scraping failed - try another account' });
    } finally {
      setIsScraping(false);
      setTimeout(() => setScrapeStatus(null), 4000);
    }
  };

  const handleScrapeAll = async () => {
    setIsScraping(true);
    setScrapeStatus({ type: 'loading', message: 'Scraping popular accounts...' });
    
    const usernames = popularAccounts.map(a => a.username);
    
    try {
      const response = await fetch('/api/scrape/batch?max_posts_per_account=10', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(usernames)
      });
      
      if (response.ok) {
        const data = await response.json();
        const successful = data.results.filter(r => r.status === 'success').length;
        setScrapeStatus({ 
          type: 'success', 
          message: `Scraped ${successful} accounts successfully!` 
        });
        setTimeout(() => window.location.reload(), 1500);
      } else {
        throw new Error('Batch scrape failed');
      }
    } catch (err) {
      setScrapeStatus({ type: 'error', message: 'Batch scraping failed' });
    } finally {
      setIsScraping(false);
      setTimeout(() => setScrapeStatus(null), 4000);
    }
  };

  const handleCustomScrape = async (e) => {
    e.preventDefault();
    if (scrapeUsername.trim()) {
      await handleScrape(scrapeUsername.trim().replace('@', ''));
      setScrapeUsername('');
    }
  };

  const quickSearches = [
    { label: 'AI announcements', query: 'artificial intelligence' },
    { label: 'Technology news', query: 'technology innovation' },
    { label: 'Climate updates', query: 'climate change' },
    { label: 'Space exploration', query: 'space SpaceX' },
    { label: 'Cryptocurrency', query: 'crypto blockchain' },
  ];

  return (
    <motion.aside 
      className="sidebar"
      initial={{ x: -300, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: -300, opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Stats Section */}
      {stats && (
        <div className="sidebar-section stats-section">
          <h3 className="section-title">System Stats</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{stats.total_posts.toLocaleString()}</span>
              <span className="stat-label">Posts</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.total_accounts}</span>
              <span className="stat-label">Accounts</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.total_searches}</span>
              <span className="stat-label">Searches</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.index_size}</span>
              <span className="stat-label">Indexed</span>
            </div>
          </div>
        </div>
      )}

      {/* Scrape Section */}
      <div className="sidebar-section">
        <h3 className="section-title">Scrape X Posts</h3>
        
        <form onSubmit={handleCustomScrape} className="scrape-form">
          <input
            type="text"
            value={scrapeUsername}
            onChange={(e) => setScrapeUsername(e.target.value)}
            placeholder="Enter @username..."
            disabled={isScraping}
          />
          <button type="submit" disabled={isScraping || !scrapeUsername.trim()}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </button>
        </form>

        <div className="popular-accounts">
          <div className="accounts-header">
            <span>Popular Accounts</span>
            <button 
              className="scrape-all-btn"
              onClick={handleScrapeAll}
              disabled={isScraping}
            >
              {isScraping ? 'Scraping...' : 'Scrape All'}
            </button>
          </div>
          
          <div className="accounts-list">
            {popularAccounts.slice(0, 6).map((account, index) => (
              <div key={index} className="account-item">
                <div className="account-info">
                  <span className="account-name">
                    @{account.username}
                    {account.verified && (
                      <svg className="verified" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                      </svg>
                    )}
                  </span>
                </div>
                <button
                  className="scrape-btn"
                  onClick={() => handleScrape(account.username)}
                  disabled={isScraping}
                  title={`Scrape @${account.username}`}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Scrape Status */}
        {scrapeStatus && (
          <motion.div 
            className={`scrape-status ${scrapeStatus.type}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {scrapeStatus.type === 'loading' && <div className="mini-spinner" />}
            {scrapeStatus.type === 'success' && '✓'}
            {scrapeStatus.type === 'error' && '✕'}
            <span>{scrapeStatus.message}</span>
          </motion.div>
        )}
      </div>

      {/* Quick Search Section */}
      <div className="sidebar-section">
        <h3 className="section-title">Quick Search</h3>
        <div className="quick-search-list">
          {quickSearches.map((item, index) => (
            <button
              key={index}
              className="quick-search-btn"
              onClick={() => onQuickSearch(item.query)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Top Authors */}
      {stats?.top_authors?.length > 0 && (
        <div className="sidebar-section">
          <h3 className="section-title">Top Authors</h3>
          <div className="top-authors-list">
            {stats.top_authors.slice(0, 5).map((author, index) => (
              <button
                key={index}
                className="author-btn"
                onClick={() => onQuickSearch(`from:${author.username}`)}
              >
                <span className="author-rank">#{index + 1}</span>
                <span className="author-name">@{author.username}</span>
                <span className="author-count">{author.post_count} posts</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </motion.aside>
  );
}

export default Sidebar;
