/**
 * WebSocket Service (Enhanced Version)
 * 
 * This is the new implementation that uses the enhanced WebSocket service
 * with connection management, error handling, message queuing, and health monitoring.
 * The deprecated version is available in src/components/archived/services/websocket-service_deprecated.ts
 */

import { EnhancedWebSocketService } from './enhanced-websocket-service';

export * from './enhanced-websocket-service';
export { EnhancedWebSocketService as WebSocketService } from './enhanced-websocket-service';

// Singleton instance for backward compatibility
let websocketServiceInstance: any = null;

export function getWebSocketService(config?: any): any {
  if (!websocketServiceInstance) {
    websocketServiceInstance = new EnhancedWebSocketService(config);
  }
  return websocketServiceInstance;
}

export function resetWebSocketService(): void {
  if (websocketServiceInstance) {
    websocketServiceInstance.destroy();
    websocketServiceInstance = null;
  }
}
