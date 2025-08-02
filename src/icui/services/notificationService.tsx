/**
 * Notification Service
 * 
 * Unified notification system for the ICUI framework.
 * Provides type-safe notification methods with toast-style UI feedback.
 * Integrates with ICUI theming system using CSS variables.
 */

import React from 'react';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface NotificationOptions {
  duration?: number; // Duration in milliseconds, defaults to 3000
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  dismissible?: boolean; // Whether user can click to dismiss
}

export interface Notification {
  id: string;
  message: string;
  type: NotificationType;
  timestamp: number;
  options: Required<NotificationOptions>;
}

class NotificationService {
  private notifications: Map<string, Notification> = new Map();
  private notificationCallbacks: Set<(notifications: Notification[]) => void> = new Set();

  private defaultOptions: Required<NotificationOptions> = {
    duration: 3000,
    position: 'top-right',
    dismissible: true
  };

  /**
   * Show a notification with specified message, type, and options
   */
  show(
    message: string, 
    type: NotificationType = 'info', 
    options: NotificationOptions = {}
  ): string {
    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const mergedOptions = { ...this.defaultOptions, ...options };

    const notification: Notification = {
      id,
      message,
      type,
      timestamp: Date.now(),
      options: mergedOptions
    };

    // Add notification to active list
    this.notifications.set(id, notification);

    // Create and show DOM element for immediate feedback
    this.createNotificationElement(notification);

    // Notify React components
    this.notifyComponents();

    // Auto-dismiss if duration > 0
    if (mergedOptions.duration > 0) {
      setTimeout(() => {
        this.dismiss(id);
      }, mergedOptions.duration);
    }

    return id;
  }

  /**
   * Dismiss a specific notification by ID
   */
  dismiss(id: string): boolean {
    const notification = this.notifications.get(id);
    if (!notification) return false;

    this.notifications.delete(id);
    this.removeNotificationElement(id);
    this.notifyComponents();

    return true;
  }

  /**
   * Clear all notifications
   */
  clear(): void {
    const notificationIds = Array.from(this.notifications.keys());
    notificationIds.forEach(id => this.dismiss(id));
  }

  /**
   * Get all active notifications
   */
  getAll(): Notification[] {
    return Array.from(this.notifications.values())
      .sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Subscribe to notification updates (for React components)
   */
  subscribe(callback: (notifications: Notification[]) => void): () => void {
    this.notificationCallbacks.add(callback);
    // Immediately call with current notifications
    callback(this.getAll());
    
    // Return unsubscribe function
    return () => {
      this.notificationCallbacks.delete(callback);
    };
  }

  /**
   * Convenience methods for specific notification types
   */
  success(message: string, options?: NotificationOptions): string {
    return this.show(message, 'success', options);
  }

  error(message: string, options?: NotificationOptions): string {
    return this.show(message, 'error', options);
  }

  warning(message: string, options?: NotificationOptions): string {
    return this.show(message, 'warning', options);
  }

  info(message: string, options?: NotificationOptions): string {
    return this.show(message, 'info', options);
  }

  private notifyComponents(): void {
    const notifications = this.getAll();
    this.notificationCallbacks.forEach(callback => callback(notifications));
  }

  private createNotificationElement(notification: Notification): void {
    const element = document.createElement('div');
    element.id = `icui-notification-${notification.id}`;
    
    // Use ICUI CSS variables for theming
    const typeClasses = {
      success: 'bg-green-500 text-white border-green-600',
      error: 'bg-red-500 text-white border-red-600', 
      warning: 'bg-yellow-500 text-black border-yellow-600',
      info: 'bg-blue-500 text-white border-blue-600'
    };

    const positionClasses = {
      'top-right': 'top-4 right-4',
      'top-left': 'top-4 left-4',
      'bottom-right': 'bottom-4 right-4',
      'bottom-left': 'bottom-4 left-4'
    };

    element.className = `
      fixed px-4 py-3 rounded-lg shadow-lg z-50 transition-all duration-300
      border-l-4 max-w-sm min-w-[250px]
      ${typeClasses[notification.type]}
      ${positionClasses[notification.options.position]}
    `.trim();

    // Create content
    const content = document.createElement('div');
    content.className = 'flex items-start justify-between gap-3';

    const message = document.createElement('div');
    message.className = 'flex-1 text-sm font-medium';
    message.textContent = notification.message;

    content.appendChild(message);

    // Add dismiss button if dismissible
    if (notification.options.dismissible) {
      const dismissButton = document.createElement('button');
      dismissButton.className = 'flex-shrink-0 text-sm opacity-70 hover:opacity-100 font-bold';
      dismissButton.textContent = '×';
      dismissButton.onclick = () => this.dismiss(notification.id);
      content.appendChild(dismissButton);
    }

    element.appendChild(content);

    // Add to DOM
    document.body.appendChild(element);

    // Animate in
    requestAnimationFrame(() => {
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
    });

    // Set initial styles for animation
    element.style.opacity = '0';
    element.style.transform = 'translateY(-20px)';
  }

  private removeNotificationElement(id: string): void {
    const element = document.getElementById(`icui-notification-${id}`);
    if (element) {
      element.style.opacity = '0';
      element.style.transform = 'translateY(-20px)';
      
      setTimeout(() => {
        if (element.parentNode) {
          element.parentNode.removeChild(element);
        }
      }, 300);
    }
  }
}

// Create singleton instance
export const notificationService = new NotificationService();

/**
 * React hook for using notifications
 */
export const useNotifications = () => {
  const [notifications, setNotifications] = React.useState<Notification[]>([]);

  React.useEffect(() => {
    const unsubscribe = notificationService.subscribe(setNotifications);
    return unsubscribe;
  }, []);

  return {
    notifications,
    show: notificationService.show.bind(notificationService),
    dismiss: notificationService.dismiss.bind(notificationService),
    clear: notificationService.clear.bind(notificationService),
    success: notificationService.success.bind(notificationService),
    error: notificationService.error.bind(notificationService),
    warning: notificationService.warning.bind(notificationService),
    info: notificationService.info.bind(notificationService)
  };
};

// Export service instance as default
export default notificationService;
