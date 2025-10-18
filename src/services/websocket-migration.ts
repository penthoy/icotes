/**
 * WebSocket Migration Helper
 * 
 * Provides a gradual migration path from existing WebSocket implementations
 * to the enhanced WebSocket service with backward compatibility.
 */

import { WebSocketService } from './websocket-service-impl';
import { ServiceType } from './connection-manager';
import { ChatBackendClient } from '../icui/services/chatBackendClient';

export interface MigrationConfig {
  enableWebSocketService: boolean;
  migrateChat: boolean;
  migrateTerminal: boolean;
  migrateMain: boolean;
  fallbackToLegacy: boolean;
  testMode: boolean;
}

export class WebSocketMigrationHelper {
  private wsService: WebSocketService | null = null;
  private legacyServices = new Map<string, any>();
  private config: MigrationConfig;

  private readonly DEFAULT_MIGRATION_CONFIG: MigrationConfig = {
    enableWebSocketService: true,
    migrateChat: true,
    migrateTerminal: false, // Start with false to test chat first
    migrateMain: false,
    fallbackToLegacy: true,
    testMode: true
  };

  constructor(config?: Partial<MigrationConfig>) {
    this.config = { ...this.DEFAULT_MIGRATION_CONFIG, ...config };
    
    if (this.config.enableWebSocketService) {
      this.initializeWebSocketService();
    }
  }

  /**
   * Get service for a specific type (enhanced or legacy)
   */
  getService(serviceType: ServiceType): any {
    const shouldUseWebSocket = this.shouldUseWebSocketService(serviceType);
    
    if (shouldUseWebSocket && this.wsService) {
      return new WebSocketServiceAdapter(this.wsService, serviceType);
    }
    
    return this.getLegacyService(serviceType);
  }

  /**
   * Test enhanced service with a connection
   */
  async testEnhancedService(serviceType: ServiceType): Promise<boolean> {
    if (!this.wsService) {
      return false;
    }

    try {
      console.log(`Testing enhanced service for ${serviceType}...`);
      
      const connectionId = await this.wsService.connect({
        serviceType,
        timeout: 5000
      });

      // Test basic connectivity
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const status = this.wsService.getConnectionStatus(connectionId);
      const isHealthy = status?.status === 'connected';
      
      // Cleanup test connection
      await this.wsService.disconnect(connectionId);
      
      console.log(`Enhanced service test for ${serviceType}: ${isHealthy ? 'PASSED' : 'FAILED'}`);
      return isHealthy;
      
    } catch (error) {
      console.error(`Enhanced service test failed for ${serviceType}:`, error);
      return false;
    }
  }

  /**
   * Enable enhanced service for a specific type
   */
  async enableWebSocketService(serviceType: ServiceType): Promise<boolean> {
    const testPassed = await this.testEnhancedService(serviceType);
    
    if (testPassed) {
      switch (serviceType) {
        case 'chat':
          this.config.migrateChat = true;
          break;
        case 'terminal':
          this.config.migrateTerminal = true;
          break;
        case 'main':
          this.config.migrateMain = true;
          break;
      }
      
      console.log(`Enhanced service enabled for ${serviceType}`);
      return true;
    } else if (this.config.fallbackToLegacy) {
      console.warn(`Enhanced service test failed for ${serviceType}, falling back to legacy`);
      return false;
    } else {
      throw new Error(`Enhanced service test failed for ${serviceType} and fallback is disabled`);
    }
  }

  /**
   * Disable enhanced service for a specific type
   */
  disableEnhancedService(serviceType: ServiceType): void {
    switch (serviceType) {
      case 'chat':
        this.config.migrateChat = false;
        break;
      case 'terminal':
        this.config.migrateTerminal = false;
        break;
      case 'main':
        this.config.migrateMain = false;
        break;
    }
    
    console.log(`Enhanced service disabled for ${serviceType}, falling back to legacy`);
  }

  /**
   * Get migration status
   */
  getMigrationStatus(): {
    wsServiceAvailable: boolean;
    servicesUsingEnhanced: ServiceType[];
    servicesUsingLegacy: ServiceType[];
    testMode: boolean;
  } {
    const allServices: ServiceType[] = ['chat', 'terminal', 'main'];
    const servicesUsingEnhanced: ServiceType[] = [];
    const servicesUsingLegacy: ServiceType[] = [];
    
    allServices.forEach(service => {
      if (this.shouldUseWebSocketService(service)) {
        servicesUsingEnhanced.push(service);
      } else {
        servicesUsingLegacy.push(service);
      }
    });

    return {
      wsServiceAvailable: this.wsService !== null,
      servicesUsingEnhanced,
      servicesUsingLegacy,
      testMode: this.config.testMode
    };
  }

  /**
   * Get performance comparison
   */
  getPerformanceMetrics(): any {
    if (!this.wsService) {
      return { error: 'Enhanced service not available' };
    }

    return {
      enhanced: this.wsService.getHealthInfo(),
      legacy: this.getLegacyMetrics(),
      migration: this.getMigrationStatus()
    };
  }

  /**
   * Cleanup and destroy services
   */
  destroy(): void {
    if (this.wsService) {
      this.wsService.destroy();
    }
    
    for (const service of this.legacyServices.values()) {
      if (service && typeof service.destroy === 'function') {
        service.destroy();
      } else if (service && typeof service.disconnect === 'function') {
        service.disconnect();
      }
    }
    
    this.legacyServices.clear();
  }

