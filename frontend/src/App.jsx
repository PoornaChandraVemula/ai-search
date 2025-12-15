import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SearchBar from './components/SearchBar';
import SearchResults from './components/SearchResults';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import LoadingState from './components/LoadingState';
import EmptyState from './components/EmptyState';
import './App.css';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    sortBy: 'relevance',
    sortOrder: 'desc',
    hasMedia: null,
    minLikes: null,
    author: null,
    searchMode: 'keyword', // keyword or semantic
  });
  const [embeddingAvailable, setEmbeddingAvailable] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Fetch system stats on mount
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const handleSearch = useCallback(async (query, customFilters = null) => {
    if (!query.trim()) return;
    
    setIsLoading(true);
    setError(null);
    setSearchQuery(query);

    const activeFilters = customFilters || filters;
    
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          limit: 30,
          offset: 0,
          sort_by: activeFilters.sortBy,
          sort_order: activeFilters.sortOrder,
          has_media: activeFilters.hasMedia,
          min_likes: activeFilters.minLikes,
          author: activeFilters.author,
          use_grok_enhancement: true,
          search_mode: activeFilters.searchMode || 'keyword'
        })
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setSearchResults(data);
      
      // Update embedding availability from response
      if (data.embedding_available !== undefined) {
        setEmbeddingAvailable(data.embedding_available);
      }
      
      fetchStats(); // Refresh stats after search
    } catch (err) {
      setError(err.message);
      setSearchResults(null);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    if (searchQuery) {
      handleSearch(searchQuery, newFilters);
    }
  };

  return (
    <div className="app">
      <Header 
        sidebarOpen={sidebarOpen}
        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />
      
      <div className="app-layout">
        <AnimatePresence>
          {sidebarOpen && (
            <Sidebar 
              stats={stats}
              onQuickSearch={(query) => handleSearch(query)}
            />
          )}
        </AnimatePresence>

        <main className="main-content">
          <div className="search-container">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="search-hero"
            >
              <h1 className="hero-title">
                <span className="gradient-text">Grok-Powered</span> X Search
              </h1>
              <p className="hero-subtitle">
                Intelligent discovery and retrieval of posts from popular accounts
              </p>
            </motion.div>

            <SearchBar 
              onSearch={handleSearch}
              filters={filters}
              onFilterChange={handleFilterChange}
              isLoading={isLoading}
              embeddingAvailable={embeddingAvailable}
            />
          </div>

          <div className="results-container">
            {isLoading ? (
              <LoadingState />
            ) : error ? (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="error-state"
              >
                <div className="error-icon">⚠️</div>
                <h3>Search Error</h3>
                <p>{error}</p>
                <button onClick={() => handleSearch(searchQuery)} className="retry-btn">
                  Try Again
                </button>
              </motion.div>
            ) : searchResults ? (
              <SearchResults 
                results={searchResults}
                query={searchQuery}
                onRelatedSearch={handleSearch}
              />
            ) : (
              <EmptyState 
                stats={stats}
                onQuickSearch={handleSearch}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;

