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
  private isCurrentlyFlushing: boolean = false; // Add mutex flag to prevent concurrent flushes
  private originalConsole: {
    log: typeof console.log;
    warn: typeof console.warn;
    error: typeof console.error;
  };

  constructor() {
    this.sessionId = this.generateSessionId();
    
    // Store original console methods before intercepting
    this.originalConsole = {
      log: console.log.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console)
    };
    
    // Intercept console methods to capture all logs
    this.interceptConsole();
    
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

  private interceptConsole(): void {
    // Intercept console.log
    console.log = (...args: any[]) => {
      this.originalConsole.log(...args);
      
      // Extract component from call stack or use CONSOLE
      const component = this.extractComponentFromStack() || 'CONSOLE';
      const message = args.map(arg => this.stringifyArg(arg)).join(' ');
      
      const entry = this.createLogEntry(LogLevel.INFO, component, message);
      this.addToQueue(entry);
    };

    // Intercept console.warn
    console.warn = (...args: any[]) => {
      this.originalConsole.warn(...args);
      
      const component = this.extractComponentFromStack() || 'CONSOLE';
      const message = args.map(arg => this.stringifyArg(arg)).join(' ');
      
      const entry = this.createLogEntry(LogLevel.WARN, component, message);
      this.addToQueue(entry);
    };

    // Intercept console.error
    console.error = (...args: any[]) => {
      this.originalConsole.error(...args);
      
      const component = this.extractComponentFromStack() || 'CONSOLE';
      const message = args.map(arg => this.stringifyArg(arg)).join(' ');
      
      // Extract error object if present
      const errorObj = args.find(arg => arg instanceof Error) as Error | undefined;
      
      const entry = this.createLogEntry(LogLevel.ERROR, component, message, undefined, errorObj);
      this.addToQueue(entry);
    };
  }

  private stringifyArg(arg: any): string {
    if (arg === null) return 'null';
    if (arg === undefined) return 'undefined';
    if (typeof arg === 'string') return arg;
    if (typeof arg === 'number' || typeof arg === 'boolean') return String(arg);
    if (arg instanceof Error) return `${arg.name}: ${arg.message}`;
    
    try {
      // Try to stringify objects, but limit size
      const str = JSON.stringify(arg);
      return str.length > 200 ? str.substring(0, 200) + '...' : str;
    } catch {
      return String(arg);
    }
  }

  private extractComponentFromStack(): string | null {
    try {
      const stack = new Error().stack;
      if (!stack) return null;
      
      // Parse stack trace to find the calling file/component
      const lines = stack.split('\n');
      // Skip first 4 lines (Error, interceptConsole, console method, actual caller)
      for (let i = 4; i < Math.min(lines.length, 8); i++) {
        const line = lines[i];
        // Extract filename from stack trace
        const match = line.match(/\/([^/]+)\.(tsx?|jsx?):/);
        if (match) {
          return match[1].toUpperCase().replace(/-/g, '_');
        }
      }
      return null;
    } catch {
      return null;
    }
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
    // Use original console to prevent recursion
    this.originalConsole.log(`[${component}] ${message}`, data || '');
  }

  info(component: string, message: string, data?: any): void {
    const entry = this.createLogEntry(LogLevel.INFO, component, message, data);
    this.addToQueue(entry);
    this.originalConsole.log(`[${component}] ${message}`, data || '');
  }

  warn(component: string, message: string, data?: any): void {
    const entry = this.createLogEntry(LogLevel.WARN, component, message, data);
    this.addToQueue(entry);
    this.originalConsole.warn(`[${component}] ${message}`, data || '');
  }

  error(component: string, message: string, data?: any, error?: Error): void {
    const entry = this.createLogEntry(LogLevel.ERROR, component, message, data, error);
    this.addToQueue(entry);
    this.originalConsole.error(`[${component}] ${message}`, data || '', error || '');
  }

  private addToQueue(entry: LogEntry): void {
    // Drop known noisy logs that don't aid debugging (INFO/DEBUG only)
    if (this.shouldDrop(entry)) {
      return;
    }

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

  // Heuristic filter to reduce log noise sent to backend
  private shouldDrop(entry: LogEntry): boolean {
    // Never drop warnings or errors
    if (entry.level === LogLevel.ERROR || entry.level === LogLevel.WARN) return false;

    const msg = entry.message || '';
    // SCM polling messages can be very frequent; suppress at INFO/DEBUG
    if (/Getting SCM (status|repo info|diff) from:/i.test(msg)) return true;
    if (/\/api\/scm\/(status|repo|diff)/.test(msg)) return true;

    // Allow everything else
    return false;
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
    if (!this.isFlushingEnabled || this.logQueue.length === 0 || this.isCurrentlyFlushing) {
      return;
    }

    // Set mutex to prevent concurrent flushes
    this.isCurrentlyFlushing = true;

    const logsToFlush = [...this.logQueue];
    this.logQueue = [];

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
      // Clear mutex flag after flush attempt
      this.isCurrentlyFlushing = false;
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
