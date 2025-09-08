/**
 * ICUI Theming Foundation
 * 
 * Theming system with CSS variables, dark/light mode support, and extensible themes.
 * Uses CSS custom properties for runtime theme switching.
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { z } from 'zod';

/**
 * Theme definitions
 */
export interface Theme {
  name: string;
  displayName: string;
  type: 'light' | 'dark';
  colors: {
    // Background colors
    bg: {
      primary: string;
      secondary: string;
      tertiary: string;
      inverse: string;
      overlay: string;
    };
    // Text colors
    text: {
      primary: string;
      secondary: string;
      tertiary: string;
      inverse: string;
      link: string;
      disabled: string;
    };
    // Border colors
    border: {
      primary: string;
      secondary: string;
      focus: string;
      error: string;
      success: string;
      warning: string;
    };
    // Interactive colors
    interactive: {
      primary: string;
      primaryHover: string;
      primaryActive: string;
      secondary: string;
      secondaryHover: string;
      secondaryActive: string;
      danger: string;
      dangerHover: string;
      dangerActive: string;
    };
    // Status colors
    status: {
      error: string;
      success: string;
      warning: string;
      info: string;
    };
    // Syntax highlighting (for code)
    syntax: {
      keyword: string;
      string: string;
      number: string;
      comment: string;
      function: string;
      variable: string;
      type: string;
    };
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    xxl: string;
  };
  typography: {
    fontFamily: {
      sans: string;
      mono: string;
    };
    fontSize: {
      xs: string;
      sm: string;
      base: string;
      lg: string;
      xl: string;
      xxl: string;
    };
    fontWeight: {
      normal: string;
      medium: string;
      semibold: string;
      bold: string;
    };
    lineHeight: {
      tight: string;
      normal: string;
      relaxed: string;
    };
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  borderRadius: {
    none: string;
    sm: string;
    md: string;
    lg: string;
    full: string;
  };
  animations: {
    fast: string;
    normal: string;
    slow: string;
  };
}

/**
 * Default light theme
 */
export const lightTheme: Theme = {
  name: 'light',
  displayName: 'Light',
  type: 'light',
  colors: {
    bg: {
      primary: '#ffffff',
      secondary: '#f8f9fa',
      tertiary: '#e9ecef',
      inverse: '#212529',
      overlay: 'rgba(0, 0, 0, 0.5)',
    },
    text: {
      primary: '#212529',
      secondary: '#6c757d',
      tertiary: '#adb5bd',
      inverse: '#ffffff',
      link: '#0d6efd',
      disabled: '#adb5bd',
    },
    border: {
      primary: '#dee2e6',
      secondary: '#e9ecef',
      focus: '#0d6efd',
      error: '#dc3545',
      success: '#198754',
      warning: '#ffc107',
    },
    interactive: {
      primary: '#0d6efd',
      primaryHover: '#0b5ed7',
      primaryActive: '#0a58ca',
      secondary: '#6c757d',
      secondaryHover: '#5c636a',
      secondaryActive: '#565e64',
      danger: '#dc3545',
      dangerHover: '#c82333',
      dangerActive: '#bd2130',
    },
    status: {
      error: '#dc3545',
      success: '#198754',
      warning: '#ffc107',
      info: '#0dcaf0',
    },
    syntax: {
      keyword: '#d73a49',
      string: '#032f62',
      number: '#005cc5',
      comment: '#6a737d',
      function: '#6f42c1',
      variable: '#e36209',
      type: '#005cc5',
    },
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    xxl: '3rem',
  },
  typography: {
    fontFamily: {
      sans: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      mono: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", monospace',
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      xxl: '1.5rem',
    },
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75',
    },
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  },
  borderRadius: {
    none: '0',
    sm: '0.125rem',
    md: '0.375rem',
    lg: '0.5rem',
    full: '9999px',
  },
  animations: {
    fast: '150ms ease-in-out',
    normal: '250ms ease-in-out',
    slow: '350ms ease-in-out',
  },
};

/**
 * Default dark theme
 */
export const darkTheme: Theme = {
  ...lightTheme,
  name: 'dark',
  displayName: 'Dark',
  type: 'dark',
  colors: {
    bg: {
      primary: '#1a1a1a',
      secondary: '#2d2d2d',
      tertiary: '#404040',
      inverse: '#ffffff',
      overlay: 'rgba(0, 0, 0, 0.7)',
    },
    text: {
      primary: '#ffffff',
      secondary: '#cccccc',
      tertiary: '#999999',
      inverse: '#1a1a1a',
      link: '#66b3ff',
      disabled: '#666666',
    },
    border: {
      primary: '#404040',
      secondary: '#333333',
      focus: '#66b3ff',
      error: '#ff6b6b',
      success: '#51cf66',
      warning: '#ffd43b',
    },
    interactive: {
      primary: '#66b3ff',
      primaryHover: '#4dabf7',
      primaryActive: '#339af0',
      secondary: '#868e96',
      secondaryHover: '#adb5bd',
      secondaryActive: '#ced4da',
      danger: '#ff6b6b',
      dangerHover: '#ff5252',
      dangerActive: '#ff1744',
    },
    status: {
      error: '#ff6b6b',
      success: '#51cf66',
      warning: '#ffd43b',
      info: '#66d9ef',
    },
    syntax: {
      keyword: '#ff79c6',
      string: '#f1fa8c',
      number: '#bd93f9',
      comment: '#6272a4',
      function: '#8be9fd',
      variable: '#ffb86c',
      type: '#8be9fd',
    },
  },
};

