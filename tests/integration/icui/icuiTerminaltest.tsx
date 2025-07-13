/**
 * ICUI Terminal Test Component
 * Minimal test component containing just a terminal to test and fix scrolling issues
 */

import React from 'react';
import ICUITerminalPanelFromScratch from '../../../src/icui/components/panels/ICUITerminalPanelFromScratch';

export const ICUITerminalTest: React.FC = () => {
  return (
    <div className="h-screen w-screen flex flex-col bg-gray-900">
      {/* Simple header for identification */}
      <div className="bg-gray-800 text-white p-2 text-sm">
        ICUI Terminal Test - Scrolling Issue Fix
      </div>
      
      {/* Terminal container taking full remaining height */}
      <div className="flex-1 overflow-hidden">
        <ICUITerminalPanelFromScratch />
      </div>
    </div>
  );
};

export default ICUITerminalTest; 