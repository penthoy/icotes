/**
 * Dynamic Configuration Service
 * 
 * Fetches configuration from the backend to enable deployment-agnostic URLs.
 * This allows the same Docker image to work on localhost, LAN IPs, and remote servers.
 */

import React from 'react';

export interface FrontendConfig {
  base_url: string;
  api_url: string;
  ws_url: string;
  version: string;
  auth_mode: 'standalone' | 'saas';
  features: {
    terminal: boolean;
    icpy: boolean;
    clipboard: boolean;
  };
}

class ConfigService {
  private config: FrontendConfig | null = null;
  private loading: Promise<FrontendConfig> | null = null;

  private normalizeWsUrl(wsUrl: string): string {
    try {
      const url = new URL(wsUrl);
      if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
        url.protocol = 'wss:';
      }
      return `${url.protocol}//${url.host}${url.pathname}${url.search}`;
    } catch {
      return wsUrl;
    }
  }

  async getConfig(): Promise<FrontendConfig> {
    // Return cached config if available
    if (this.config) {
      return this.config;
    }

    // Return existing loading promise if already loading
    if (this.loading) {
      return this.loading;
    }

    // Start loading config
    this.loading = this.fetchConfig();
    
    try {
      this.config = await this.loading;
      return this.config;
    } finally {
      this.loading = null;
    }
  }

  private async fetchConfig(): Promise<FrontendConfig> {
    try {
      // Try to fetch from the dynamic config endpoint with a short timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout

      const response = await fetch('/api/config', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        // Don't cache this request
        cache: 'no-cache',
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Config fetch failed: ${response.status}`);
      }

      const config = await response.json();
      if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
        console.log('✅ Dynamic configuration loaded:', config);
      }
      // Normalize ws protocol based on current page
      config.ws_url = this.normalizeWsUrl(config.ws_url);
      return config;
    } catch (error) {
      if (error.name === 'AbortError') {
        console.warn('⚠️  Dynamic config request timed out, using fallback');
      } else {
        console.warn('⚠️  Failed to fetch dynamic config, using fallback:', error);
      }
      
      // Fallback to environment variables or dynamic detection
      return this.getFallbackConfig();
    }
  }

  private getFallbackConfig(): FrontendConfig {
    // Check for build-time environment variables first
    const envApiUrl = import.meta.env.VITE_API_URL;
    const envWsUrl = import.meta.env.VITE_WS_URL;
    const envBackendUrl = import.meta.env.VITE_BACKEND_URL;

    let base_url: string;
    let api_url: string;
    let ws_url: string;

    console.log('🔧 Environment variables available:', {
      VITE_API_URL: envApiUrl,
      VITE_WS_URL: envWsUrl,
      VITE_BACKEND_URL: envBackendUrl
    });

    // In development, prioritize environment variables
    if (envApiUrl && envWsUrl && envApiUrl !== '' && envWsUrl !== '') {
      try {
        const apiUrlObj = new URL(envApiUrl);
        base_url = envBackendUrl || `${apiUrlObj.protocol}//${apiUrlObj.host}`;
        api_url = envApiUrl;
        
        // SAAS PROTOCOL FIX: Ensure WebSocket uses correct protocol
        ws_url = this.normalizeWsUrl(envWsUrl);
        if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
          console.log('✅ Using environment variables for development:', { base_url, api_url, ws_url });
        }
      } catch (error) {
        console.warn('⚠️  Invalid environment variable URLs, falling back to dynamic detection:', error);
        // Fall through to dynamic detection
        ({ base_url, api_url, ws_url } = this.getDynamicUrls());
      }
    } else {
      console.log('🔄 No valid environment variables found, using dynamic detection');
      // Dynamic detection based on current window location
      ({ base_url, api_url, ws_url } = this.getDynamicUrls());
    }

    console.log('🔄 Using fallback configuration:', { base_url, api_url, ws_url });

    return {
      base_url,
      api_url,
      ws_url,
      version: '1.0.0',
      auth_mode: 'standalone', // Default to standalone
      features: {
        terminal: true,
        icpy: true,
        clipboard: true
      }
    };
  }

  private getDynamicUrls() {
    if (typeof window === 'undefined') {
      // SSR fallback
      return {
        base_url: 'http://localhost:8000',
        api_url: 'http://localhost:8000/api',
        ws_url: 'ws://localhost:8000/ws'
      };
    }

    const protocol = window.location.protocol;
    const host = window.location.host;
    // SAAS PROTOCOL FIX: Ensure WebSocket uses secure protocol when page is HTTPS
    const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
    
    if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
      console.log(`🔒 Dynamic URL protocol detection: page=${protocol}, ws=${wsProtocol}`);
    }
    
    return {
      base_url: `${protocol}//${host}`,
      api_url: `${protocol}//${host}/api`,
      ws_url: `${wsProtocol}//${host}/ws`
    };
  }

  /**
   * Reset cached configuration (useful for testing or configuration changes)
   */
  resetConfig(): void {
    this.config = null;
    this.loading = null;
  }
}

// Export singleton instance
export const configService = new ConfigService();

/**
 * React hook for using dynamic configuration
 */
export const useConfig = () => {
  const [config, setConfig] = React.useState<FrontendConfig | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;

    const loadConfig = async () => {
      try {
        const cfg = await configService.getConfig();
        if (mounted) {
          setConfig(cfg);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Failed to load configuration');
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadConfig();

    return () => {
      mounted = false;
    };
  }, []);

  return { config, loading, error, reload: () => configService.resetConfig() };
};

// For backward compatibility, export a function to get config synchronously
export const getCurrentConfig = (): FrontendConfig | null => {
  // This is only safe to call after getConfig() has resolved at least once
  return (configService as any).config;
};
