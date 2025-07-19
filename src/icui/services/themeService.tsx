/**
 * Theme Detection and Management Service
 * 
 * Unified theme management service for the ICUI framework.
 * Extracted from simpleeditor.tsx and ICUIEnhancedEditorPanel.tsx patterns.
 * Provides automatic theme detection and React integration.
 */

import React, { useState, useEffect } from 'react';

export type ThemeType = 'light' | 'dark';

export interface ThemeInfo {
  type: ThemeType;
  name: string;
  cssClass: string;
}

export interface ThemeServiceConfig {
  enablePersistence?: boolean;
  storageKey?: string;
  autoDetect?: boolean;
}

class ThemeService {
  private config: Required<ThemeServiceConfig>;
  private themeCallbacks: Set<(theme: ThemeInfo) => void> = new Set();
  private observer: MutationObserver | null = null;
  private currentTheme: ThemeInfo | null = null;

  // Predefined theme mappings
  private readonly themeMap = new Map<string, ThemeInfo>([
    ['light', { type: 'light', name: 'Light', cssClass: 'light' }],
    ['dark', { type: 'dark', name: 'Dark', cssClass: 'dark' }],
    ['icui-theme-github-light', { type: 'light', name: 'GitHub Light', cssClass: 'icui-theme-github-light' }],
    ['icui-theme-github-dark', { type: 'dark', name: 'GitHub Dark', cssClass: 'icui-theme-github-dark' }],
    ['icui-theme-monokai', { type: 'dark', name: 'Monokai', cssClass: 'icui-theme-monokai' }],
    ['icui-theme-one-dark', { type: 'dark', name: 'One Dark', cssClass: 'icui-theme-one-dark' }],
    ['icui-theme-solarized-light', { type: 'light', name: 'Solarized Light', cssClass: 'icui-theme-solarized-light' }],
    ['icui-theme-solarized-dark', { type: 'dark', name: 'Solarized Dark', cssClass: 'icui-theme-solarized-dark' }]
  ]);

  constructor(config: ThemeServiceConfig = {}) {
    this.config = {
      enablePersistence: config.enablePersistence !== false, // Default to true
      storageKey: config.storageKey || 'icui-theme-preference',
      autoDetect: config.autoDetect !== false, // Default to true
      ...config
    };

    if (this.config.autoDetect) {
      this.startAutoDetection();
    }

    // Load persisted theme preference
    if (this.config.enablePersistence) {
      this.loadPersistedTheme();
    }
  }

  /**
   * Start automatic theme detection
   */
  startAutoDetection(): void {
    if (this.observer) {
      this.stopAutoDetection();
    }

    // Initial detection
    this.detectCurrentTheme();

    // Set up observer for theme changes
    this.observer = new MutationObserver(() => {
      this.detectCurrentTheme();
    });

    this.observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
  }

  /**
   * Stop automatic theme detection
   */
  stopAutoDetection(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }

  /**
   * Detect current theme from DOM
   */
  detectCurrentTheme(): void {
    const htmlElement = document.documentElement;
    const classList = Array.from(htmlElement.classList);
    
    // Check for specific ICUI themes first
    for (const className of classList) {
      const themeInfo = this.themeMap.get(className);
      if (themeInfo) {
        this.setCurrentTheme(themeInfo);
        return;
      }
    }

    // Fallback to generic dark/light detection
    const isDark = classList.includes('dark') || 
                   classList.some(cls => cls.includes('dark')) ||
                   classList.some(cls => this.themeMap.get(cls)?.type === 'dark');

    const fallbackTheme: ThemeInfo = {
      type: isDark ? 'dark' : 'light',
      name: isDark ? 'Dark' : 'Light',
      cssClass: isDark ? 'dark' : 'light'
    };

    this.setCurrentTheme(fallbackTheme);
  }

  /**
   * Get current theme
   */
  getCurrentTheme(): ThemeInfo {
    if (!this.currentTheme) {
      this.detectCurrentTheme();
    }
    return this.currentTheme || { type: 'light', name: 'Light', cssClass: 'light' };
  }

  /**
   * Set current theme
   */
  setCurrentTheme(theme: ThemeInfo): void {
    const previousTheme = this.currentTheme;
    this.currentTheme = theme;

    // Persist theme preference
    if (this.config.enablePersistence) {
      this.persistTheme(theme);
    }

    // Notify callbacks only if theme changed
    if (!previousTheme || previousTheme.cssClass !== theme.cssClass) {
      this.notifyThemeChange(theme);
    }
  }

