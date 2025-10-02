/**
 * ICUI Framework - Base Footer Component
 * Base footer component that provides common footer functionality and can be extended
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { backendService, useTheme } from '../services';

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
  style = {},
  children,
  statusItems = [],
  statusText = '',
  connectionStatus
}) => {
  const [realConnectionStatus, setRealConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting' | 'error'>('connecting');
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [hopSummary, setHopSummary] = useState<string>('local');
  
  // Use centralized theme service instead of manual theme detection
  const { theme } = useTheme();

  // Check backend connection status using centralized service
  const checkBackendConnection = useCallback(async () => {
    try {
      setRealConnectionStatus('connecting');
      const status = await backendService.getConnectionStatus();
      if (status.connected) {
        setRealConnectionStatus('connected');
      } else {
        setRealConnectionStatus('disconnected');
      }
      setLastChecked(new Date());
    } catch (error) {
      console.error('Backend connection failed:', error);
      setRealConnectionStatus('error');
      setLastChecked(new Date());
    }
  }, []);

  // Initialize backend connection check
  useEffect(() => {
    checkBackendConnection();
    const interval = setInterval(checkBackendConnection, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [checkBackendConnection]);

  // Hop status indicator (non-blocking)
  useEffect(() => {
    let mounted = true;
    const updateHop = async () => {
      try {
        if ((backendService as any).getHopStatus) {
          const s = await (backendService as any).getHopStatus();
          if (!mounted) return;
          if (s?.connected) {
            setHopSummary(`${s.username || ''}@${s.host || 'remote'}`);
          } else {
            setHopSummary('local');
          }
        }
      } catch { /* ignore */ }
    };
    updateHop();
    const onHop = (s: any) => {
      if (s?.connected) setHopSummary(`${s.username || ''}@${s.host || 'remote'}`);
      else setHopSummary('local');
    };
    (backendService as any).on?.('hop_status', onHop);
    return () => { mounted = false; (backendService as any).off?.('hop_status', onHop); };
  }, []);

  // Use provided connection status or fall back to real status
  const effectiveConnectionStatus = connectionStatus || realConnectionStatus;

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
          <span className="text-xs">{getConnectionStatusText()}</span>
          <span className="text-xs opacity-80">[{hopSummary}]</span>
        </div>
      </div>
    </div>
  );
};

export default ICUIBaseFooter; 