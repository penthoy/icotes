/**
 * Chat Backend Client - Enhanced Version
 * 
 * Using the enhanced implementation with advanced WebSocket features.
 * Provides reliable chat functionality with connection management, error handling,
 * message queuing, and health monitoring.
 */

export * from './chat-backend-client-impl';
export { ChatBackendClient } from './chat-backend-client-impl';

// Create a default instance for compatibility
import { chatBackendClient } from './chat-backend-client-impl';
export { chatBackendClient };
