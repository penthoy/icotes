/**
 * Test Integrated Home Component - Minimal version for debugging
 */

import React from 'react';

interface TestIntegratedHomeProps {
  className?: string;
}

const TestIntegratedHome: React.FC<TestIntegratedHomeProps> = ({ className = '' }) => {
  return (
    <div className={`test-integrated-home ${className}`}>
      <h1>Test Integrated Home</h1>
      <p>If you see this, the route is working.</p>
    </div>
  );
};

export default TestIntegratedHome;
