/**
 * ICUI Framework - Panel Content Component
 * Content container with consistent padding, styling, and error boundaries
 */

import React, { Component, ReactNode, ErrorInfo } from 'react';
import { ICUIPanelContentProps } from '../types/icui-panel';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary for Panel Content
 */
class PanelContentErrorBoundary extends Component<
  { children: ReactNode }, 
  ErrorBoundaryState
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo,
    });
    
    console.error('Panel content error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="icui-panel-error">
          <div className="icui-error-content">
            <div className="icui-error-icon">⚠️</div>
            <h3 className="icui-error-title">Panel Error</h3>
            <p className="icui-error-message">
              {this.state.error?.message || 'An unexpected error occurred in this panel.'}
            </p>
            <div className="icui-error-actions">
              <button 
                className="icui-error-retry"
                onClick={this.handleRetry}
              >
                Retry
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="icui-error-details">
                <summary>Error Details (Development)</summary>
                <pre className="icui-error-stack">
                  {this.state.error?.stack}
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Panel Content Component
 * Provides consistent styling and error boundaries for panel content
 */
export const ICUIPanelContent: React.FC<ICUIPanelContentProps> = ({
  panel,
  children,
  className = '',
  padding = true,
  scrollable,
}) => {
  // Determine scrollable behavior
  const isScrollable = scrollable !== undefined 
    ? scrollable 
    : panel.config.contentType === 'scrollable';

  // Build content classes
  const contentClasses = [
    'icui-panel-content',
    `icui-content-${panel.config.contentType}`,
    padding ? 'icui-content-padded' : 'icui-content-no-padding',
    isScrollable ? 'icui-content-scrollable' : 'icui-content-fixed',
    className,
  ].filter(Boolean).join(' ');

  // Content styles
  const contentStyles: React.CSSProperties = {
    height: panel.state === 'minimized' ? 0 : undefined,
    overflow: isScrollable ? 'auto' : 'hidden',
    opacity: panel.state === 'minimized' ? 0 : 1,
    transition: 'height 0.2s ease-in-out, opacity 0.2s ease-in-out',
  };

  return (
    <div 
      className={contentClasses}
      style={contentStyles}
      data-panel-content={panel.id}
    >
      <PanelContentErrorBoundary>
        {children}
      </PanelContentErrorBoundary>
    </div>
  );
};

export default ICUIPanelContent;
