/**
 * ICUI Framework - Base Footer Component
 * Base footer component that provides common footer functionality and can be extended
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';

// Backend client for direct connection checking (from ICUIEditor)
class FooterBackendClient {
  private backendUrl: string;

  constructor() {
    this.backendUrl = (import.meta as any).env?.VITE_BACKEND_URL || (import.meta as any).env?.VITE_API_URL || '';
  }

  async checkConnection(): Promise<boolean> {
    try {
      // Default to localhost:8000 if no backend URL is configured
      const url = this.backendUrl || 'http://localhost:8000';
      const response = await fetch(`${url}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  }
}

export interface ICUIBaseFooterProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
  // Status information
  statusItems?: Array<{
    id: string;
    label: string;
    value: string | number;
    icon?: string;
    color?: string;
    onClick?: () => void;
  }>;
  // Connection status (ignored - we check directly)
  connectionStatus?: 'connected' | 'disconnected' | 'connecting' | 'error';
  // Custom status text
  statusText?: string;
}

/**
 * Base Footer Component
 * Provides common footer functionality with status bar, connection status, and custom content
 */
export const ICUIBaseFooter: React.FC<ICUIBaseFooterProps> = ({
  className = '',
  style,
  children,
  statusItems = [],
  connectionStatus = 'connected', // This prop is now ignored - we check directly
  statusText = 'Ready',
}) => {
  // Direct backend connection state (independent of props)
  const [realConnectionStatus, setRealConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'error'>('disconnected');
  const backendClient = useRef(new FooterBackendClient());

  // Direct backend connection check (same logic as ICUIEditor)
  const checkBackendConnection = useCallback(async () => {
    try {
      const isConnected = await backendClient.current.checkConnection();
      setRealConnectionStatus(isConnected ? 'connected' : 'disconnected');
      return isConnected;
    } catch (error) {
      setRealConnectionStatus('error');
      return false;
    }
  }, []);

  // Initialize backend connection check
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Use real connection status instead of prop
  const effectiveConnectionStatus = realConnectionStatus;

  // Get connection status color
  const getConnectionStatusColor = () => {
    switch (effectiveConnectionStatus) {
      case 'connected':
        return 'var(--icui-success)';
      case 'disconnected':
        return 'var(--icui-error)';
      case 'connecting':
        return 'var(--icui-warning)';
      case 'error':
        return 'var(--icui-error)';
      default:
        return 'var(--icui-text-secondary)';
    }
  };

  // Get connection status text
  const getConnectionStatusText = () => {
    switch (effectiveConnectionStatus) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Disconnected';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  };

  return (
    <div 
      className={`icui-base-footer flex items-center justify-between border-t text-sm shrink-0 ${className}`}
      style={{
        backgroundColor: 'var(--icui-bg-secondary)',
        borderColor: 'var(--icui-border-subtle)',
        color: 'var(--icui-text-secondary)',
        padding: '4px 16px', // Compact padding
        minHeight: '28px', // Compact minimum height
        ...style,
      }}
    >
      {/* Left side - Status Items */}
      <div className="flex items-center space-x-4">
        {statusItems.map(item => (
          <div 
            key={item.id}
            className={`flex items-center space-x-1 ${item.onClick ? 'cursor-pointer hover:text-white' : ''}`}
            onClick={item.onClick}
            style={{ color: item.color || 'inherit' }}
          >
            {item.icon && <span className="text-xs">{item.icon}</span>}
            <span>
              {item.label}: {item.value}
            </span>
          </div>
        ))}
        
        {/* Status Text */}
        <span>{statusText}</span>
      </div>

      {/* Right side - Connection Status and Custom Content */}
      <div className="flex items-center space-x-4">
        {/* Custom content */}
        {children}

        {/* Connection Status */}
        <div className="flex items-center space-x-2">
          <div 
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: getConnectionStatusColor() }}
          />
          <span className="text-xs">
            {getConnectionStatusText()}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ICUIBaseFooter; 