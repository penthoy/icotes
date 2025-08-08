/**
 * Debug Logger for tracking workspace path resolution
 * Logs both to console and to backend logs folder
 */

interface DebugLogEntry {
  timestamp: string;
  component: string;
  action: string;
  path: string;
  source: string;
  details?: any;
}

class DebugLogger {
  private logs: DebugLogEntry[] = [];

  async logWorkspacePath(component: string, action: string, path: string, source: string, details?: any) {
    const entry: DebugLogEntry = {
      timestamp: new Date().toISOString(),
      component,
      action,
      path,
      source,
      details
    };

    this.logs.push(entry);
    
    // Console log with clear formatting
    console.group(`🔍 [WORKSPACE DEBUG] ${component} - ${action}`);
    console.log(`📍 Path: ${path}`);
    console.log(`📝 Source: ${source}`);
    if (details) {
      console.log(`📋 Details:`, details);
    }
    console.groupEnd();

    // Try to send to backend for file logging
    try {
      await fetch('/api/debug-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry)
      });
    } catch (error) {
      console.warn('Failed to send debug log to backend:', error);
    }
  }

  getLogs(): DebugLogEntry[] {
    return [...this.logs];
  }

  clearLogs(): void {
    this.logs = [];
  }
}

export const debugLogger = new DebugLogger();
