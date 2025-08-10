/**
 * Protocol Detection Test Utility
 * 
 * Quick utility to test WebSocket protocol detection logic
 * Can be imported in browser console for debugging
 */

interface ProtocolTestResult {
  currentPageProtocol: string;
  shouldUseSecure: boolean;
  testUrls: {
    input: string;
    output: string;
    expectedProtocol: string;
  }[];
  configServiceUrls?: {
    base_url: string;
    api_url: string;
    ws_url: string;
  };
}

/**
 * Test the protocol detection logic with various URL inputs
 */
export function testProtocolDetection(): ProtocolTestResult {
  const currentProtocol = window.location.protocol;
  const shouldUseSecure = currentProtocol === 'https:';
  
  const testUrls = [
    'ws://localhost:8000/ws',
    'wss://localhost:8000/ws',
    'ws://user-abc.icotes.com/ws',
    'wss://user-abc.icotes.com/ws',
    'ws://192.168.1.100:8000/ws',
  ];
  
  const results: ProtocolTestResult = {
    currentPageProtocol: currentProtocol,
    shouldUseSecure,
    testUrls: testUrls.map(input => {
      const url = new URL(input);
      const finalProtocol = shouldUseSecure ? 'wss:' : url.protocol;
      const output = `${finalProtocol}//${url.host}${url.pathname}${url.search}`;
      
      return {
        input,
        output,
        expectedProtocol: finalProtocol
      };
    })
  };
  
  return results;
}

/**
 * Test the dynamic URL generation from config service
 */
export async function testConfigServiceUrls(): Promise<ProtocolTestResult['configServiceUrls']> {
  try {
    const { configService } = await import('../services/config-service');
    const config = await configService.getConfig();
    
    return {
      base_url: config.base_url,
      api_url: config.api_url,
      ws_url: config.ws_url
    };
  } catch (error) {
    console.error('Failed to get config service URLs:', error);
    return undefined;
  }
}

/**
 * Run comprehensive protocol detection tests
 */
export async function runProtocolTests(): Promise<void> {
  console.group('🔒 Protocol Detection Tests');
  
  const basicResults = testProtocolDetection();
  console.log('Basic Protocol Detection:', basicResults);
  
  const configUrls = await testConfigServiceUrls();
  if (configUrls) {
    console.log('Config Service URLs:', configUrls);
  }
  
  // Test the urlHelpers functions if available
  try {
    const { httpToWsUrl, constructWebSocketUrl } = await import('../icui/utils/urlHelpers');
    
    console.group('URL Helper Functions');
    const testHttpUrls = [
      'http://localhost:8000',
      'https://localhost:8000',
      'http://user-abc.icotes.com',
      'https://user-abc.icotes.com'
    ];
    
    testHttpUrls.forEach(httpUrl => {
      const wsUrl = httpToWsUrl(httpUrl);
      console.log(`${httpUrl} -> ${wsUrl}`);
    });
    
    console.log('WebSocket endpoint construction:');
    const wsEndpoint = constructWebSocketUrl('/ws/terminal/abc123');
    console.log(`/ws/terminal/abc123 -> ${wsEndpoint}`);
    
    console.groupEnd();
  } catch (error) {
    console.warn('Could not test URL helper functions:', error);
  }
  
  console.groupEnd();
  
  // Summary
  console.log(`
🔒 Protocol Detection Summary:
- Current page: ${basicResults.currentPageProtocol}
- Should use secure: ${basicResults.shouldUseSecure}
- All WebSocket connections will use: ${basicResults.shouldUseSecure ? 'wss://' : 'ws://'}
  `);
}

// Auto-run tests if in development mode
if (import.meta.env.DEV) {
  console.log('🧪 Protocol detection test utility loaded. Run runProtocolTests() in console to test.');
}
