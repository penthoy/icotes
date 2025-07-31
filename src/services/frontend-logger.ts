/**
 * Frontend Logger Service
 * Integrates frontend logging with backend log storage
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  component: string;
  message: string;
  data?: any;
  error?: string;
  sessionId?: string;
  connectionId?: string;
}

class FrontendLogger {
  private sessionId: string;
  private logQueue: LogEntry[] = [];
  private flushInterval: number = 5000; // 5 seconds
  private maxQueueSize: number = 100;
  private flushTimer?: NodeJS.Timeout;
  private isFlushingEnabled: boolean = true; // Re-enable backend logging with safety measures

  constructor() {
    this.sessionId = this.generateSessionId();
    this.startPeriodicFlush();
    
    // Capture unhandled errors
    window.addEventListener('error', (event) => {
      this.error('GLOBAL_ERROR', 'Unhandled error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error?.stack
      });
    });

    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error('GLOBAL_ERROR', 'Unhandled promise rejection', {
        reason: event.reason,
        stack: event.reason?.stack
      });
    });
  }

  private generateSessionId(): string {
    return `frontend-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private createLogEntry(level: LogLevel, component: string, message: string, data?: any, error?: Error): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      data,
      error: error ? `${error.name}: ${error.message}\n${error.stack}` : undefined,
      sessionId: this.sessionId
    };
  }

  debug(component: string, message: string, data?: any): void {
    const entry = this.createLogEntry(LogLevel.DEBUG, component, message, data);
    this.addToQueue(entry);
    // Only log to console, don't use our logger to prevent recursion
    if (typeof console !== 'undefined' && console.log) {
      console.log(`[${component}] ${message}`, data || '');
    }
  }

  info(component: string, message: string, data?: any): void {
    const entry = this.createLogEntry(LogLevel.INFO, component, message, data);
    this.addToQueue(entry);
    if (typeof console !== 'undefined' && console.log) {
      console.log(`[${component}] ${message}`, data || '');
    }
  }

  warn(component: string, message: string, data?: any): void {
    const entry = this.createLogEntry(LogLevel.WARN, component, message, data);
    this.addToQueue(entry);
    if (typeof console !== 'undefined' && console.warn) {
      console.warn(`[${component}] ${message}`, data || '');
    }
  }

  error(component: string, message: string, data?: any, error?: Error): void {
    const entry = this.createLogEntry(LogLevel.ERROR, component, message, data, error);
    this.addToQueue(entry);
    if (typeof console !== 'undefined' && console.error) {
      console.error(`[${component}] ${message}`, data || '', error || '');
    }
  }

  private addToQueue(entry: LogEntry): void {
    this.logQueue.push(entry);
    
    // Prevent queue from growing too large
    if (this.logQueue.length > this.maxQueueSize) {
      this.logQueue = this.logQueue.slice(-this.maxQueueSize);
    }

    // Flush immediately for error level logs
    if (entry.level === LogLevel.ERROR) {
      this.flushLogs();
    }
  }

  private startPeriodicFlush(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    
    this.flushTimer = setInterval(() => {
      this.flushLogs();
    }, this.flushInterval);
  }

  private async flushLogs(): Promise<void> {
    if (!this.isFlushingEnabled || this.logQueue.length === 0) {
      return;
    }

    const logsToFlush = [...this.logQueue];
    this.logQueue = [];

    // Prevent recursive logging during flush
    this.isFlushingEnabled = false;

    try {
      const response = await fetch('/api/logs/frontend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: this.sessionId,
          logs: logsToFlush
        })
      });

      if (!response.ok) {
        // If backend is not available, silently re-queue logs (but limit size)
        this.logQueue = [...logsToFlush.slice(-10), ...this.logQueue].slice(-50);
      }
    } catch (error) {
      // Backend not available, silently re-queue logs
      this.logQueue = [...logsToFlush.slice(-10), ...this.logQueue].slice(-50);
    } finally {
      // Re-enable logging after flush attempt
      this.isFlushingEnabled = true;
    }
  }

  // Method to get current logs for debugging
  getCurrentLogs(): LogEntry[] {
    return [...this.logQueue];
  }

  // Method to clear logs
  clearLogs(): void {
    this.logQueue = [];
  }

  // Method to disable/enable log flushing to backend
  setFlushingEnabled(enabled: boolean): void {
    this.isFlushingEnabled = enabled;
  }

  // Method to force flush
  async forceFlush(): Promise<void> {
    await this.flushLogs();
  }

  // Cleanup method
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    this.flushLogs(); // Final flush
  }
}

// Create singleton instance
export const frontendLogger = new FrontendLogger();

// Export convenience methods
export const log = {
  debug: (component: string, message: string, data?: any) => frontendLogger.debug(component, message, data),
  info: (component: string, message: string, data?: any) => frontendLogger.info(component, message, data),
  warn: (component: string, message: string, data?: any) => frontendLogger.warn(component, message, data),
  error: (component: string, message: string, data?: any, error?: Error) => frontendLogger.error(component, message, data, error)
};
