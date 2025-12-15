import React, { useState } from 'react';
import { motion } from 'framer-motion';
import './PostCard.css';

function PostCard({ post, onHashtagClick }) {
  const [expanded, setExpanded] = useState(false);
  
  const formatNumber = (num) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      if (diffHours === 0) {
        const diffMins = Math.floor(diffMs / (1000 * 60));
        return `${diffMins}m`;
      }
      return `${diffHours}h`;
    }
    if (diffDays < 7) {
      return `${diffDays}d`;
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive': return '#00ff88';
      case 'negative': return '#ef4444';
      case 'mixed': return '#fbbf24';
      default: return '#a0a0b0';
    }
  };

  const renderContent = (content) => {
    // Parse hashtags and mentions
    const parts = content.split(/(\#\w+|\@\w+)/g);
    
    return parts.map((part, index) => {
      if (part.startsWith('#')) {
        return (
          <span 
            key={index} 
            className="hashtag"
            onClick={(e) => {
              e.stopPropagation();
              onHashtagClick?.(part);
            }}
          >
            {part}
          </span>
        );
      }
      if (part.startsWith('@')) {
        return (
          <span key={index} className="mention">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <motion.div 
      className="post-card"
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2 }}
    >
      {/* Post Header */}
      <div className="post-header">
        <div className="author-info">
          <div className="author-avatar">
            {post.author_display_name?.[0] || post.author_username[0].toUpperCase()}
          </div>
          <div className="author-details">
            <div className="author-name">
              {post.author_display_name || post.author_username}
              {post.author_verified && (
                <svg className="verified-badge" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                </svg>
              )}
            </div>
            <div className="author-handle">
              @{post.author_username}
            </div>
          </div>
        </div>
        <div className="post-time">
          {formatDate(post.created_at)}
        </div>
      </div>

      {/* Post Content */}
      <div 
        className={`post-content ${expanded ? 'expanded' : ''}`}
        onClick={() => post.content.length > 280 && setExpanded(!expanded)}
      >
        {renderContent(expanded ? post.content : post.content.slice(0, 280))}
        {!expanded && post.content.length > 280 && (
          <span className="read-more">...read more</span>
        )}
      </div>

      {/* Grok Analysis */}
      {(post.grok_summary || post.grok_topics?.length > 0) && (
        <div className="grok-analysis">
          {post.grok_sentiment && (
            <div 
              className="sentiment-indicator"
              style={{ '--sentiment-color': getSentimentColor(post.grok_sentiment) }}
            >
              <span className="sentiment-dot"></span>
              {post.grok_sentiment}
            </div>
          )}
          
          {post.grok_topics?.length > 0 && (
            <div className="topics-chips">
              {post.grok_topics.slice(0, 3).map((topic, index) => (
                <span 
                  key={index} 
                  className="topic-chip"
                  onClick={() => onHashtagClick?.(topic)}
                >
                  {topic}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Engagement Metrics */}
      <div className="post-metrics">
        <div className="metric">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
          </svg>
          <span>{formatNumber(post.likes)}</span>
        </div>
        
        <div className="metric">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M17 1l4 4-4 4"/>
            <path d="M3 11V9a4 4 0 0 1 4-4h14"/>
            <path d="M7 23l-4-4 4-4"/>
            <path d="M21 13v2a4 4 0 0 1-4 4H3"/>
          </svg>
          <span>{formatNumber(post.retweets)}</span>
        </div>
        
        <div className="metric">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
          </svg>
          <span>{formatNumber(post.replies)}</span>
        </div>
        
        <div className="metric views">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          <span>{formatNumber(post.views)}</span>
        </div>

        {post.has_media && (
          <div className="metric media-badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <path d="M21 15l-5-5L5 21"/>
            </svg>
          </div>
        )}

        {post.has_links && (
          <div className="metric link-badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </div>
        )}
      </div>

      {/* Relevance Score */}
      {post.relevance_score !== null && post.relevance_score > 0 && (
        <div className="relevance-bar">
          <div 
            className="relevance-fill"
            style={{ width: `${Math.min(post.relevance_score * 10, 100)}%` }}
          />
        </div>
      )}
    </motion.div>
  );
}

export default PostCard;

