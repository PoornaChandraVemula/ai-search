import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './SearchBar.css';

const SEARCH_MODES = [
  { 
    value: 'keyword', 
    label: 'Keyword', 
    icon: '🔤',
    description: 'Fast exact token matching (BM25)'
  },
  { 
    value: 'semantic', 
    label: 'Semantic', 
    icon: '🧠',
    description: 'AI-powered conceptual search'
  },
];

function SearchBar({ onSearch, filters, onFilterChange, isLoading, embeddingAvailable = true }) {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [showModeTooltip, setShowModeTooltip] = useState(false);
  const inputRef = useRef(null);
  const suggestionsTimeout = useRef(null);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  const handleInputChange = async (e) => {
    const value = e.target.value;
    setQuery(value);

    // Debounce suggestions fetch
    if (suggestionsTimeout.current) {
      clearTimeout(suggestionsTimeout.current);
    }

    if (value.length >= 2) {
      suggestionsTimeout.current = setTimeout(async () => {
        try {
          const response = await fetch(`/api/search/suggestions?query=${encodeURIComponent(value)}`);
          if (response.ok) {
            const data = await response.json();
            setSuggestions(data.suggestions || []);
            setShowSuggestions(data.suggestions?.length > 0);
          }
        } catch (err) {
          console.error('Failed to fetch suggestions:', err);
        }
      }, 300);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setShowSuggestions(false);
      onSearch(query);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    onSearch(suggestion);
  };

  const handleFilterChange = (key, value) => {
    onFilterChange({ ...filters, [key]: value });
  };

  return (
    <div className="search-bar-wrapper">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-container">
          <div className="search-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </div>
          
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder="Search posts... Try: AI announcements from:elonmusk min_likes:1000"
            className="search-input"
            disabled={isLoading}
          />

          <div className="search-actions">
            <button 
              type="button"
              className={`filter-toggle ${showFilters ? 'active' : ''}`}
              onClick={() => setShowFilters(!showFilters)}
              aria-label="Toggle filters"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6" />
              </svg>
            </button>
            
            <button 
              type="submit" 
              className="search-button"
              disabled={isLoading || !query.trim()}
            >
              {isLoading ? (
                <div className="spinner" />
              ) : (
                <>
                  <span>Search</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Suggestions Dropdown */}
        <AnimatePresence>
          {showSuggestions && suggestions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="suggestions-dropdown"
            >
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  type="button"
                  className="suggestion-item"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                  <span>{suggestion}</span>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </form>

      {/* Filters Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="filters-panel"
          >
            {/* Search Mode Selector */}
            <div className="search-mode-section">
              <div className="section-header">
                <span className="section-title">Search Mode</span>
                <button 
                  className="info-button"
                  onMouseEnter={() => setShowModeTooltip(true)}
                  onMouseLeave={() => setShowModeTooltip(false)}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 16v-4M12 8h.01" />
                  </svg>
                </button>
                <AnimatePresence>
                  {showModeTooltip && (
                    <motion.div 
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }}
                      className="mode-tooltip"
                    >
                      <p><strong>Keyword:</strong> Uses BM25F algorithm for fast, exact token matching. Best for specific phrases.</p>
                      <p><strong>Semantic:</strong> Uses AI embeddings for conceptual matching. Finds related content even without exact words.</p>
                      <p><strong>Hybrid:</strong> Combines both approaches for best results. Recommended for most searches.</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
              <div className="search-mode-buttons">
                {SEARCH_MODES.map((mode) => (
                  <button
                    key={mode.value}
                    type="button"
                    className={`mode-button ${filters.searchMode === mode.value ? 'active' : ''} ${
                      mode.value !== 'keyword' && !embeddingAvailable ? 'disabled' : ''
                    }`}
                    onClick={() => handleFilterChange('searchMode', mode.value)}
                    disabled={mode.value !== 'keyword' && !embeddingAvailable}
                    title={mode.description}
                  >
                    <span className="mode-icon">{mode.icon}</span>
                    <span className="mode-label">{mode.label}</span>
                    {filters.searchMode === mode.value && (
                      <motion.div 
                        layoutId="activeModeIndicator"
                        className="active-indicator"
                      />
                    )}
                  </button>
                ))}
              </div>
              {!embeddingAvailable && (
                <p className="embedding-warning">
                  ⚠️ Semantic search unavailable - embedding model not loaded
                </p>
              )}
            </div>

            <div className="filters-divider" />

            <div className="filters-grid">
              <div className="filter-group">
                <label>Sort By</label>
                <select 
                  value={filters.sortBy}
                  onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                >
                  <option value="relevance">Relevance</option>
                  <option value="date">Date</option>
                  <option value="likes">Likes</option>
                  <option value="retweets">Retweets</option>
                  <option value="views">Views</option>
                </select>
              </div>

              <div className="filter-group">
                <label>Order</label>
                <select 
                  value={filters.sortOrder}
                  onChange={(e) => handleFilterChange('sortOrder', e.target.value)}
                >
                  <option value="desc">Descending</option>
                  <option value="asc">Ascending</option>
                </select>
              </div>

              <div className="filter-group">
                <label>From Author</label>
                <input 
                  type="text"
                  placeholder="username"
                  value={filters.author || ''}
                  onChange={(e) => handleFilterChange('author', e.target.value || null)}
                />
              </div>

              <div className="filter-group">
                <label>Min Likes</label>
                <input 
                  type="number"
                  placeholder="0"
                  min="0"
                  value={filters.minLikes || ''}
                  onChange={(e) => handleFilterChange('minLikes', e.target.value ? parseInt(e.target.value) : null)}
                />
              </div>

              <div className="filter-group checkbox-group">
                <label>
                  <input 
                    type="checkbox"
                    checked={filters.hasMedia === true}
                    onChange={(e) => handleFilterChange('hasMedia', e.target.checked ? true : null)}
                  />
                  <span>Has Media</span>
                </label>
              </div>
            </div>

            <div className="filter-tip">
              <span className="tip-icon">💡</span>
              <span>
                Tip: Use <code>from:username</code>, <code>min_likes:1000</code>, 
                <code>has:media</code>, <code>"exact phrase"</code>, and <code>AND</code> operator
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default SearchBar;

