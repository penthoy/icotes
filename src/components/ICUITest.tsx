/**
 * ICUI Framework Test Component
 * Simple demonstration of the Frame Container
 */

import React from 'react';
import { ICUIFrameContainer } from '../icui';

interface ICUITestProps {
  className?: string;
}

/**
 * Test component for ICUI Framework
 * Shows basic usage of the Frame Container
 */
export const ICUITest: React.FC<ICUITestProps> = ({ className = '' }) => {
  return (
    <div className={`icui-test-container p-4 ${className}`}>
      <h2 className="text-xl font-bold mb-4">ICUI Framework Test</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-96">
        {/* First frame */}
        <ICUIFrameContainer
          id="icui-test-frame-1"
          config={{
            responsive: true,
            borderDetection: true,
            minPanelSize: { width: 250, height: 150 },
          }}
          className="bg-gray-50 dark:bg-gray-900"
          onResize={(size) => console.log('Frame 1 resized:', size)}
          onBorderDetected={(borders) => console.log('Frame 1 borders:', borders)}
        >
          <div className="p-4">
            <h3 className="font-semibold mb-2">Test Frame 1</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              This is a test frame with responsive borders and resize handles.
              Try resizing the window to see border detection in action.
            </p>
            <div className="mt-4 space-y-2">
              <div className="w-full bg-blue-200 h-2 rounded"></div>
              <div className="w-3/4 bg-green-200 h-2 rounded"></div>
              <div className="w-1/2 bg-yellow-200 h-2 rounded"></div>
            </div>
          </div>
        </ICUIFrameContainer>
        
        {/* Second frame */}
        <ICUIFrameContainer
          id="icui-test-frame-2"
          config={{
            responsive: true,
            borderDetection: true,
            minPanelSize: { width: 200, height: 100 },
            resizeHandleSize: 6,
          }}
          className="bg-blue-50 dark:bg-blue-900"
          onResize={(size) => console.log('Frame 2 resized:', size)}
          onBorderDetected={(borders) => console.log('Frame 2 borders:', borders)}
        >
          <div className="p-4">
            <h3 className="font-semibold mb-2">Test Frame 2</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              This frame has larger resize handles and different styling.
              Hover over the edges to see resize handles.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs">Responsive</span>
              <span className="px-2 py-1 bg-green-200 text-green-800 rounded text-xs">Borders</span>
              <span className="px-2 py-1 bg-yellow-200 text-yellow-800 rounded text-xs">Resizable</span>
            </div>
          </div>
        </ICUIFrameContainer>
      </div>
      
      <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded">
        <h4 className="font-semibold mb-2">ICUI Framework Features</h4>
        <ul className="text-sm space-y-1">
          <li>• Responsive frame container with border detection</li>
          <li>• Dynamic resize handles with visual feedback</li>
          <li>• Configurable minimum sizes and snap thresholds</li>
          <li>• Development debug information</li>
          <li>• TypeScript support with comprehensive type definitions</li>
        </ul>
      </div>
    </div>
  );
};

export default ICUITest;
