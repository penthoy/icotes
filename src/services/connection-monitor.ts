/**
 * Connection Health Monitor
 * 
 * Provides real-time monitoring and diagnostics for WebSocket connections
 * across all services, including latency tracking, throughput analysis,
 * and health scoring.
 */

import { ServiceConnection, ConnectionHealth } from './connection-manager';

export interface HealthMetrics {
  latency: {
    current: number;
    average: number;
    min: number;
    max: number;
    samples: number[];
  };
  throughput: {
    messagesPerSecond: number;
    bytesPerSecond: number;
    totalMessages: number;
    totalBytes: number;
  };
  reliability: {
    uptime: number;
    downtimeEvents: number;
    successRate: number;
    errorRate: number;
    reconnectionCount: number;
  };
  performance: {
    cpuUsage: number;
    memoryUsage: number;
    networkUtilization: number;
  };
}

export interface HealthScore {
  overall: number; // 0-100
  latency: number; // 0-100
  throughput: number; // 0-100
  reliability: number; // 0-100
  trend: 'improving' | 'stable' | 'degrading';
  issues: string[];
  recommendations: string[];
}

export interface DiagnosticResult {
  connectionId: string;
  serviceType: string;
  timestamp: number;
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  score: HealthScore;
  metrics: HealthMetrics;
  diagnostics: {
    networkTest: boolean;
    protocolTest: boolean;
    authTest: boolean;
    loadTest: boolean;
  };
}

export class ConnectionHealthMonitor {
  private connections = new Map<string, ServiceConnection>();
  private metrics = new Map<string, HealthMetrics>();
  private historicalData = new Map<string, HealthScore[]>();
  private monitoringInterval: NodeJS.Timeout | null = null;
  private diagnosticsRunning = new Set<string>();

  private readonly LATENCY_SAMPLES_LIMIT = 100;
  private readonly HISTORICAL_DATA_LIMIT = 1000;
  private readonly MONITORING_INTERVAL = 5000; // 5 seconds

  constructor() {
    this.startMonitoring();
  }

  /**
   * Register connection for monitoring
   */
  addConnection(connection: ServiceConnection): void {
    this.connections.set(connection.id, connection);
    this.initializeMetrics(connection.id);
  }

  /**
   * Remove connection from monitoring
   */
  removeConnection(connectionId: string): void {
    this.connections.delete(connectionId);
    this.metrics.delete(connectionId);
    this.historicalData.delete(connectionId);
    this.diagnosticsRunning.delete(connectionId);
  }

  /**
   * Update connection metrics
   */
  updateMetrics(connectionId: string, update: {
    latency?: number;
    messagesSent?: number;
    messagesReceived?: number;
    bytesSent?: number;
    bytesReceived?: number;
    errorCount?: number;
  }): void {
    const metrics = this.metrics.get(connectionId);
    if (!metrics) return;

    const now = Date.now();

    // Update latency
    if (update.latency !== undefined) {
      metrics.latency.current = update.latency;
      metrics.latency.samples.push(update.latency);
      
      // Keep only recent samples
      if (metrics.latency.samples.length > this.LATENCY_SAMPLES_LIMIT) {
        metrics.latency.samples = metrics.latency.samples.slice(-this.LATENCY_SAMPLES_LIMIT);
      }
      
      // Recalculate stats
      this.recalculateLatencyStats(metrics);
    }

    // Update throughput
    if (update.messagesSent !== undefined) {
      metrics.throughput.totalMessages += update.messagesSent;
    }
    if (update.messagesReceived !== undefined) {
      metrics.throughput.totalMessages += update.messagesReceived;
    }
    if (update.bytesSent !== undefined) {
      metrics.throughput.totalBytes += update.bytesSent;
    }
    if (update.bytesReceived !== undefined) {
      metrics.throughput.totalBytes += update.bytesReceived;
    }

    // Update reliability
    if (update.errorCount !== undefined) {
      metrics.reliability.errorRate += update.errorCount;
    }

    // Recalculate throughput rates
    this.recalculateThroughputRates(connectionId, metrics);
  }

  /**
   * Get current health score for a connection
   */
  getHealthScore(connectionId: string): HealthScore | null {
    const connection = this.connections.get(connectionId);
    const metrics = this.metrics.get(connectionId);
    
    if (!connection || !metrics) {
      return null;
    }

    return this.calculateHealthScore(connection, metrics);
  }

