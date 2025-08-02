/**
 * useTheme Hook - ICUI Framework
 * Provides automatic theme detection and management
 */

import { useState, useEffect } from 'react';

export interface ThemeState {
  isDark: boolean;
  theme: 'light' | 'dark' | 'auto';
}

/**
 * Custom hook for theme detection and management
 * Automatically detects theme changes from document classes and media queries
 */
export function useTheme(): ThemeState {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const detectTheme = () => {
      const isDarkMode = document.documentElement.classList.contains('dark') ||
                        document.body.classList.contains('dark') ||
                        window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDark(isDarkMode);
    };

    // Initial detection
    detectTheme();

    // Watch for DOM class changes
    const observer = new MutationObserver(detectTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    // Watch for media query changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleMediaChange = (e: MediaQueryListEvent) => {
      // Only update if no explicit theme classes are set
      if (!document.documentElement.classList.contains('dark') && 
          !document.body.classList.contains('dark')) {
        setIsDark(e.matches);
      }
    };

    if (mediaQuery.addListener) {
      mediaQuery.addListener(handleMediaChange);
    } else {
      mediaQuery.addEventListener('change', handleMediaChange);
    }

    return () => {
      observer.disconnect();
      if (mediaQuery.removeListener) {
        mediaQuery.removeListener(handleMediaChange);
      } else {
        mediaQuery.removeEventListener('change', handleMediaChange);
      }
    };
  }, []);

  const theme: 'light' | 'dark' | 'auto' = 
    document.documentElement.classList.contains('dark') || 
    document.body.classList.contains('dark') ? 'dark' :
    document.documentElement.classList.contains('light') ||
    document.body.classList.contains('light') ? 'light' : 'auto';

  return { isDark, theme };
}

/**
 * Get theme-aware CSS classes for common UI elements
 */
export function useThemeClasses() {
  const { isDark } = useTheme();

  return {
    // Background classes
    bg: {
      primary: isDark ? 'bg-gray-900 text-white' : 'bg-white text-gray-900',
      secondary: isDark ? 'bg-gray-800 text-white' : 'bg-gray-50 text-gray-900',
      tertiary: isDark ? 'bg-gray-700 text-white' : 'bg-gray-100 text-gray-900'
    },
    
    // Border classes
    border: {
      primary: isDark ? 'border-gray-700' : 'border-gray-300',
      secondary: isDark ? 'border-gray-600' : 'border-gray-200'
    },
    
    // Input classes
    input: isDark 
      ? 'bg-gray-300 text-black border-gray-500 placeholder-gray-600'
      : 'bg-white text-black border-gray-300 placeholder-gray-500',
    
    // Button classes
    button: {
      primary: isDark
        ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-gray-700'
        : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-400',
      secondary: isDark
        ? 'bg-gray-600 hover:bg-gray-700 text-white disabled:bg-gray-800'
        : 'bg-gray-500 hover:bg-gray-600 text-white disabled:bg-gray-400'
    },
    
    // Text classes
    text: {
      primary: isDark ? 'text-white' : 'text-gray-900',
      secondary: isDark ? 'text-gray-300' : 'text-gray-600',
      muted: isDark ? 'text-gray-500' : 'text-gray-400'
    },

    // Common combined classes
    panel: isDark
      ? 'bg-gray-900 text-white border-gray-700'
      : 'bg-white text-gray-900 border-gray-300',
    
    header: isDark
      ? 'bg-gray-800 border-gray-700'
      : 'bg-gray-50 border-gray-300'
  };
}