/**
 * Theme context
 */
interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  availableThemes: Theme[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

/**
 * Theme provider component
 */
interface ThemeProviderProps {
  children: ReactNode;
  defaultTheme?: Theme;
  availableThemes?: Theme[];
  storageKey?: string;
}

export function ThemeProvider({
  children,
  defaultTheme = lightTheme,
  availableThemes = [lightTheme, darkTheme],
  storageKey = 'icui-theme',
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof window === 'undefined') return defaultTheme;
    
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const themeName = JSON.parse(stored);
        return availableThemes.find(t => t.name === themeName) || defaultTheme;
      }
    } catch {
      // Ignore localStorage errors
    }
    
    // Auto-detect system preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return availableThemes.find(t => t.type === 'dark') || defaultTheme;
    }
    
    return defaultTheme;
  });

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(storageKey, JSON.stringify(newTheme.name));
      } catch {
        // Ignore localStorage errors
      }
    }
  };

  const toggleTheme = () => {
    const oppositeType = theme.type === 'light' ? 'dark' : 'light';
    const newTheme = availableThemes.find(t => t.type === oppositeType);
    if (newTheme) {
      setTheme(newTheme);
    }
  };

  // Apply theme CSS variables
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const root = document.documentElement;
    
    // Apply colors
    Object.entries(theme.colors).forEach(([category, colors]) => {
      Object.entries(colors).forEach(([name, value]) => {
        root.style.setProperty(`--color-${category}-${name}`, value);
      });
    });

    // Apply spacing
    Object.entries(theme.spacing).forEach(([name, value]) => {
      root.style.setProperty(`--spacing-${name}`, value);
    });

    // Apply typography
    Object.entries(theme.typography).forEach(([category, values]) => {
      Object.entries(values).forEach(([name, value]) => {
        root.style.setProperty(`--font-${category}-${name}`, value);
      });
    });

    // Apply shadows
    Object.entries(theme.shadows).forEach(([name, value]) => {
      root.style.setProperty(`--shadow-${name}`, value);
    });

    // Apply border radius
    Object.entries(theme.borderRadius).forEach(([name, value]) => {
      root.style.setProperty(`--radius-${name}`, value);
    });

    // Apply animations
    Object.entries(theme.animations).forEach(([name, value]) => {
      root.style.setProperty(`--animation-${name}`, value);
    });

    // Set theme type for CSS
    root.setAttribute('data-theme', theme.type);
  }, [theme]);

  const value: ThemeContextValue = {
    theme,
    setTheme,
    toggleTheme,
    availableThemes,
  };

  return React.createElement(
    ThemeContext.Provider,
    { value },
    children
  );
}

/**
 * Hook to use theme context
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

/**
 * Hook to get CSS variable values
 */
export function useCSSVariables() {
  const { theme } = useTheme();
  
  const getCSSVar = (path: string): string => {
    return `var(--${path})`;
  };

  const getColor = (category: keyof Theme['colors'], name: string): string => {
    return getCSSVar(`color-${category}-${name}`);
  };

  const getSpacing = (size: keyof Theme['spacing']): string => {
    return getCSSVar(`spacing-${size}`);
  };

  const getFont = (category: keyof Theme['typography'], property: string): string => {
    return getCSSVar(`font-${category}-${property}`);
  };

  const getShadow = (size: keyof Theme['shadows']): string => {
    return getCSSVar(`shadow-${size}`);
  };

  const getRadius = (size: keyof Theme['borderRadius']): string => {
    return getCSSVar(`radius-${size}`);
  };

  const getAnimation = (speed: keyof Theme['animations']): string => {
    return getCSSVar(`animation-${speed}`);
  };

  return {
    getCSSVar,
    getColor,
    getSpacing,
    getFont,
    getShadow,
    getRadius,
    getAnimation,
  };
}

/**
 * Utility to create theme variants
 */
export class ThemeUtils {
  /**
   * Create a theme variant with overrides
   */
  static createVariant(baseTheme: Theme, overrides: Partial<Theme>): Theme {
    return {
      ...baseTheme,
      ...overrides,
      colors: {
        ...baseTheme.colors,
        ...overrides.colors,
      },
      spacing: {
        ...baseTheme.spacing,
        ...overrides.spacing,
      },
      typography: {
        ...baseTheme.typography,
        ...overrides.typography,
      },
      shadows: {
        ...baseTheme.shadows,
        ...overrides.shadows,
      },
      borderRadius: {
        ...baseTheme.borderRadius,
        ...overrides.borderRadius,
      },
      animations: {
        ...baseTheme.animations,
        ...overrides.animations,
      },
    };
  }