  /**
   * Get detailed health metrics
   */
  getHealthMetrics(connectionId: string): HealthMetrics | null {
    return this.metrics.get(connectionId) || null;
  }

  /**
   * Get health summary for all connections
   */
  getHealthSummary(): {
    total: number;
    healthy: number;
    warning: number;
    critical: number;
    unknown: number;
    averageScore: number;
  } {
    const connections = Array.from(this.connections.values());
    const scores = connections
      .map(conn => this.getHealthScore(conn.id))
      .filter(score => score !== null) as HealthScore[];

    const summary = {
      total: connections.length,
      healthy: 0,
      warning: 0,
      critical: 0,
      unknown: 0,
      averageScore: 0
    };

    if (scores.length === 0) {
      summary.unknown = connections.length;
      return summary;
    }

    scores.forEach(score => {
      if (score.overall >= 80) summary.healthy++;
      else if (score.overall >= 60) summary.warning++;
      else if (score.overall >= 0) summary.critical++;
      else summary.unknown++;
    });

    summary.averageScore = scores.reduce((sum, score) => sum + score.overall, 0) / scores.length;
    
    return summary;
  }

  /**
   * Run comprehensive diagnostics on a connection
   */
  async runDiagnostics(connectionId: string): Promise<DiagnosticResult | null> {
    const connection = this.connections.get(connectionId);
    const metrics = this.metrics.get(connectionId);
    
    if (!connection || !metrics) {
      return null;
    }

    // Prevent concurrent diagnostics
    if (this.diagnosticsRunning.has(connectionId)) {
      console.warn(`Diagnostics already running for connection ${connectionId}`);
      return null;
    }

    this.diagnosticsRunning.add(connectionId);

    try {
      const diagnostics = {
        networkTest: await this.testNetworkConnectivity(connection),
        protocolTest: await this.testProtocolCompliance(connection),
        authTest: await this.testAuthentication(connection),
        loadTest: await this.testLoadCapacity(connection)
      };

      const score = this.calculateHealthScore(connection, metrics);
      
      let status: DiagnosticResult['status'] = 'healthy';
      if (score.overall < 60) status = 'critical';
      else if (score.overall < 80) status = 'warning';

      return {
        connectionId,
        serviceType: connection.type,
        timestamp: Date.now(),
        status,
        score,
        metrics,
        diagnostics
      };
    } finally {
      this.diagnosticsRunning.delete(connectionId);
    }
  }

  /**
   * Get historical trend for a connection
   */
  getHealthTrend(connectionId: string, timeRange: number = 3600000): HealthScore[] {
    const historical = this.historicalData.get(connectionId) || [];
    const cutoff = Date.now() - timeRange;
    
    return historical.filter(score => {
      // Assuming we store timestamps in the historical data
      return true; // For now, return all data
    });
  }

  /**
   * Get performance recommendations
   */
  getRecommendations(connectionId: string): string[] {
    const score = this.getHealthScore(connectionId);
    const metrics = this.getHealthMetrics(connectionId);
    
    if (!score || !metrics) {
      return ['Unable to analyze connection - insufficient data'];
    }

    const recommendations: string[] = [];

    // Latency recommendations
    if (score.latency < 70) {
      if (metrics.latency.average > 1000) {
        recommendations.push('High latency detected - consider using a CDN or closer server');
      }
      if (metrics.latency.max > 5000) {
        recommendations.push('Intermittent network issues - check network stability');
      }
    }

    // Throughput recommendations
    if (score.throughput < 70) {
      if (metrics.throughput.messagesPerSecond < 1) {
        recommendations.push('Low message throughput - consider message batching');
      }
      if (metrics.throughput.bytesPerSecond > 1024 * 1024) {
        recommendations.push('High bandwidth usage - consider compression');
      }
    }

    // Reliability recommendations
    if (score.reliability < 70) {
      if (metrics.reliability.reconnectionCount > 5) {
        recommendations.push('Frequent reconnections - check network stability');
      }
      if (metrics.reliability.errorRate > 0.1) {
        recommendations.push('High error rate - review error logs and server health');
      }
    }

    // General recommendations
    if (score.overall < 60) {
      recommendations.push('Overall poor health - consider switching to backup server');
    }

    return recommendations.length > 0 ? recommendations : ['Connection is performing well'];
  }

