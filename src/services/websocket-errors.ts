/**
 * WebSocket Error Handling System
 * 
 * Provides structured error categorization, recovery strategies, and user-friendly
 * error messages for WebSocket connections across all services.
 */

export enum WebSocketErrorType {
  CONNECTION_FAILED = 'connection_failed',
  AUTHENTICATION_FAILED = 'authentication_failed',
  SERVICE_UNAVAILABLE = 'service_unavailable',
  PROTOCOL_ERROR = 'protocol_error',
  TIMEOUT = 'timeout',
  NETWORK_ERROR = 'network_error',
  INVALID_MESSAGE = 'invalid_message',
  RATE_LIMITED = 'rate_limited',
  PERMISSION_DENIED = 'permission_denied',
  RESOURCE_NOT_FOUND = 'resource_not_found'
}

export interface WebSocketError {
  type: WebSocketErrorType;
  message: string;
  code?: number;
  details?: any;
  recoverable: boolean;
  retryAfter?: number;
  timestamp: number;
  connectionId?: string;
  serviceType?: string;
}

export interface ErrorContext {
  connectionId?: string;
  serviceType?: string;
  endpoint?: string;
  userAgent?: string;
  timestamp: number;
  additionalInfo?: Record<string, any>;
}

export interface RecoveryStrategy {
  type: 'reconnect' | 'refresh' | 'auth' | 'wait' | 'manual';
  delay?: number;
  maxAttempts?: number;
  message: string;
  action?: () => Promise<void>;
}

export class WebSocketErrorHandler {
  private static errorHistory: WebSocketError[] = [];
  private static readonly MAX_ERROR_HISTORY = 100;

  /**
   * Categorize and enhance error information
   */
  static categorizeError(event: Event | CloseEvent, context?: ErrorContext): WebSocketError {
    const timestamp = Date.now();
    
    if (event instanceof CloseEvent) {
      return this.categorizeCloseEvent(event, context, timestamp);
    } else {
      return this.categorizeGenericError(event, context, timestamp);
    }
  }

  /**
   * Determine if an error should trigger a retry
   */
  static shouldRetry(error: WebSocketError): boolean {
    if (!error.recoverable) {
      return false;
    }

    // Don't retry authentication or permission errors
    if ([WebSocketErrorType.AUTHENTICATION_FAILED, WebSocketErrorType.PERMISSION_DENIED].includes(error.type)) {
      return false;
    }

    // Check if we should wait before retrying
    if (error.retryAfter && Date.now() - error.timestamp < error.retryAfter) {
      return false;
    }

    return true;
  }

  /**
   * Get recommended recovery strategy for an error
   */
  static getRecoveryStrategy(error: WebSocketError): RecoveryStrategy {
    switch (error.type) {
      case WebSocketErrorType.AUTHENTICATION_FAILED:
        return {
          type: 'auth',
          message: 'Authentication failed. Please refresh the page to re-authenticate.',
          action: async () => WebSocketErrorHandler.reloadPage()
        };

      case WebSocketErrorType.SERVICE_UNAVAILABLE:
        return {
          type: 'wait',
          delay: error.retryAfter || 5000,
          maxAttempts: 3,
          message: 'Service is temporarily unavailable. Retrying automatically...'
        };

      case WebSocketErrorType.RATE_LIMITED:
        return {
          type: 'wait',
          delay: error.retryAfter || 60000,
          message: 'Rate limit exceeded. Please wait before trying again.'
        };

      case WebSocketErrorType.PERMISSION_DENIED:
        return {
          type: 'manual',
          message: 'Access denied. Please check your permissions or contact administrator.'
        };

      case WebSocketErrorType.NETWORK_ERROR:
      case WebSocketErrorType.CONNECTION_FAILED:
      case WebSocketErrorType.TIMEOUT:
        return {
          type: 'reconnect',
          delay: 1000,
          maxAttempts: 5,
          message: 'Connection lost. Attempting to reconnect...'
        };

      case WebSocketErrorType.PROTOCOL_ERROR:
      case WebSocketErrorType.INVALID_MESSAGE:
        return {
          type: 'refresh',
          message: 'Communication error. Please refresh the page.',
          action: async () => window.location.reload()
        };

      case WebSocketErrorType.RESOURCE_NOT_FOUND:
        return {
          type: 'manual',
          message: 'Requested resource not found. Please check the connection settings.'
        };

      default:
        return {
          type: 'reconnect',
          delay: 2000,
          maxAttempts: 3,
          message: 'Unexpected error occurred. Attempting to recover...'
        };
    }
  }

