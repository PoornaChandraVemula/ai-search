import React from 'react';
import { motion } from 'framer-motion';
import './EmptyState.css';

function EmptyState({ stats, onQuickSearch }) {
  const exampleQueries = [
    { query: 'AI breakthrough announcements', desc: 'Find major AI news' },
    { query: 'from:elonmusk SpaceX', desc: 'Elon on SpaceX' },
    { query: 'climate change solutions', desc: 'Environmental updates' },
    { query: '"artificial intelligence" min_likes:10000', desc: 'Popular AI posts' },
    { query: 'technology innovation has:media', desc: 'Tech with media' },
  ];

  return (
    <motion.div 
      className="empty-state"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
    >
      <div className="empty-hero">
        <motion.div 
          className="hero-icon"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
        >
          <svg width="120" height="120" viewBox="0 0 120 120">
            <defs>
              <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00ff88" />
                <stop offset="50%" stopColor="#00d4ff" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
              <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            
            {/* Outer ring */}
            <circle 
              cx="60" cy="60" r="55" 
              fill="none" 
              stroke="url(#heroGrad)" 
              strokeWidth="2"
              opacity="0.3"
            />
            
            {/* Search icon */}
            <g filter="url(#glow)">
              <circle 
                cx="52" cy="52" r="24" 
                fill="none" 
                stroke="url(#heroGrad)" 
                strokeWidth="4"
              />
              <line 
                x1="70" y1="70" x2="85" y2="85" 
                stroke="url(#heroGrad)" 
                strokeWidth="4" 
                strokeLinecap="round"
              />
            </g>
            
            {/* Sparkles */}
            <circle cx="90" cy="30" r="3" fill="#00ff88" opacity="0.8">
              <animate attributeName="opacity" values="0.8;0.2;0.8" dur="2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="25" cy="85" r="2" fill="#00d4ff" opacity="0.6">
              <animate attributeName="opacity" values="0.6;0.1;0.6" dur="2.5s" repeatCount="indefinite"/>
            </circle>
            <circle cx="100" cy="70" r="2" fill="#8b5cf6" opacity="0.7">
              <animate attributeName="opacity" values="0.7;0.2;0.7" dur="1.8s" repeatCount="indefinite"/>
            </circle>
          </svg>
        </motion.div>
        
        <motion.h2 
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          Discover Posts with <span className="gradient-text">Grok Intelligence</span>
        </motion.h2>
        
        <motion.p
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          Search through posts from popular X accounts using natural language queries.
          Grok enhances your searches and provides intelligent summaries.
        </motion.p>
      </div>

      {/* Feature highlights */}
      <motion.div 
        className="features-grid"
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.6 }}
      >
        <div className="feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </div>
          <h3>Smart Enhancement</h3>
          <p>Grok understands your intent and enhances queries for better results</p>
        </div>
        
        <div className="feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
            </svg>
          </div>
          <h3>AI Summaries</h3>
          <p>Get intelligent summaries and key insights from search results</p>
        </div>
        
        <div className="feature-card">
          <div className="feature-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>
            </svg>
          </div>
          <h3>Advanced Filters</h3>
          <p>Use operators like from:, min_likes:, has:media for precise search</p>
        </div>
      </motion.div>

      {/* Example queries */}
      <motion.div 
        className="example-queries"
        initial={{ y: 30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.7 }}
      >
        <h3>Try these searches</h3>
        <div className="queries-grid">
          {exampleQueries.map((item, index) => (
            <motion.button
              key={index}
              className="query-card"
              onClick={() => onQuickSearch(item.query)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 + index * 0.1 }}
            >
              <span className="query-text">{item.query}</span>
              <span className="query-desc">{item.desc}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>

      {/* Getting started note */}
      {stats && stats.total_posts === 0 && (
        <motion.div 
          className="getting-started"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
        >
          <div className="start-icon">💡</div>
          <div className="start-content">
            <h4>Getting Started</h4>
            <p>
              No posts indexed yet. Use the sidebar to scrape posts from popular accounts,
              then start searching!
            </p>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

export default EmptyState;

