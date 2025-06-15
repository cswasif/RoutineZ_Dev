import React from 'react';

const AnimatedGridPattern = ({ numSquares = 30, maxOpacity = 0.3, duration = 3, repeatDelay = 1, className = '' }) => {
  return (
    <div className={`grid-container ${className}`}>
      <div className="grid-pattern" />
      <div className="grid-gradient" />
    </div>
  );
};

export default AnimatedGridPattern; 