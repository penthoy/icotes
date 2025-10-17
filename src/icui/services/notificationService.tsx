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
  key?: string; // Optional idempotency key: replaces any existing toast with the same key
  replace?: boolean; // When true (default), replace existing toast with the same key
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
  private hoverTimeouts: Map<string, NodeJS.Timeout> = new Map(); // Track auto-dismiss timeouts
  private notificationElements: Map<string, HTMLElement> = new Map(); // Track DOM elements
  private keyIndex: Map<string, string> = new Map(); // key -> notification id
  private recentMessages: Map<string, number> = new Map(); // message -> last timestamp

  private defaultOptions: Required<NotificationOptions> = {
    duration: 3000,
    position: 'top-right',
    dismissible: true,
    key: undefined,
    replace: true,
  } as Required<NotificationOptions>;

  /**
   * Show a notification with specified message, type, and options
   */
  show(
    message: string, 
    type: NotificationType = 'info', 
    options: NotificationOptions = {}
  ): string {
    const id = `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const mergedOptions = { ...this.defaultOptions, ...options } as Required<NotificationOptions>;

    // Debounce exact same message within 1s to avoid rapid duplicates
    const now = Date.now();
    const last = this.recentMessages.get(`${type}:${message}`) || 0;
    if (now - last < 1000) {
      this.recentMessages.set(`${type}:${message}`, now);
      return id; // ignore duplicate burst
    }
    this.recentMessages.set(`${type}:${message}`, now);

    // If key present and replacement enabled, dismiss existing toast with same key
    if (mergedOptions.key && mergedOptions.replace) {
      const existingId = this.keyIndex.get(mergedOptions.key);
      if (existingId) {
        this.dismiss(existingId);
      }
    }

    const notification: Notification = {
      id,
      message,
      type,
      timestamp: Date.now(),
      options: mergedOptions
    };

    // Add notification to active list
    this.notifications.set(id, notification);
    if (mergedOptions.key) {
      this.keyIndex.set(mergedOptions.key, id);
    }

    // Create and show DOM element for immediate feedback
    this.createNotificationElement(notification);

    // Notify React components
    this.notifyComponents();

    // Auto-dismiss if duration > 0
    if (mergedOptions.duration > 0) {
      this.scheduleAutoDismiss(id, mergedOptions.duration);
    }

    return id;
  }

  /**
   * Schedule auto-dismiss for a notification
   */
  private scheduleAutoDismiss(id: string, duration: number): void {
    // Clear any existing timeout
    const existingTimeout = this.hoverTimeouts.get(id);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    // Schedule new timeout
    const timeout = setTimeout(() => {
      this.dismiss(id);
      this.hoverTimeouts.delete(id);
    }, duration);

    this.hoverTimeouts.set(id, timeout);
  }

  /**
   * Cancel auto-dismiss for a notification (on hover)
   */
  private cancelAutoDismiss(id: string): void {
    const timeout = this.hoverTimeouts.get(id);
    if (timeout) {
      clearTimeout(timeout);
      this.hoverTimeouts.delete(id);
    }
  }

  /**
   * Resume auto-dismiss for a notification (on hover out)
   */
  private resumeAutoDismiss(id: string): void {
    const notification = this.notifications.get(id);
    if (notification && notification.options.duration > 0) {
      // Use remaining time or default duration
      this.scheduleAutoDismiss(id, notification.options.duration);
    }
  }

  /**
   * Dismiss a specific notification by ID
   */
  dismiss(id: string): boolean {
    const notification = this.notifications.get(id);
    if (!notification) return false;

    // Clear any pending timeout
    this.cancelAutoDismiss(id);

    this.notifications.delete(id);
    this.removeNotificationElement(id);
    this.notifyComponents();

    // Reposition remaining notifications
    this.repositionNotifications();

    // Cleanup key index when applicable
    const k = notification.options.key;
    if (k && this.keyIndex.get(k) === id) {
      this.keyIndex.delete(k);
    }

    return true;
  }

  /**
   * Clear all notifications
   */
  clear(): void {
    // Clear all timeouts
    this.hoverTimeouts.forEach(timeout => clearTimeout(timeout));
    this.hoverTimeouts.clear();
    this.keyIndex.clear();
    this.recentMessages.clear();
    
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

    element.className = `
      fixed px-4 py-3 rounded-lg shadow-lg z-50 transition-all duration-300
      border-l-4 max-w-sm min-w-[250px]
      ${typeClasses[notification.type]}
    `.trim();

    // Set initial position (will be adjusted after DOM insertion)
    this.applyPosition(element, notification.options.position, 0);

    // Create content
    const content = document.createElement('div');
    content.className = 'flex items-start justify-between gap-3';

    const message = document.createElement('div');
    message.className = 'flex-1 text-sm font-medium select-text cursor-text'; // Enable text selection
    message.textContent = notification.message;
    // Make text selectable
    message.style.userSelect = 'text';
    message.style.webkitUserSelect = 'text';

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

    // Add hover detection to pause auto-dismiss
    element.addEventListener('mouseenter', () => {
      this.cancelAutoDismiss(notification.id);
    });

    element.addEventListener('mouseleave', () => {
      this.resumeAutoDismiss(notification.id);
    });

    // Set initial styles for animation
    element.style.opacity = '0';

    // Add to DOM first so element gets its dimensions
    document.body.appendChild(element);

    // Store element reference after it's in the DOM
    this.notificationElements.set(notification.id, element);

    // Wait for layout to complete, then calculate proper offset and position
    requestAnimationFrame(() => {
      const offset = this.calculateNotificationOffset(notification);
      this.applyPosition(element, notification.options.position, offset);
      
      // Animate in on next frame
      requestAnimationFrame(() => {
        element.style.opacity = '1';
      });
    });
  }

  /**
   * Calculate vertical offset for notification based on existing notifications at same position
   */
  private calculateNotificationOffset(notification: Notification): number {
    const position = notification.options.position;
    let offset = 0;

    // Find all existing notifications at the same position
    this.notifications.forEach((existingNotification, existingId) => {
      if (existingNotification.id !== notification.id && 
          existingNotification.options.position === position) {
        const element = this.notificationElements.get(existingId);
        if (element) {
          // Add height + gap (12px = 0.75rem)
          offset += element.offsetHeight + 12;
        }
      }
    });

    return offset;
  }

  /**
   * Apply position to notification element with offset
   */
  private applyPosition(element: HTMLElement, position: string, offset: number): void {
    const isBottom = position.includes('bottom');
    const isRight = position.includes('right');

    // Ensure smooth transitions
    element.style.transition = 'all 0.3s ease-out';

    // Set horizontal position
    if (isRight) {
      element.style.right = '1rem';
      element.style.left = 'auto';
    } else {
      element.style.left = '1rem';
      element.style.right = 'auto';
    }

    // Set vertical position with offset
    if (isBottom) {
      element.style.bottom = `${1 + offset / 16}rem`; // Convert px to rem
      element.style.top = 'auto';
    } else {
      element.style.top = `${1 + offset / 16}rem`;
      element.style.bottom = 'auto';
    }
  }

  /**
   * Reposition all notifications after one is dismissed
   */
  private repositionNotifications(): void {
    // Group notifications by position
    const positionGroups = new Map<string, Notification[]>();
    
    this.notifications.forEach(notification => {
      const position = notification.options.position;
      if (!positionGroups.has(position)) {
        positionGroups.set(position, []);
      }
      positionGroups.get(position)!.push(notification);
    });

    // Reposition each group
    positionGroups.forEach((notifications, position) => {
      let cumulativeOffset = 0;
      
      // Sort by timestamp (oldest first for proper stacking)
      notifications.sort((a, b) => a.timestamp - b.timestamp);

      notifications.forEach(notification => {
        const element = this.notificationElements.get(notification.id);
        if (element) {
          this.applyPosition(element, position, cumulativeOffset);
          cumulativeOffset += element.offsetHeight + 12;
        }
      });
    });
  }

  private removeNotificationElement(id: string): void {
    const element = this.notificationElements.get(id);
    if (element) {
      element.style.opacity = '0';
      element.style.transform = 'translateY(-20px)';
      
      setTimeout(() => {
        if (element.parentNode) {
          element.parentNode.removeChild(element);
        }
        // Clean up reference
        this.notificationElements.delete(id);
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
