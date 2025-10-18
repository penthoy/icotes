/**
 * WebSocket Service (Enhanced Version)
 * 
 * This is the new implementation that uses the enhanced WebSocket service
 * with connection management, error handling, message queuing, and health monitoring.
 */

import { WebSocketService } from './websocket-service-impl';

export * from './websocket-service-impl';
export { WebSocketService as WebSocketService } from './websocket-service-impl';

// Singleton instance for backward compatibility
let websocketServiceInstance: any = null;

export function getWebSocketService(config?: any): any {
  if (!websocketServiceInstance) {
    websocketServiceInstance = new WebSocketService(config);
  }
  return websocketServiceInstance;
}

export function resetWebSocketService(): void {
  if (websocketServiceInstance) {
    websocketServiceInstance.destroy();
    websocketServiceInstance = null;
  }
}
