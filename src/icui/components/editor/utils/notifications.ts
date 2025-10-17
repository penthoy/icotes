/**
 * Editor Notification Service
 * 
 * Provides toast-style notifications for editor operations
 * (file save, open, error states, etc.)
 */

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

// Unified editor notifications: delegate to global notificationService
// This avoids overlapping fixed-position toasts and ensures consistent stacking,
// hover-to-pause behavior, and selectable text.
import { notificationService } from '../../../services/notificationService';

export class EditorNotificationService {
  static show(message: string, type: NotificationType = 'info'): void {
    notificationService.show(message, type, {
      position: 'top-right',
      duration: 3000,
      dismissible: true,
      // key helps dedupe frequent editor messages
      key: `editor:${type}:${message}`,
    });
  }
}