  /**
   * Get user-friendly error message
   */
  static getUserFriendlyMessage(error: WebSocketError): string {
    const baseMessages: Record<WebSocketErrorType, string> = {
      [WebSocketErrorType.CONNECTION_FAILED]: 'Unable to connect to the server. Please check your internet connection.',
      [WebSocketErrorType.AUTHENTICATION_FAILED]: 'Authentication failed. Please refresh the page to sign in again.',
      [WebSocketErrorType.SERVICE_UNAVAILABLE]: 'The service is temporarily unavailable. Please try again in a few moments.',
      [WebSocketErrorType.PROTOCOL_ERROR]: 'A communication error occurred. Please refresh the page.',
      [WebSocketErrorType.TIMEOUT]: 'Connection timed out. Please check your internet connection.',
      [WebSocketErrorType.NETWORK_ERROR]: 'Network error occurred. Please check your internet connection.',
      [WebSocketErrorType.INVALID_MESSAGE]: 'Invalid data received. Please refresh the page.',
      [WebSocketErrorType.RATE_LIMITED]: 'Too many requests. Please wait a moment before trying again.',
      [WebSocketErrorType.PERMISSION_DENIED]: 'Access denied. You may not have permission to perform this action.',
      [WebSocketErrorType.RESOURCE_NOT_FOUND]: 'The requested resource was not found.'
    };

    let message = baseMessages[error.type] || 'An unexpected error occurred.';
    
    // Add service-specific context
    if (error.serviceType) {
      const serviceNames: Record<string, string> = {
        terminal: 'Terminal',
        chat: 'Chat',
        main: 'Backend'
      };
      
      const serviceName = serviceNames[error.serviceType] || error.serviceType;
      message = `${serviceName}: ${message}`;
    }

    return message;
  }

  /**
   * Log error for debugging and analytics
   */
  static logError(error: WebSocketError): void {
    // Add to error history
    this.errorHistory.push(error);
    
    // Maintain history size
    if (this.errorHistory.length > this.MAX_ERROR_HISTORY) {
      this.errorHistory = this.errorHistory.slice(-this.MAX_ERROR_HISTORY);
    }

    // Console logging with appropriate level
    const logLevel = error.recoverable ? 'warn' : 'error';
    console[logLevel]('[WebSocket Error]', {
      type: error.type,
      message: error.message,
      code: error.code,
      recoverable: error.recoverable,
      connectionId: error.connectionId,
      serviceType: error.serviceType,
      timestamp: new Date(error.timestamp).toISOString(),
      details: error.details
    });

    // Send to analytics if available
    if (typeof (window as any).analytics !== 'undefined') {
      (window as any).analytics.track('WebSocket Error', {
        error_type: error.type,
        service_type: error.serviceType,
        recoverable: error.recoverable,
        error_code: error.code
      });
    }
  }

