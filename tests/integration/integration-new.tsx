/**
 * Integration Test Environment
 * 
 * Main integration test component for ICUI-ICPY integration testing.
 * Provides a comprehensive testing environment with connection status,
 * backend communication testing, and component integration verification.
 */

import React from 'react';
import { BackendContextProvider } from '../../src/contexts/BackendContext';
import { IntegratedHome } from './components/IntegratedHome';

/**
 * Main Integration Test Component
 */
export const Integration: React.FC = () => {
  return (
    <BackendContextProvider>
      <div className="integration-test-environment">
        <IntegratedHome />
      </div>
    </BackendContextProvider>
  );
};

export default Integration;
