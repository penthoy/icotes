/**
 * Debug Logger for Tab Switch Bug Investigation
 * 
 * Provides comprehensive logging for component lifecycle, tab operations,
 * and performance tracking to help identify the root cause of tab switching issues.
 */

export interface DebugLogEntry {
  timestamp: number;
  component: string;
  action: string;
  details?: any;
  performanceMarker?: string;
}

class DebugLogger {
  private logs: DebugLogEntry[] = [];
  private maxLogs = 1000; // Keep last 1000 entries
  private enabled = false;
  private performanceMarkers = new Map<string, number>();
  
  constructor() {
    // Enable debug logging in development or when explicitly set
    this.enabled = process.env.NODE_ENV === 'development' || 
                   localStorage.getItem('icui-debug-logging') === 'true';
    
    if (this.enabled) {
      console.log('[DebugLogger] Debug logging enabled');
      // Expose logger to window for console access
      (window as any).icuiDebugLogger = this;
    }
  }
  
  /**
   * Enable or disable debug logging
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
    localStorage.setItem('icui-debug-logging', enabled ? 'true' : 'false');
    console.log(`[DebugLogger] Debug logging ${enabled ? 'enabled' : 'disabled'}`);
  }
  
  /**
   * Log a component lifecycle event
   */
  lifecycle(component: string, action: 'mount' | 'unmount' | 'render' | 'update', details?: any): void {
    if (!this.enabled) return;
    
    const entry: DebugLogEntry = {
      timestamp: Date.now(),
      component,
      action: `lifecycle:${action}`,
      details
    };
    
    this.addLog(entry);
    
    // Log render frequency warnings
    if (action === 'render' || action === 'update') {
      this.checkRenderFrequency(component);
    }
    
    console.debug(`[${component}] ${action}`, details || '');
  }
  
  /**
   * Log a tab operation event
   */
  tabOperation(action: string, details?: any): void {
    if (!this.enabled) return;
    
    const entry: DebugLogEntry = {
      timestamp: Date.now(),
      component: 'TabSystem',
      action: `tab:${action}`,
      details
    };
    
    this.addLog(entry);
    console.debug(`[TabSystem] ${action}`, details || '');
  }
  
  /**
   * Log a command registry event
   */
  commandRegistry(action: string, commandId?: string, details?: any): void {
    if (!this.enabled) return;
    
    const entry: DebugLogEntry = {
      timestamp: Date.now(),
      component: 'CommandRegistry',
      action: `command:${action}`,
      details: { commandId, ...details }
    };
    
    this.addLog(entry);
    
    // Warn on excessive registrations
    if (action === 'register' || action === 'duplicate-attempt') {
      this.checkCommandRegistrationFrequency(commandId || 'unknown');
    }
    
    console.debug(`[CommandRegistry] ${action}`, commandId, details || '');
  }
  
  /**
   * Start a performance measurement
   */
  startPerformanceMark(markerId: string): void {
    if (!this.enabled) return;
    
    this.performanceMarkers.set(markerId, performance.now());
    performance.mark(`icui-${markerId}-start`);
  }
  
  /**
   * End a performance measurement and log the duration
   */
  endPerformanceMark(markerId: string, component?: string): number | null {
    if (!this.enabled) return null;
    
    const startTime = this.performanceMarkers.get(markerId);
    if (!startTime) {
      console.warn(`[DebugLogger] No start time found for marker: ${markerId}`);
      return null;
    }
    
    const duration = performance.now() - startTime;
    this.performanceMarkers.delete(markerId);
    
    performance.mark(`icui-${markerId}-end`);
    try {
      performance.measure(`icui-${markerId}`, `icui-${markerId}-start`, `icui-${markerId}-end`);
    } catch (e) {
      // Ignore if marks don't exist
    }
    
    const entry: DebugLogEntry = {
      timestamp: Date.now(),
      component: component || 'Performance',
      action: 'performance',
      details: { markerId, duration: `${duration.toFixed(2)}ms` },
      performanceMarker: markerId
    };
    
    this.addLog(entry);
    
    // Warn on slow operations (>100ms)
    if (duration > 100) {
      console.warn(`[Performance] Slow operation detected: ${markerId} took ${duration.toFixed(2)}ms`);
    } else {
      console.debug(`[Performance] ${markerId}: ${duration.toFixed(2)}ms`);
    }
    
    return duration;
  }
  
  /**
   * Log a form validation error
   */
  validationError(component: string, elementType: string, issue: string, details?: any): void {
    if (!this.enabled) return;
    
    const entry: DebugLogEntry = {
      timestamp: Date.now(),
      component,
      action: 'validation-error',
      details: { elementType, issue, ...details }
    };
    
    this.addLog(entry);
    console.error(`[${component}] Validation error: ${elementType} - ${issue}`, details || '');
  }
  
