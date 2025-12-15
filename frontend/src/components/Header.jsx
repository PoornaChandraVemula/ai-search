import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import './Header.css';

function Header({ sidebarOpen, toggleSidebar }) {
  const [isHealthy, setIsHealthy] = useState(null);
  const [grokConfigured, setGrokConfigured] = useState(false);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const response = await fetch('/health');
      if (response.ok) {
        const data = await response.json();
        setIsHealthy(true);
        setGrokConfigured(data.grok_configured);
      } else {
        setIsHealthy(false);
      }
    } catch {
      setIsHealthy(false);
    }
  };

  return (
    <header className="header">
      <div className="header-left">
        <button 
          className="sidebar-toggle"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
        >
          <motion.div
            animate={{ rotate: sidebarOpen ? 0 : 180 }}
            transition={{ duration: 0.3 }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12h18M3 6h18M3 18h18" />
            </svg>
          </motion.div>
        </button>
        
        <div className="logo">
          <div className="logo-icon">
            <svg width="32" height="32" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#00ff88" />
                  <stop offset="100%" stopColor="#00d4ff" />
                </linearGradient>
              </defs>
              <circle cx="50" cy="50" r="42" fill="none" stroke="url(#logoGrad)" strokeWidth="4"/>
              <path d="M30 50 L45 65 L70 35" fill="none" stroke="url(#logoGrad)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span className="logo-text">
            <span className="gradient-text">Grok</span> X Search
          </span>
        </div>
      </div>

      <div className="header-right">
        <div className="status-indicators">
          <div className={`status-badge ${isHealthy ? 'healthy' : 'unhealthy'}`}>
            <span className="status-dot"></span>
            <span className="status-text">
              {isHealthy === null ? 'Checking...' : isHealthy ? 'API Online' : 'API Offline'}
            </span>
          </div>
          
          {isHealthy && (
            <div className={`status-badge ${grokConfigured ? 'healthy' : 'warning'}`}>
              <span className="status-dot"></span>
              <span className="status-text">
                {grokConfigured ? 'Grok Active' : 'Grok Not Configured'}
              </span>
            </div>
          )}
        </div>

        <a 
          href="https://x.ai" 
          target="_blank" 
          rel="noopener noreferrer"
          className="xai-link"
        >
          Powered by xAI
        </a>
      </div>
    </header>
  );
}

export default Header;

