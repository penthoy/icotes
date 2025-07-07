/**
 * ICUI Framework - Responsive Hook
 * Provides viewport detection and responsive utilities
 */

import { useState, useEffect } from 'react';
import { ICUIViewport, ICUIBreakpoint, ICUIResponsiveConfig } from '../types/icui-layout';

const ICUI_BREAKPOINTS: Record<ICUIBreakpoint, number> = {
  xs: 0,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
};

/**
 * Custom hook for responsive design and viewport detection
 * @returns Viewport information and responsive utilities
 */
export function useICUIResponsive(): ICUIResponsiveConfig & {
  viewport: ICUIViewport;
  isBreakpoint: (breakpoint: ICUIBreakpoint) => boolean;
  isMinBreakpoint: (breakpoint: ICUIBreakpoint) => boolean;
} {
  const [viewport, setViewport] = useState<ICUIViewport>({
    width: 0,
    height: 0,
    isMobile: false,
    isTablet: false,
    isDesktop: false,
  });

  const [currentBreakpoint, setCurrentBreakpoint] = useState<ICUIBreakpoint>('xs');

  useEffect(() => {
    const updateViewport = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      // Determine device type
      const isMobile = width < ICUI_BREAKPOINTS.md;
      const isTablet = width >= ICUI_BREAKPOINTS.md && width < ICUI_BREAKPOINTS.lg;
      const isDesktop = width >= ICUI_BREAKPOINTS.lg;

      // Determine current breakpoint
      let newBreakpoint: ICUIBreakpoint = 'xs';
      Object.entries(ICUI_BREAKPOINTS)
        .reverse()
        .forEach(([bp, minWidth]) => {
          if (width >= minWidth) {
            newBreakpoint = bp as ICUIBreakpoint;
          }
        });

      // Only update if values actually changed
      setViewport(prev => {
        if (prev.width === width && prev.height === height && 
            prev.isMobile === isMobile && prev.isTablet === isTablet && 
            prev.isDesktop === isDesktop) {
          return prev; // No change, return same object reference
        }
        return {
          width,
          height,
          isMobile,
          isTablet,
          isDesktop,
        };
      });

      setCurrentBreakpoint(prev => prev === newBreakpoint ? prev : newBreakpoint);
    };

    // Debounce the resize handler
    let timeoutId: NodeJS.Timeout;
    const debouncedUpdateViewport = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(updateViewport, 100);
    };

    // Initial update
    updateViewport();

    // Add event listener with debouncing
    window.addEventListener('resize', debouncedUpdateViewport);

    // Cleanup
    return () => {
      window.removeEventListener('resize', debouncedUpdateViewport);
      clearTimeout(timeoutId);
    };
  }, []);

  const isBreakpoint = (breakpoint: ICUIBreakpoint): boolean => {
    return currentBreakpoint === breakpoint;
  };

  const isMinBreakpoint = (breakpoint: ICUIBreakpoint): boolean => {
    return viewport.width >= ICUI_BREAKPOINTS[breakpoint];
  };

  return {
    breakpoints: ICUI_BREAKPOINTS,
    currentBreakpoint,
    viewport,
    isBreakpoint,
    isMinBreakpoint,
  };
}
