/**
 * WebSocket Migration Helper
 * 
 * Provides a gradual migration path from existing WebSocket implementations
 * to the enhanced WebSocket service with backward compatibility.
 */

import { EnhancedWebSocketService } from './websocket-service-impl';
import { ServiceType } from './connection-manager';
import { ChatBackendClient } from '../icui/services/chatBackendClient';

export interface MigrationConfig {
  enableEnhancedService: boolean;
  migrateChat: boolean;
  migrateTerminal: boolean;
  migrateMain: boolean;
  fallbackToLegacy: boolean;
  testMode: boolean;
}

export class WebSocketMigrationHelper {
  private enhancedService: EnhancedWebSocketService | null = null;
  private legacyServices = new Map<string, any>();
  private config: MigrationConfig;

  private readonly DEFAULT_MIGRATION_CONFIG: MigrationConfig = {
    enableEnhancedService: true,
    migrateChat: true,
    migrateTerminal: false, // Start with false to test chat first
    migrateMain: false,
    fallbackToLegacy: true,
    testMode: true
  };

  constructor(config?: Partial<MigrationConfig>) {
    this.config = { ...this.DEFAULT_MIGRATION_CONFIG, ...config };
    
    if (this.config.enableEnhancedService) {
      this.initializeEnhancedService();
    }
  }

  /**
   * Get service for a specific type (enhanced or legacy)
   */
  getService(serviceType: ServiceType): any {
    const shouldUseEnhanced = this.shouldUseEnhancedService(serviceType);
    
    if (shouldUseEnhanced && this.enhancedService) {
      return new EnhancedServiceAdapter(this.enhancedService, serviceType);
    }
    
    return this.getLegacyService(serviceType);
  }

  /**
   * Test enhanced service with a connection
   */
  async testEnhancedService(serviceType: ServiceType): Promise<boolean> {
    if (!this.enhancedService) {
      return false;
    }

    try {
      console.log(`Testing enhanced service for ${serviceType}...`);
      
      const connectionId = await this.enhancedService.connect({
        serviceType,
        timeout: 5000
      });

      // Test basic connectivity
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const status = this.enhancedService.getConnectionStatus(connectionId);
      const isHealthy = status?.status === 'connected';
      
      // Cleanup test connection
      await this.enhancedService.disconnect(connectionId);
      
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
  async enableEnhancedService(serviceType: ServiceType): Promise<boolean> {
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
    enhancedServiceAvailable: boolean;
    servicesUsingEnhanced: ServiceType[];
    servicesUsingLegacy: ServiceType[];
    testMode: boolean;
  } {
    const allServices: ServiceType[] = ['chat', 'terminal', 'main'];
    const servicesUsingEnhanced: ServiceType[] = [];
    const servicesUsingLegacy: ServiceType[] = [];
    
    allServices.forEach(service => {
      if (this.shouldUseEnhancedService(service)) {
        servicesUsingEnhanced.push(service);
      } else {
        servicesUsingLegacy.push(service);
      }
    });

    return {
      enhancedServiceAvailable: this.enhancedService !== null,
      servicesUsingEnhanced,
      servicesUsingLegacy,
      testMode: this.config.testMode
    };
  }

  /**
   * Get performance comparison
   */
  getPerformanceMetrics(): any {
    if (!this.enhancedService) {
      return { error: 'Enhanced service not available' };
    }

    return {
      enhanced: this.enhancedService.getHealthInfo(),
      legacy: this.getLegacyMetrics(),
      migration: this.getMigrationStatus()
    };
  }

  /**
   * Cleanup and destroy services
   */
  destroy(): void {
    if (this.enhancedService) {
      this.enhancedService.destroy();
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

  private initializeEnhancedService(): void {
    try {
      // Prevent double initialization
      if (this.enhancedService) {
        return; // Already initialized
      }
      this.enhancedService = new EnhancedWebSocketService({
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
      this.enhancedService = null;
    }
  }

  private shouldUseEnhancedService(serviceType: ServiceType): boolean {
    if (!this.config.enableEnhancedService || !this.enhancedService) {
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
class EnhancedServiceAdapter {
  private enhancedService: EnhancedWebSocketService;
  private serviceType: ServiceType;
  private connectionId: string | null = null;

  constructor(enhancedService: EnhancedWebSocketService, serviceType: ServiceType) {
    this.enhancedService = enhancedService;
    this.serviceType = serviceType;
  }

  /**
   * Connect (compatible with existing interfaces)
   */
  async connectWebSocket(options?: any): Promise<boolean> {
    try {
      this.connectionId = await this.enhancedService.connect({
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

    await this.enhancedService.sendMessage(
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
      await this.enhancedService.disconnect(this.connectionId);
      this.connectionId = null;
    }
  }

  /**
   * Event subscription (compatible with existing interfaces)
   */
  onMessage(callback: Function): void {
    this.enhancedService.on('message', (data) => {
      if (data.connectionId === this.connectionId) {
        callback(data.message);
      }
    });
  }

  onStatus(callback: Function): void {
    this.enhancedService.on('connection_opened', (data) => {
      if (data.connectionId === this.connectionId) {
        callback({ connected: true });
      }
    });

    this.enhancedService.on('connection_closed', (data) => {
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
    
    return this.enhancedService.getHealthInfo(this.connectionId);
  }

  /**
   * Get recommendations (enhanced feature)
   */
  getRecommendations(): string[] {
    if (!this.connectionId) {
      return ['Not connected'];
    }
    
    return this.enhancedService.getRecommendations(this.connectionId);
  }

  /**
   * Run diagnostics (enhanced feature)
   */
  async runDiagnostics(): Promise<any> {
    if (!this.connectionId) {
      return null;
    }
    
    return await this.enhancedService.runDiagnostics(this.connectionId);
  }
}

// Export singleton instance for easy use
export const webSocketMigration = new WebSocketMigrationHelper({
  enableEnhancedService: true,
  migrateChat: false, // Start with false, enable after testing
  migrateTerminal: false,
  migrateMain: false,
  testMode: true
});
