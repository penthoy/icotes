/**
 * ICUI Services - Centralized export for all services
 * 
 * This file provides a central import point for all ICUI services,
 * making it easy to import and use services throughout the application.
 */

// Core Services
export { 
  notificationService,
  type NotificationOptions,
  type Notification,
  type NotificationType,
  useNotifications
} from './notificationService';

export { 
  BackendClient, 
  FileClient, 
  TerminalClient, 
  ExecutionClient,
  type ServiceCapabilities,
  type BackendConfig,
  type ConnectionStatus
} from './backendClient';

export { 
  ICUIBackendService as BackendService,
  icuiBackendService as backendService,
  type ICUIFile,
  type ICUIFileNode
} from './backendService';

export { 
  FileService, 
  fileService,
  type FileServiceConfig,
  type FileInfo
} from './fileService';

export { 
  themeService,
  type ThemeServiceConfig,
  type ThemeInfo,
  type ThemeType,
  useTheme
} from './themeService';

// Legacy Services (maintain compatibility)
export { 
  ClipboardService, 
  clipboardService,
  type ClipboardResult,
  type ClipboardCapabilities,
  type ClipboardNotification
} from './ClipboardService';

// Service Instances (ready to use)
import { notificationService } from './notificationService';
import { FileClient, TerminalClient, ExecutionClient } from './backendClient';
import { fileService } from './fileService';
import { themeService } from './themeService';
import { clipboardService } from './ClipboardService';

export const services = {
  notification: notificationService,
  file: fileService,
  theme: themeService,
  clipboard: clipboardService,
  FileClient,
  TerminalClient,
  ExecutionClient
} as const;

// Cleanup helper
export function cleanupServices(): void {
  try {
    services.theme.destroy();
    services.file.destroy();
    console.log('ICUI Services cleaned up successfully');
  } catch (error) {
    console.error('Error cleaning up ICUI Services:', error);
  }
}

export default services;