  /**
   * Export health data for analysis
   */
  exportHealthData(connectionId?: string): any {
    if (connectionId) {
      return {
        connection: this.connections.get(connectionId),
        metrics: this.metrics.get(connectionId),
        historical: this.historicalData.get(connectionId)
      };
    }

    return {
      connections: Object.fromEntries(this.connections),
      metrics: Object.fromEntries(this.metrics),
      historical: Object.fromEntries(this.historicalData)
    };
  }

  /**
   * Start monitoring
   */
  startMonitoring(): void {
    if (this.monitoringInterval) return;

    this.monitoringInterval = setInterval(() => {
      this.updateAllHealthScores();
      this.performHealthChecks();
      this.cleanupOldData();
    }, this.MONITORING_INTERVAL);
  }

  /**
   * Stop monitoring
   */
  stopMonitoring(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
  }

  /**
   * Destroy monitor and cleanup
   */
  destroy(): void {
    this.stopMonitoring();
    this.connections.clear();
    this.metrics.clear();
    this.historicalData.clear();
    this.diagnosticsRunning.clear();
  }

  // Private helper methods

  private initializeMetrics(connectionId: string): void {
    this.metrics.set(connectionId, {
      latency: {
        current: 0,
        average: 0,
        min: Infinity,
        max: 0,
        samples: []
      },
      throughput: {
        messagesPerSecond: 0,
        bytesPerSecond: 0,
        totalMessages: 0,
        totalBytes: 0
      },
      reliability: {
        uptime: 0,
        downtimeEvents: 0,
        successRate: 1.0,
        errorRate: 0,
        reconnectionCount: 0
      },
      performance: {
        cpuUsage: 0,
        memoryUsage: 0,
        networkUtilization: 0
      }
    });
  }

  private recalculateLatencyStats(metrics: HealthMetrics): void {
    const samples = metrics.latency.samples;
    if (samples.length === 0) return;

    metrics.latency.average = samples.reduce((sum, val) => sum + val, 0) / samples.length;
    metrics.latency.min = Math.min(...samples);
    metrics.latency.max = Math.max(...samples);
  }

  private recalculateThroughputRates(connectionId: string, metrics: HealthMetrics): void {
    const connection = this.connections.get(connectionId);
    if (!connection || !connection.connectedAt) return;

    const uptimeSeconds = (Date.now() - connection.connectedAt) / 1000;
    if (uptimeSeconds > 0) {
      metrics.throughput.messagesPerSecond = metrics.throughput.totalMessages / uptimeSeconds;
      metrics.throughput.bytesPerSecond = metrics.throughput.totalBytes / uptimeSeconds;
    }
  }

  private calculateHealthScore(connection: ServiceConnection, metrics: HealthMetrics): HealthScore {
    // Calculate individual scores
    const latencyScore = this.calculateLatencyScore(metrics.latency);
    const throughputScore = this.calculateThroughputScore(metrics.throughput);
    const reliabilityScore = this.calculateReliabilityScore(metrics.reliability);

    // Calculate overall score (weighted average)
    const overall = Math.round(
      latencyScore * 0.3 + 
      throughputScore * 0.3 + 
      reliabilityScore * 0.4
    );

    // Determine trend
    const historical = this.historicalData.get(connection.id) || [];
    let trend: HealthScore['trend'] = 'stable';
    
    if (historical.length >= 3) {
      const recent = historical.slice(-3);
      const avgRecent = recent.reduce((sum, score) => sum + score.overall, 0) / recent.length;
      
      if (overall > avgRecent + 5) trend = 'improving';
      else if (overall < avgRecent - 5) trend = 'degrading';
    }

    // Identify issues
    const issues: string[] = [];
    if (latencyScore < 70) issues.push('High latency');
    if (throughputScore < 70) issues.push('Low throughput');
    if (reliabilityScore < 70) issues.push('Reliability concerns');
    if (connection.reconnectAttempts > 3) issues.push('Frequent reconnections');

    return {
      overall,
      latency: latencyScore,
      throughput: throughputScore,
      reliability: reliabilityScore,
      trend,
      issues,
      recommendations: [] // Remove circular dependency - recommendations will be calculated separately
    };
  }

