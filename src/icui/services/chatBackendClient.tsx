/**
 * Chat Backend Client
 * 
 * Currently using the proven implementation for reliable chat functionality.
 * The enhanced version with advanced features is available as enhancedChatBackendClient.tsx
 */

export * from './chatBackendClient_deprecated';
export { ChatBackendClient } from './chatBackendClient_deprecated';

// Create a default instance for compatibility
import { ChatBackendClient as ChatBackendClientClass } from './chatBackendClient_deprecated';
export const chatBackendClient = new ChatBackendClientClass();
