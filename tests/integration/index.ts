/**
 * Integration Tests Index
 * 
 * Main entry point for all integration tests related to ICUI-ICPY integration.
 * This file provides a comprehensive test suite for Phase 1.1 implementation.
 */

import { runWebSocketServiceTests } from './websocket-service.test';

/**
 * Run all Phase 1.1 integration tests
 */
export async function runPhase1_1Tests() {
  console.log('='.repeat(60));
  console.log('ICUI-ICPY Integration Tests - Phase 1.1');
  console.log('WebSocket Service Layer Testing');
  console.log('='.repeat(60));
  
  let totalPassed = 0;
  let totalFailed = 0;
  
  try {
    // Run WebSocket Service Tests
    const wsResults = await runWebSocketServiceTests();
    totalPassed += wsResults.passed;
    totalFailed += wsResults.failed;
    
    // Additional tests can be added here as Phase 1.1 expands
    
  } catch (error) {
    console.error('Test suite failed:', error);
    totalFailed++;
  }
  
  console.log('\n' + '='.repeat(60));
  console.log(`TOTAL RESULTS: ${totalPassed} passed, ${totalFailed} failed`);
  console.log('='.repeat(60));
  
  if (totalFailed === 0) {
    console.log('🎉 All Phase 1.1 tests passed!');
    console.log('✅ WebSocket Service Layer is ready for Phase 1.2');
  } else {
    console.log('❌ Some tests failed. Please fix issues before proceeding.');
  }
  
  return {
    passed: totalPassed,
    failed: totalFailed,
    success: totalFailed === 0
  };
}

// Export individual test functions for selective testing
export { runWebSocketServiceTests } from './websocket-service.test';
export { Integration } from './integration';

// Run tests if this file is executed directly
if (typeof window !== 'undefined') {
  // Browser environment - can be called manually
  (window as any).runPhase1_1Tests = runPhase1_1Tests;
} else if (typeof module !== 'undefined' && module.exports) {
  // Node.js environment
  module.exports = {
    runPhase1_1Tests,
    runWebSocketServiceTests
  };
}
