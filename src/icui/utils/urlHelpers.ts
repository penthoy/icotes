/**
 * URL Helpers - ICUI Framework
 * Utilities for URL construction and domain detection
 */

/**
 * Constructs backend URL with smart domain detection for Cloudflare tunnel compatibility
 * Falls back to current origin if environment URLs don't match current host
 */
export function constructBackendUrl(): string {
  // Get environment URLs
  const envBackendUrl = (import.meta as any).env?.VITE_BACKEND_URL as string | undefined;
  const envApiUrl = (import.meta as any).env?.VITE_API_URL as string | undefined;
  const primaryUrl = envBackendUrl || envApiUrl;
  
  // Get current host
  const currentHost = window.location.host;
  let envHost = '';
  
  // Safely extract host from environment URL
  if (primaryUrl && primaryUrl.trim() !== '') {
    try {
      envHost = new URL(primaryUrl).host;
    } catch (error) {
      console.warn('Could not parse environment URL:', primaryUrl);
    }
  }
  
  // Use environment URL if hosts match, otherwise use current origin
  if (primaryUrl && primaryUrl.trim() !== '' && currentHost === envHost) {
    return primaryUrl;
  } else {
    return window.location.origin;
  }
}

/**
 * Converts HTTP URL to WebSocket URL with intelligent protocol detection
 * SAAS FIX: Ensures wss:// is used when page is loaded over HTTPS
 */
export function httpToWsUrl(httpUrl: string): string {
  // Parse the URL to understand its components
  const url = new URL(httpUrl);
  
  // Determine the correct WebSocket protocol based on current page security
  const currentProtocol = window.location.protocol;
  const shouldUseSecure = currentProtocol === 'https:';
  
  // Force secure WebSocket if page is HTTPS, regardless of input URL protocol
  if (shouldUseSecure) {
    url.protocol = 'wss:';
  } else {
    // Use ws: for non-secure pages
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  }
  
  // Debug logging (optional)
  if ((import.meta as any).env?.VITE_DEBUG_PROTOCOL === 'true') {
    console.log(`🔒 Protocol conversion: page=${currentProtocol}, input=${httpUrl}, output=${url.toString()}`);
  }
  return url.toString();
}

/**
 * Constructs WebSocket URL for a given endpoint
 */
export function constructWebSocketUrl(endpoint: string): string {
  const baseUrl = constructBackendUrl();
  const wsBaseUrl = httpToWsUrl(baseUrl);
  return `${wsBaseUrl}${endpoint}`;
}

/**
 * Constructs HTTP API URL for a given endpoint
 */
export function constructApiUrl(endpoint: string): string {
  const baseUrl = constructBackendUrl();
  return `${baseUrl}${endpoint}`;
}

/**
 * Checks if two URLs have the same host
 */
export function isSameHost(url1: string, url2: string): boolean {
  try {
    const host1 = new URL(url1).host;
    const host2 = new URL(url2).host;
    return host1 === host2;
  } catch {
    return false;
  }
}

/**
 * Validates if a URL is well-formed
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Gets the current environment information
 */
export function getEnvironmentInfo() {
  return {
    currentOrigin: window.location.origin,
    currentHost: window.location.host,
    envBackendUrl: (import.meta as any).env?.VITE_BACKEND_URL,
    envApiUrl: (import.meta as any).env?.VITE_API_URL,
    constructedUrl: constructBackendUrl()
  };
}
