/**
 * Backend Service
 * 
 * Currently using the proven implementation for reliable backend functionality.
 * The enhanced version with advanced features is available as enhancedBackendService.tsx
 */

export * from './backendService_deprecated';
export { icuiBackendService } from './backendService_deprecated';

// Re-export the stable service as the default ICUIBackendService
export { ICUIBackendService } from './backendService_deprecated';
