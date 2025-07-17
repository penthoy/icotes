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
  // Use debug component for now to isolate the issue
  return (
    <div style={{ padding: '20px' }}>
      <h1>Integration Test</h1>
      <DebugIntegration />
      
      {/* Uncomment when debug passes */}
      {/* 
      <BackendContextProvider>
        <IntegratedHome />
      </BackendContextProvider>
      */}
    </div>
  );
};

export default Integration;
