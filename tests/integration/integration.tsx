/**
 * Integration Test Route
 * 
 * This route provides a comprehensive test interface for the ICUI-ICPY integration.
 * Accessible at http://192.168.2.195:8000/integration
 */

import React from 'react';
import { BackendContextProvider } from '../../src/contexts/BackendContext';
import { IntegratedHome } from './components/IntegratedHome';

const Integration: React.FC = () => {
  return (
    <BackendContextProvider>
      <div className="integration-test-container">
        <header className="bg-blue-600 text-white p-4">
          <h1 className="text-xl font-bold">ICUI-ICPY Backend Integration Test</h1>
          <div className="text-sm mt-1">
            Terminal Integration Test Environment - http://192.168.2.195:8000/integration
          </div>
        </header>
        <div className="p-4">
          <IntegratedHome />
        </div>
      </div>
    </BackendContextProvider>
  );
};

export default Integration;
