import React, { useState, useEffect } from 'react';
import { API_BASE } from '../config';

const ApiStatus = () => {
  const [status, setStatus] = useState({
    isOnline: false,
    cached: true,
    error: null
  });

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/connapi-status`);
        const data = await response.json();
        setStatus({
          isOnline: !data.cached, // If cached is false, API is online
          cached: data.cached,
          error: data.error
        });
      } catch (error) {
        setStatus({
          isOnline: false,
          cached: true,
          error: error.message
        });
      }
    };

    // Check immediately and then every 30 seconds
    checkStatus();
    const interval = setInterval(checkStatus, 30000);

    return () => clearInterval(interval);
  }, []);

  const getStatusText = () => {
    if (status.error) return "Offline";
    if (status.isOnline) return "Online (Live)";
    return "Offline (Cached)";
  };

  const getStatusColor = () => {
    if (status.error || !status.isOnline) return "#ff4444";
    return "#44ff44";
  };

  const handleClick = () => {
    window.open('https://connectlive-nine.vercel.app/', '_blank');
  };

  return (
    <div 
      onClick={handleClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 8px',
        borderRadius: '4px',
        backgroundColor: '#333',
        cursor: 'pointer',
        userSelect: 'none',
        transition: 'opacity 0.2s',
        marginLeft: '8px'
      }}
    >
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: getStatusColor(),
          marginRight: '6px'
        }}
      />
      <span style={{ fontSize: '14px', color: '#fff' }}>
        {getStatusText()}
      </span>
    </div>
  );
};

export default ApiStatus; 