  /**
   * Apply theme to DOM
   */
  applyTheme(theme: ThemeInfo): void {
    const htmlElement = document.documentElement;
    
    // Remove existing theme classes
    for (const [cssClass] of this.themeMap) {
      htmlElement.classList.remove(cssClass);
    }

    // Add new theme class
    htmlElement.classList.add(theme.cssClass);
    
    // Update current theme
    this.setCurrentTheme(theme);
  }

  /**
   * Switch theme by name or type
   */
  switchTheme(themeIdentifier: string | ThemeType): boolean {
    // Try to find by exact CSS class match first
    let theme = this.themeMap.get(themeIdentifier);
    
    if (!theme) {
      // Try to find by type
      theme = Array.from(this.themeMap.values()).find(t => t.type === themeIdentifier);
    }
    
    if (!theme) {
      // Try to find by name (case-insensitive)
      theme = Array.from(this.themeMap.values()).find(t => 
        t.name.toLowerCase() === themeIdentifier.toLowerCase()
      );
    }

    if (theme) {
      this.applyTheme(theme);
      return true;
    }

    return false;
  }

  /**
   * Toggle between light and dark themes
   */
  toggleTheme(): void {
    const current = this.getCurrentTheme();
    const targetType = current.type === 'light' ? 'dark' : 'light';
    
    // Find a theme of the opposite type
    const oppositeTheme = Array.from(this.themeMap.values()).find(t => t.type === targetType);
    
    if (oppositeTheme) {
      this.applyTheme(oppositeTheme);
    }
  }

  /**
   * Get all available themes
   */
  getAvailableThemes(): ThemeInfo[] {
    return Array.from(this.themeMap.values());
  }

  /**
   * Get themes by type
   */
  getThemesByType(type: ThemeType): ThemeInfo[] {
    return Array.from(this.themeMap.values()).filter(theme => theme.type === type);
  }

  /**
   * Subscribe to theme changes
   */
  subscribe(callback: (theme: ThemeInfo) => void): () => void {
    this.themeCallbacks.add(callback);
    
    // Immediately call with current theme
    callback(this.getCurrentTheme());
    
    return () => {
      this.themeCallbacks.delete(callback);
    };
  }

  /**
   * Register a custom theme
   */
  registerTheme(cssClass: string, themeInfo: Omit<ThemeInfo, 'cssClass'>): void {
    this.themeMap.set(cssClass, {
      ...themeInfo,
      cssClass
    });
  }

  /**
   * Unregister a theme
   */
  unregisterTheme(cssClass: string): boolean {
    return this.themeMap.delete(cssClass);
  }

  /**
   * Check if running in dark theme
   */
  isDarkTheme(): boolean {
    return this.getCurrentTheme().type === 'dark';
  }

  /**
   * Check if running in light theme
   */
  isLightTheme(): boolean {
    return this.getCurrentTheme().type === 'light';
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.stopAutoDetection();
    this.themeCallbacks.clear();
  }

  /**
   * Persist theme preference to localStorage
   */
  private persistTheme(theme: ThemeInfo): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        localStorage.setItem(this.config.storageKey, JSON.stringify({
          cssClass: theme.cssClass,
          name: theme.name,
          type: theme.type
        }));
      } catch (error) {
        console.warn('Failed to persist theme preference:', error);
      }
    }
  }

  /**
   * Load persisted theme preference from localStorage
   */
  private loadPersistedTheme(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      try {
        const stored = localStorage.getItem(this.config.storageKey);
        if (stored) {
          const themeData = JSON.parse(stored) as ThemeInfo;
          const theme = this.themeMap.get(themeData.cssClass);
          if (theme) {
            this.currentTheme = theme;
          }
        }
      } catch (error) {
        console.warn('Failed to load persisted theme preference:', error);
      }
    }
  }

  /**
   * Notify theme change subscribers
   */
  private notifyThemeChange(theme: ThemeInfo): void {
    this.themeCallbacks.forEach(callback => callback(theme));
  }
}

// Create singleton instance
export const themeService = new ThemeService();

/**
 * React hook for theme management
 */
export const useTheme = () => {
  const [theme, setTheme] = useState<ThemeInfo>(themeService.getCurrentTheme);

  useEffect(() => {
    const unsubscribe = themeService.subscribe(setTheme);
    return unsubscribe;
  }, []);

  return {
    theme,
    isDark: theme.type === 'dark',
    isLight: theme.type === 'light',
    switchTheme: themeService.switchTheme.bind(themeService),
    toggleTheme: themeService.toggleTheme.bind(themeService),
    applyTheme: themeService.applyTheme.bind(themeService),
    getAvailableThemes: themeService.getAvailableThemes.bind(themeService),
    getThemesByType: themeService.getThemesByType.bind(themeService)
  };
};

// Export service instance as default
export default themeService;