  /**
   * Get error statistics
   */
  static getErrorStatistics(): {
    total: number;
    byType: Record<WebSocketErrorType, number>;
    byService: Record<string, number>;
    recoverable: number;
    nonRecoverable: number;
    recentErrors: WebSocketError[];
  } {
    const byType = this.errorHistory.reduce((acc, error) => {
      acc[error.type] = (acc[error.type] || 0) + 1;
      return acc;
    }, {} as Record<WebSocketErrorType, number>);

    const byService = this.errorHistory.reduce((acc, error) => {
      if (error.serviceType) {
        acc[error.serviceType] = (acc[error.serviceType] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>);

    const recoverable = this.errorHistory.filter(e => e.recoverable).length;
    const nonRecoverable = this.errorHistory.length - recoverable;
    
    // Get recent errors (last 10)
    const recentErrors = this.errorHistory.slice(-10);

    return {
      total: this.errorHistory.length,
      byType,
      byService,
      recoverable,
      nonRecoverable,
      recentErrors
    };
  }

  /**
   * Clear error history
   */
  static clearErrorHistory(): void {
    this.errorHistory = [];
  }

  // Private helper methods

  private static categorizeCloseEvent(event: CloseEvent, context?: ErrorContext, timestamp?: number): WebSocketError {
    const baseError: Omit<WebSocketError, 'type' | 'message' | 'recoverable'> = {
      code: event.code,
      timestamp: timestamp || Date.now(),
      connectionId: context?.connectionId,
      serviceType: context?.serviceType,
      details: {
        reason: event.reason,
        wasClean: event.wasClean,
        endpoint: context?.endpoint
      }
    };

    switch (event.code) {
      case 1000: // Normal closure
        return {
          ...baseError,
          type: WebSocketErrorType.CONNECTION_FAILED,
          message: 'Connection closed normally',
          recoverable: false,
        };

      case 1001: // Going away
        return {
          ...baseError,
          type: WebSocketErrorType.CONNECTION_FAILED,
          message: 'Connection closed - endpoint going away',
          recoverable: true,
        };

      case 1002: // Protocol error
        return {
          ...baseError,
          type: WebSocketErrorType.PROTOCOL_ERROR,
          message: 'Connection closed due to protocol error',
          recoverable: false,
        };

      case 1003: // Unsupported data type
        return {
          ...baseError,
          type: WebSocketErrorType.PROTOCOL_ERROR,
          message: 'Connection closed - unsupported data type',
          recoverable: false,
        };

      case 1006: // Abnormal closure
        return {
          ...baseError,
          type: WebSocketErrorType.NETWORK_ERROR,
          message: 'Connection closed abnormally - possible network issue',
          recoverable: true,
        };

      case 1007: // Invalid frame payload data
        return {
          ...baseError,
          type: WebSocketErrorType.INVALID_MESSAGE,
          message: 'Connection closed - invalid message format',
          recoverable: false,
        };

      case 1008: // Policy violation
        return {
          ...baseError,
          type: WebSocketErrorType.PERMISSION_DENIED,
          message: 'Connection closed - policy violation',
          recoverable: false,
        };

      case 1009: // Message too big
        return {
          ...baseError,
          type: WebSocketErrorType.PROTOCOL_ERROR,
          message: 'Connection closed - message too large',
          recoverable: false,
        };

      case 1011: // Server error
        return {
          ...baseError,
          type: WebSocketErrorType.SERVICE_UNAVAILABLE,
          message: 'Connection closed - server encountered an error',
          recoverable: true,
          retryAfter: 5000,
        };

      case 1012: // Service restart
        return {
          ...baseError,
          type: WebSocketErrorType.SERVICE_UNAVAILABLE,
          message: 'Connection closed - service restarting',
          recoverable: true,
          retryAfter: 10000,
        };

      case 1013: // Try again later
        return {
          ...baseError,
          type: WebSocketErrorType.RATE_LIMITED,
          message: 'Connection closed - server overloaded, try again later',
          recoverable: true,
          retryAfter: 30000,
        };

      case 1014: // Bad gateway
        return {
          ...baseError,
          type: WebSocketErrorType.SERVICE_UNAVAILABLE,
          message: 'Connection closed - bad gateway',
          recoverable: true,
          retryAfter: 5000,
        };

      case 1015: // TLS handshake failure
        return {
          ...baseError,
          type: WebSocketErrorType.CONNECTION_FAILED,
          message: 'Connection closed - TLS handshake failed',
          recoverable: true,
        };

      // Custom application-specific codes
      case 4001:
        return {
          ...baseError,
          type: WebSocketErrorType.AUTHENTICATION_FAILED,
          message: 'Connection closed - authentication required',
          recoverable: false,
        };

      case 4002:
        return {
          ...baseError,
          type: WebSocketErrorType.PERMISSION_DENIED,
          message: 'Connection closed - insufficient permissions',
          recoverable: false,
        };

      case 4003:
        return {
          ...baseError,
          type: WebSocketErrorType.RESOURCE_NOT_FOUND,
          message: 'Connection closed - resource not found',
          recoverable: false,
        };

      case 4004:
        return {
          ...baseError,
          type: WebSocketErrorType.RATE_LIMITED,
          message: 'Connection closed - rate limit exceeded',
          recoverable: true,
          retryAfter: 60000,
        };

      default:
        return {
          ...baseError,
          type: WebSocketErrorType.CONNECTION_FAILED,
          message: event.reason || `Connection closed with unknown code: ${event.code}`,
          recoverable: true,
        };
    }
  }

  private static categorizeGenericError(event: Event, context?: ErrorContext, timestamp?: number): WebSocketError {
    return {
      type: WebSocketErrorType.NETWORK_ERROR,
      message: 'WebSocket connection error',
      recoverable: true,
      timestamp: timestamp || Date.now(),
      connectionId: context?.connectionId,
      serviceType: context?.serviceType,
      details: {
        event: event.type,
        endpoint: context?.endpoint,
        additionalInfo: context?.additionalInfo
      }
    };
  }

  /**
   * Safely reload the page, checking for window existence
   */
  static reloadPage(): void {
    if (typeof window !== 'undefined' && window.location) {
      window.location.reload();
    } else {
      // In non-browser environments (testing, server-side), log the action
      console.warn('Page reload requested but window.location is not available');
    }
  }
}

/**
 * Error recovery helper class
 */
export class ErrorRecoveryHelper {
  private static activeRecoveries = new Map<string, boolean>();

  /**
   * Execute recovery strategy
   */
  static async executeRecovery(
    error: WebSocketError, 
    onProgress?: (message: string) => void
  ): Promise<boolean> {
    const recoveryKey = `${error.connectionId}-${error.type}`;
    
    // Prevent duplicate recovery attempts
    if (this.activeRecoveries.get(recoveryKey)) {
      console.warn('Recovery already in progress for:', recoveryKey);
      return false;
    }

    this.activeRecoveries.set(recoveryKey, true);

    try {
      const strategy = WebSocketErrorHandler.getRecoveryStrategy(error);
      onProgress?.(strategy.message);

      switch (strategy.type) {
        case 'wait':
          if (strategy.delay) {
            await new Promise(resolve => setTimeout(resolve, strategy.delay));
          }
          return true;

        case 'auth':
        case 'refresh':
          if (strategy.action) {
            await strategy.action();
          }
          return true;

        case 'reconnect':
          // Recovery logic will be handled by ConnectionManager
          return true;

        case 'manual':
          // User intervention required
          onProgress?.(strategy.message);
          return false;

        default:
          return false;
      }
    } catch (recoveryError) {
      console.error('Recovery failed:', recoveryError);
      return false;
    } finally {
      this.activeRecoveries.delete(recoveryKey);
    }
  }

  /**
   * Check if recovery is in progress
   */
  static isRecoveryInProgress(connectionId: string, errorType: WebSocketErrorType): boolean {
    return this.activeRecoveries.get(`${connectionId}-${errorType}`) || false;
  }

  /**
   * Cancel recovery for a connection
   */
  static cancelRecovery(connectionId: string, errorType?: WebSocketErrorType): void {
    if (errorType) {
      this.activeRecoveries.delete(`${connectionId}-${errorType}`);
    } else {
      // Cancel all recoveries for this connection
      for (const key of this.activeRecoveries.keys()) {
        if (key.startsWith(connectionId)) {
          this.activeRecoveries.delete(key);
        }
      }
    }
  }
}
