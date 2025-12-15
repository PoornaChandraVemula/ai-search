import React from 'react';
import { motion } from 'framer-motion';
import './LoadingState.css';

function LoadingState() {
  return (
    <div className="loading-state">
      <motion.div 
        className="loading-content"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <div className="grok-loader">
          <svg width="80" height="80" viewBox="0 0 100 100">
            <defs>
              <linearGradient id="loaderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00ff88">
                  <animate 
                    attributeName="stop-color" 
                    values="#00ff88;#00d4ff;#8b5cf6;#00ff88" 
                    dur="3s" 
                    repeatCount="indefinite"
                  />
                </stop>
                <stop offset="100%" stopColor="#00d4ff">
                  <animate 
                    attributeName="stop-color" 
                    values="#00d4ff;#8b5cf6;#00ff88;#00d4ff" 
                    dur="3s" 
                    repeatCount="indefinite"
                  />
                </stop>
              </linearGradient>
            </defs>
            
            <circle 
              cx="50" 
              cy="50" 
              r="40" 
              fill="none" 
              stroke="url(#loaderGrad)" 
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray="200"
              strokeDashoffset="50"
            >
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="0 50 50"
                to="360 50 50"
                dur="2s"
                repeatCount="indefinite"
              />
            </circle>
            
            <circle 
              cx="50" 
              cy="50" 
              r="25" 
              fill="none" 
              stroke="url(#loaderGrad)" 
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray="120"
              strokeDashoffset="30"
              opacity="0.6"
            >
              <animateTransform
                attributeName="transform"
                type="rotate"
                from="360 50 50"
                to="0 50 50"
                dur="1.5s"
                repeatCount="indefinite"
              />
            </circle>
          </svg>
        </div>
        
        <motion.p 
          className="loading-text"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <span className="gradient-text">Grok</span> is analyzing your query...
        </motion.p>
        
        <div className="loading-steps">
          <motion.div 
            className="step active"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <span className="step-icon">✓</span>
            <span>Understanding query intent</span>
          </motion.div>
          <motion.div 
            className="step active"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
          >
            <span className="step-icon">✓</span>
            <span>Enhancing search terms</span>
          </motion.div>
          <motion.div 
            className="step loading"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.8 }}
          >
            <span className="step-spinner"></span>
            <span>Searching posts...</span>
          </motion.div>
          <motion.div 
            className="step pending"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 1 }}
          >
            <span className="step-icon">○</span>
            <span>Generating summary</span>
          </motion.div>
        </div>
      </motion.div>
      
      {/* Skeleton Results */}
      <div className="skeleton-results">
        {[1, 2, 3].map((i) => (
          <motion.div 
            key={i}
            className="skeleton-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 * i }}
          >
            <div className="skeleton-header">
              <div className="skeleton skeleton-avatar"></div>
              <div className="skeleton-author">
                <div className="skeleton skeleton-name"></div>
                <div className="skeleton skeleton-handle"></div>
              </div>
            </div>
            <div className="skeleton skeleton-line"></div>
            <div className="skeleton skeleton-line short"></div>
            <div className="skeleton-metrics">
              <div className="skeleton skeleton-metric"></div>
              <div className="skeleton skeleton-metric"></div>
              <div className="skeleton skeleton-metric"></div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export default LoadingState;

