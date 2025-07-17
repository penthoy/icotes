/**
 * Integration Test Route
 * 
 * This route provides a comprehensive test interface for the ICUI-ICPY integration.
 */

import React from 'react';
import { BackendContextProvider } from '../../src/contexts/BackendContext';
import { IntegratedHome } from './components/IntegratedHome';
import DebugIntegration from './debug-integration';

const Integration: React.FC = () => {
  // Switch back to full integration test now that debug test worked
  return (
    <BackendContextProvider>
      <div style={{ padding: '20px' }}>
        <h1>Integration Test</h1>
        <IntegratedHome />
      </div>
    </BackendContextProvider>
  );
};

export default Integration;