  // Private helper methods

  private initializeWebSocketService(): void {
    try {
      // Prevent double initialization
      if (this.wsService) {
        return; // Already initialized
      }
      this.wsService = new WebSocketService({
        enableMessageQueue: true,
        enableHealthMonitoring: true,
        enableAutoRecovery: true,
        maxConcurrentConnections: 10,
        messageTimeout: 10000,
        reconnect_attempts: 5,
        reconnect_delay: 1000,
        batchConfig: {
          maxSize: 10,
          maxWaitTime: 100,
          enableCompression: false // Disable initially for stability
        }
      });

      console.log('WebSocket service initialized');
    } catch (error) {
      console.error('Failed to initialize enhanced WebSocket service:', error);
      this.wsService = null;
    }
  }

  private shouldUseWebSocketService(serviceType: ServiceType): boolean {
    if (!this.config.enableWebSocketService || !this.wsService) {
      return false;
    }

    switch (serviceType) {
      case 'chat':
        return this.config.migrateChat;
      case 'terminal':
        return this.config.migrateTerminal;
      case 'main':
        return this.config.migrateMain;
      default:
        return false;
    }
  }

  private getLegacyService(serviceType: ServiceType): any {
    if (!this.legacyServices.has(serviceType)) {
      const service = this.createLegacyService(serviceType);
      this.legacyServices.set(serviceType, service);
    }
    
    return this.legacyServices.get(serviceType);
  }

  private createLegacyService(serviceType: ServiceType): any {
    switch (serviceType) {
      case 'chat':
        return new ChatBackendClient();
      case 'terminal':
        // Return a wrapper or existing terminal service
        return { type: 'legacy-terminal' };
      case 'main':
        // Return a wrapper or existing main service
        return { type: 'legacy-main' };
      default:
        throw new Error(`Unknown service type: ${serviceType}`);
    }
  }

  private getLegacyMetrics(): any {
    const metrics: any = {};
    
    for (const [serviceType, service] of this.legacyServices) {
      if (service && typeof service.getStatistics === 'function') {
        metrics[serviceType] = service.getStatistics();
      } else {
        metrics[serviceType] = { status: 'no-metrics-available' };
      }
    }
    
    return metrics;
  }
}

/**
 * Adapter to make enhanced service compatible with existing interfaces
 */
class WebSocketServiceAdapter {
  private wsService: WebSocketService;
  private serviceType: ServiceType;
  private connectionId: string | null = null;

  constructor(wsService: WebSocketService, serviceType: ServiceType) {
    this.wsService = wsService;
    this.serviceType = serviceType;
  }

  /**
   * Connect (compatible with existing interfaces)
   */
  async connectWebSocket(options?: any): Promise<boolean> {
    try {
      this.connectionId = await this.wsService.connect({
        serviceType: this.serviceType,
        ...options
      });
      return true;
    } catch (error) {
      console.error(`Enhanced service connection failed for ${this.serviceType}:`, error);
      return false;
    }
  }

  /**
   * Send message (compatible with existing interfaces)
   */
  async sendMessage(content: string, options: any = {}): Promise<void> {
    if (!this.connectionId) {
      throw new Error('Not connected');
    }

    await this.wsService.sendMessage(
      this.connectionId,
      { type: 'message', content, ...options },
      { priority: options.priority || 'normal' }
    );
  }

  /**
   * Disconnect (compatible with existing interfaces)
   */
  async disconnect(): Promise<void> {
    if (this.connectionId) {
      await this.wsService.disconnect(this.connectionId);
      this.connectionId = null;
    }
  }

  /**
   * Event subscription (compatible with existing interfaces)
   */
  onMessage(callback: Function): void {
    this.wsService.on('message', (data) => {
      if (data.connectionId === this.connectionId) {
        callback(data.message);
      }
    });
  }

  onStatus(callback: Function): void {
    this.wsService.on('connection_opened', (data) => {
      if (data.connectionId === this.connectionId) {
        callback({ connected: true });
      }
    });

    this.wsService.on('connection_closed', (data) => {
      if (data.connectionId === this.connectionId) {
        callback({ connected: false });
      }
    });
  }

  /**
   * Get health information (enhanced feature)
   */
  getHealthInfo(): any {
    if (!this.connectionId) {
      return null;
    }
    
    return this.wsService.getHealthInfo(this.connectionId);
  }

  /**
   * Get recommendations (enhanced feature)
   */
  getRecommendations(): string[] {
    if (!this.connectionId) {
      return ['Not connected'];
    }
    
    return this.wsService.getRecommendations(this.connectionId);
  }

  /**
   * Run diagnostics (enhanced feature)
   */
  async runDiagnostics(): Promise<any> {
    if (!this.connectionId) {
      return null;
    }
    
    return await this.wsService.runDiagnostics(this.connectionId);
  }
}

// Export singleton instance for easy use
export const webSocketMigration = new WebSocketMigrationHelper({
  enableWebSocketService: true,
  migrateChat: false, // Start with false, enable after testing
  migrateTerminal: false,
  migrateMain: false,
  testMode: true
});