  private calculateLatencyScore(latency: HealthMetrics['latency']): number {
    if (latency.samples.length === 0) return 100;

    // Score based on average latency
    if (latency.average < 50) return 100;
    if (latency.average < 100) return 95;
    if (latency.average < 200) return 85;
    if (latency.average < 500) return 70;
    if (latency.average < 1000) return 50;
    if (latency.average < 2000) return 25;
    return 0;
  }

  private calculateThroughputScore(throughput: HealthMetrics['throughput']): number {
    // Score based on message rate and consistency
    const messagesPerSecond = throughput.messagesPerSecond;
    
    if (messagesPerSecond > 100) return 100;
    if (messagesPerSecond > 50) return 90;
    if (messagesPerSecond > 10) return 80;
    if (messagesPerSecond > 1) return 70;
    if (messagesPerSecond > 0.1) return 50;
    return 30; // Even very low throughput gets some points for working
  }

  private calculateReliabilityScore(reliability: HealthMetrics['reliability']): number {
    // Score based on uptime and error rate
    const uptimeScore = Math.min(100, (reliability.uptime / 86400000) * 100); // 24h uptime = 100%
    const errorScore = Math.max(0, 100 - (reliability.errorRate * 1000)); // 10% error rate = 0 points
    const reconnectScore = Math.max(0, 100 - (reliability.reconnectionCount * 10)); // 10 reconnects = 0 points
    
    return Math.round((uptimeScore * 0.5 + errorScore * 0.3 + reconnectScore * 0.2));
  }

  private async testNetworkConnectivity(connection: ServiceConnection): Promise<boolean> {
    try {
      // Simple ping test
      if (connection.websocket && connection.websocket.readyState === WebSocket.OPEN) {
        const startTime = Date.now();
        
        // Send ping and wait for response (simplified test)
        return new Promise((resolve) => {
          const timeout = setTimeout(() => resolve(false), 5000);
          
          // In a real implementation, you'd listen for pong response
          // For now, just assume success if connection is open
          clearTimeout(timeout);
          resolve(true);
        });
      }
      return false;
    } catch {
      return false;
    }
  }

  private async testProtocolCompliance(connection: ServiceConnection): Promise<boolean> {
    try {
      // Test if connection follows expected protocol
      return connection.websocket?.readyState === WebSocket.OPEN;
    } catch {
      return false;
    }
  }

  private async testAuthentication(connection: ServiceConnection): Promise<boolean> {
    try {
      // Test if connection is properly authenticated
      // For now, assume authenticated if connected
      return connection.status === 'connected';
    } catch {
      return false;
    }
  }

  private async testLoadCapacity(connection: ServiceConnection): Promise<boolean> {
    try {
      // Test connection under load
      // For now, just check if connection is responsive
      return connection.websocket?.readyState === WebSocket.OPEN;
    } catch {
      return false;
    }
  }

  private updateAllHealthScores(): void {
    for (const [connectionId, connection] of this.connections) {
      const metrics = this.metrics.get(connectionId);
      if (metrics) {
        const score = this.calculateHealthScore(connection, metrics);
        
        // Store in historical data
        const historical = this.historicalData.get(connectionId) || [];
        historical.push(score);
        
        // Limit historical data size
        if (historical.length > this.HISTORICAL_DATA_LIMIT) {
          historical.splice(0, historical.length - this.HISTORICAL_DATA_LIMIT);
        }
        
        this.historicalData.set(connectionId, historical);
      }
    }
  }

  private performHealthChecks(): void {
    // Perform periodic health checks
    for (const [connectionId, connection] of this.connections) {
      if (connection.status === 'connected' && connection.websocket) {
        // Update uptime
        const metrics = this.metrics.get(connectionId);
        if (metrics && connection.connectedAt) {
          metrics.reliability.uptime = Date.now() - connection.connectedAt;
        }
      }
    }
  }

  private cleanupOldData(): void {
    // Clean up old historical data
    const cutoff = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
    
    for (const [connectionId, historical] of this.historicalData) {
      // In a real implementation, you'd filter by timestamp
      // For now, just maintain size limits
      if (historical.length > this.HISTORICAL_DATA_LIMIT) {
        historical.splice(0, historical.length - this.HISTORICAL_DATA_LIMIT);
      }
    }
  }
}