  /**
   * Get all logs or filtered logs
   */
  getLogs(filter?: { component?: string; action?: string; since?: number }): DebugLogEntry[] {
    let filtered = this.logs;
    
    if (filter?.component) {
      filtered = filtered.filter(log => log.component === filter.component);
    }
    
    if (filter?.action) {
      filtered = filtered.filter(log => log.action.includes(filter.action));
    }
    
    if (filter?.since) {
      filtered = filtered.filter(log => log.timestamp >= filter.since);
    }
    
    return filtered;
  }
  
  /**
   * Get a summary of component render counts
   */
  getRenderSummary(): Record<string, number> {
    const summary: Record<string, number> = {};
    
    this.logs
      .filter(log => log.action === 'lifecycle:render' || log.action === 'lifecycle:update')
      .forEach(log => {
        summary[log.component] = (summary[log.component] || 0) + 1;
      });
    
    return summary;
  }
  
  /**
   * Get a summary of command registration attempts
   */
  getCommandRegistrationSummary(): Record<string, { registered: number; duplicates: number }> {
    const summary: Record<string, { registered: number; duplicates: number }> = {};
    
    this.logs
      .filter(log => log.action.startsWith('command:'))
      .forEach(log => {
        const commandId = log.details?.commandId || 'unknown';
        if (!summary[commandId]) {
          summary[commandId] = { registered: 0, duplicates: 0 };
        }
        
        if (log.action === 'command:register') {
          summary[commandId].registered++;
        } else if (log.action === 'command:duplicate-attempt') {
          summary[commandId].duplicates++;
        }
      });
    
    return summary;
  }
  
  /**
   * Export logs as JSON for bug reports
   */
  exportLogs(): string {
    const exportData = {
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      logs: this.logs,
      renderSummary: this.getRenderSummary(),
      commandSummary: this.getCommandRegistrationSummary()
    };
    
    return JSON.stringify(exportData, null, 2);
  }
  
  /**
   * Clear all logs
   */
  clearLogs(): void {
    this.logs = [];
    console.log('[DebugLogger] Logs cleared');
  }
  
  /**
   * Print a summary to console
   */
  printSummary(): void {
    console.group('[DebugLogger] Summary');
    console.log('Total logs:', this.logs.length);
    console.log('Render counts:', this.getRenderSummary());
    console.log('Command registration:', this.getCommandRegistrationSummary());
    console.groupEnd();
  }
  
  private addLog(entry: DebugLogEntry): void {
    this.logs.push(entry);
    
    // Keep only the last N logs
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }
  }
  
  private checkRenderFrequency(component: string): void {
    // Check if component has rendered more than 10 times in the last second
    const oneSecondAgo = Date.now() - 1000;
    const recentRenders = this.logs.filter(
      log => log.component === component && 
             (log.action === 'lifecycle:render' || log.action === 'lifecycle:update') &&
             log.timestamp >= oneSecondAgo
    );
    
    if (recentRenders.length > 10) {
      console.warn(
        `[DebugLogger] High render frequency detected: ${component} rendered ${recentRenders.length} times in the last second`
      );
    }
  }
  
  private checkCommandRegistrationFrequency(commandId: string): void {
    // Check if command has been registered more than 5 times in the last second
    const oneSecondAgo = Date.now() - 1000;
    const recentRegistrations = this.logs.filter(
      log => log.details?.commandId === commandId && 
             log.action.startsWith('command:') &&
             log.timestamp >= oneSecondAgo
    );
    
    if (recentRegistrations.length > 5) {
      console.warn(
        `[DebugLogger] High command registration frequency: ${commandId} registered ${recentRegistrations.length} times in the last second`
      );
    }
  }
}

// Singleton instance
export const debugLogger = new DebugLogger();

// Expose to window for console access
if (typeof window !== 'undefined') {
  (window as any).icuiDebugLogger = debugLogger;
  
  // Add helper functions to window
  (window as any).icuiDebugHelpers = {
    enable: () => debugLogger.setEnabled(true),
    disable: () => debugLogger.setEnabled(false),
    summary: () => debugLogger.printSummary(),
    export: () => debugLogger.exportLogs(),
    clear: () => debugLogger.clearLogs(),
    logs: (filter?: any) => debugLogger.getLogs(filter)
  };
  
  console.log('[DebugLogger] Helper functions available:');
  console.log('  - icuiDebugHelpers.enable()');
  console.log('  - icuiDebugHelpers.disable()');
  console.log('  - icuiDebugHelpers.summary()');
  console.log('  - icuiDebugHelpers.export()');
  console.log('  - icuiDebugHelpers.clear()');
  console.log('  - icuiDebugHelpers.logs(filter)');
}

export default debugLogger;
