import React from 'react';
import { motion } from 'framer-motion';
import PostCard from './PostCard';
import './SearchResults.css';

const SEARCH_MODE_INFO = {
  keyword: { icon: '🔤', label: 'Keyword Search', color: '#4fc3f7' },
  semantic: { icon: '🧠', label: 'Semantic Search', color: '#ba68c8' },
};

function SearchResults({ results, query, onRelatedSearch }) {
  const {
    posts,
    total_count,
    enhanced_query,
    search_time_ms,
    summary,
    key_insights,
    related_topics,
    search_mode = 'keyword'
  } = results;

  const modeInfo = SEARCH_MODE_INFO[search_mode] || SEARCH_MODE_INFO.keyword;

  return (
    <div className="search-results">
      {/* Results Header */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="results-header"
      >
        <div className="results-meta">
          <span className="results-count">
            <strong>{total_count}</strong> posts found
          </span>
          <span className="results-time">
            in {search_time_ms.toFixed(0)}ms
          </span>
          <span 
            className="search-mode-badge"
            style={{ '--mode-color': modeInfo.color }}
          >
            <span className="mode-badge-icon">{modeInfo.icon}</span>
            <span className="mode-badge-label">{modeInfo.label}</span>
          </span>
        </div>
        
        {enhanced_query && enhanced_query !== query && (
          <div className="enhanced-query">
            <span className="grok-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2L1 21h22L12 2zm0 4.5l7.5 13H4.5L12 6.5z"/>
              </svg>
              Grok Enhanced
            </span>
            <span className="enhanced-text">
              Searching for: <em>"{enhanced_query}"</em>
            </span>
          </div>
        )}
      </motion.div>

      {/* AI Summary Section */}
      {summary && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="ai-summary-section"
        >
          <div className="summary-header">
            <div className="summary-icon">
              <svg width="24" height="24" viewBox="0 0 100 100">
                <defs>
                  <linearGradient id="summaryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#00ff88" />
                    <stop offset="100%" stopColor="#00d4ff" />
                  </linearGradient>
                </defs>
                <circle cx="50" cy="50" r="40" fill="none" stroke="url(#summaryGrad)" strokeWidth="4"/>
                <circle cx="50" cy="40" r="8" fill="url(#summaryGrad)"/>
                <path d="M50 55 L50 75" stroke="url(#summaryGrad)" strokeWidth="6" strokeLinecap="round"/>
              </svg>
            </div>
            <h3>Grok Analysis</h3>
          </div>
          
          <p className="summary-text">{summary}</p>
          
          {key_insights && key_insights.length > 0 && (
            <div className="key-insights">
              <h4>Key Insights</h4>
              <ul>
                {key_insights.map((insight, index) => (
                  <motion.li 
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 + index * 0.05 }}
                  >
                    <span className="insight-bullet">→</span>
                    {insight}
                  </motion.li>
                ))}
              </ul>
            </div>
          )}
          
          {related_topics && related_topics.length > 0 && (
            <div className="related-topics">
              <h4>Related Topics</h4>
              <div className="topics-list">
                {related_topics.map((topic, index) => (
                  <button
                    key={index}
                    className="topic-tag"
                    onClick={() => onRelatedSearch(topic)}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Posts Grid */}
      {posts.length > 0 ? (
        <div className="posts-grid">
          {posts.map((post, index) => (
            <motion.div
              key={post.post_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + index * 0.03 }}
            >
              <PostCard post={post} onHashtagClick={onRelatedSearch} />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="no-results">
          <div className="no-results-icon">🔍</div>
          <h3>No posts found</h3>
          <p>Try adjusting your search terms or filters</p>
        </div>
      )}
    </div>
  );
}

export default SearchResults;

