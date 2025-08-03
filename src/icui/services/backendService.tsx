/**
 * Backend Service - Enhanced Version
 * 
 * Using the enhanced implementation with advanced WebSocket features.
 * Provides reliable backend functionality with connection management, error handling,
 * message queuing, and health monitoring.
 */

export * from './backend-service-impl';
export { icuiBackendService } from './backend-service-impl';

// Re-export the enhanced service as the default ICUIBackendService
export { ICUIBackendService } from './backend-service-impl';