  /**
   * Generate CSS custom properties from theme
   */
  static generateCSSVariables(theme: Theme): string {
    const rules: string[] = [':root {'];
    
    // Colors
    Object.entries(theme.colors).forEach(([category, colors]) => {
      Object.entries(colors).forEach(([name, value]) => {
        rules.push(`  --color-${category}-${name}: ${value};`);
      });
    });

    // Spacing
    Object.entries(theme.spacing).forEach(([name, value]) => {
      rules.push(`  --spacing-${name}: ${value};`);
    });

    // Typography
    Object.entries(theme.typography).forEach(([category, values]) => {
      Object.entries(values).forEach(([name, value]) => {
        rules.push(`  --font-${category}-${name}: ${value};`);
      });
    });

    // Other properties
    ['shadows', 'borderRadius', 'animations'].forEach(category => {
      Object.entries(theme[category as keyof Theme] as Record<string, string>).forEach(([name, value]) => {
        const prefix = category === 'borderRadius' ? 'radius' : category.slice(0, -1);
        rules.push(`  --${prefix}-${name}: ${value};`);
      });
    });

    rules.push('}');
    return rules.join('\n');
  }

  /**
   * Validate theme structure
   */
  static validateTheme(theme: unknown): theme is Theme {
    if (!theme || typeof theme !== 'object') return false;

    // Define a strict schema to validate nested properties
    const colorGroup = z.object({
      primary: z.string(),
      secondary: z.string(),
      tertiary: z.string(),
      inverse: z.string(),
      overlay: z.string().optional(),
      focus: z.string().optional(),
      error: z.string().optional(),
      success: z.string().optional(),
      warning: z.string().optional(),
      info: z.string().optional(),
      link: z.string().optional(),
      disabled: z.string().optional(),
      danger: z.string().optional(),
      dangerHover: z.string().optional(),
      dangerActive: z.string().optional(),
      primaryHover: z.string().optional(),
      primaryActive: z.string().optional(),
      secondaryHover: z.string().optional(),
      secondaryActive: z.string().optional(),
      keyword: z.string().optional(),
      string: z.string().optional(),
      number: z.string().optional(),
      comment: z.string().optional(),
      function: z.string().optional(),
      variable: z.string().optional(),
      type: z.string().optional(),
    }).partial({ overlay: true });

    const ThemeSchema = z.object({
      name: z.string(),
      displayName: z.string(),
      type: z.union([z.literal('light'), z.literal('dark')]),
      colors: z.object({
        bg: z.object({
          primary: z.string(),
          secondary: z.string(),
          tertiary: z.string(),
          inverse: z.string(),
          overlay: z.string(),
        }),
        text: z.object({
          primary: z.string(),
          secondary: z.string(),
          tertiary: z.string(),
          inverse: z.string(),
          link: z.string(),
          disabled: z.string(),
        }),
        border: z.object({
          primary: z.string(),
          secondary: z.string(),
          focus: z.string(),
          error: z.string(),
          success: z.string(),
          warning: z.string(),
        }),
        interactive: z.object({
          primary: z.string(),
          primaryHover: z.string(),
          primaryActive: z.string(),
          secondary: z.string(),
          secondaryHover: z.string(),
          secondaryActive: z.string(),
          danger: z.string(),
          dangerHover: z.string(),
          dangerActive: z.string(),
        }),
        status: z.object({
          error: z.string(),
          success: z.string(),
          warning: z.string(),
          info: z.string(),
        }),
        syntax: z.object({
          keyword: z.string(),
          string: z.string(),
          number: z.string(),
          comment: z.string(),
          function: z.string(),
          variable: z.string(),
          type: z.string(),
        }),
      }),
      spacing: z.object({
        xs: z.string(),
        sm: z.string(),
        md: z.string(),
        lg: z.string(),
        xl: z.string(),
        xxl: z.string(),
      }),
      typography: z.object({
        fontFamily: z.object({ sans: z.string(), mono: z.string() }),
        fontSize: z.object({ xs: z.string(), sm: z.string(), base: z.string(), lg: z.string(), xl: z.string(), xxl: z.string() }),
        fontWeight: z.object({ normal: z.string(), medium: z.string(), semibold: z.string(), bold: z.string() }),
        lineHeight: z.object({ tight: z.string(), normal: z.string(), relaxed: z.string() }),
      }),
      shadows: z.object({ sm: z.string(), md: z.string(), lg: z.string(), xl: z.string() }),
      borderRadius: z.object({ none: z.string(), sm: z.string(), md: z.string(), lg: z.string(), full: z.string() }),
      animations: z.object({ fast: z.string(), normal: z.string(), slow: z.string() }),
    });

    const result = ThemeSchema.safeParse(theme);
    return result.success;
  }
}
