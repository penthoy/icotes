/**
 * Chat Backend Client - Enhanced Version
 * 
 * Using the enhanced implementation with advanced WebSocket features.
 * Provides reliable chat functionality with connection management, error handling,
 * message queuing, and health monitoring.
 */

export * from './enhancedChatBackendClient';
export { ChatBackendClient } from './enhancedChatBackendClient';

// Create a default instance for compatibility
import { chatBackendClient } from './enhancedChatBackendClient';
export { chatBackendClient };
