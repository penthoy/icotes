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
      <h2 className="text-xl font-bold mb-4">ICUI Framework Test - Border & Resize Detection</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-screen max-h-96">
        {/* First frame - test horizontal scaling */}
        <ICUIFrameContainer
          id="icui-test-frame-1"
          config={{
            responsive: true,
            borderDetection: true,
            minPanelSize: { width: 200, height: 100 },
            resizeHandleSize: 8,
            snapThreshold: 20,
          }}
          className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700"
          onResize={(size) => console.log('Frame 1 resized:', size)}
          onBorderDetected={(borders) => console.log('Frame 1 borders detected:', borders)}
        >
          <div className="p-4 h-full flex flex-col">
            <h3 className="font-semibold mb-2">Horizontal Scaling Test</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Resize the window horizontally to see border detection.
              Look for the blue resize handle on the right edge.
            </p>
            <div className="flex-1 flex flex-col justify-center space-y-2">
              <div className="w-full bg-blue-200 h-3 rounded"></div>
              <div className="w-3/4 bg-green-200 h-3 rounded"></div>
              <div className="w-1/2 bg-yellow-200 h-3 rounded"></div>
              <div className="w-1/4 bg-red-200 h-3 rounded"></div>
            </div>
          </div>
        </ICUIFrameContainer>
        
        {/* Second frame - test vertical scaling */}
        <ICUIFrameContainer
          id="icui-test-frame-2"
          config={{
            responsive: true,
            borderDetection: true,
            minPanelSize: { width: 200, height: 100 },
            resizeHandleSize: 8,
            snapThreshold: 20,
          }}
          className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700"
          onResize={(size) => console.log('Frame 2 resized:', size)}
          onBorderDetected={(borders) => console.log('Frame 2 borders detected:', borders)}
        >
          <div className="p-4 h-full flex flex-col">
            <h3 className="font-semibold mb-2">Vertical Scaling Test</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Resize the window vertically to see border detection.
              Look for the blue resize handle on the bottom edge.
            </p>
            <div className="flex-1 flex flex-col justify-around">
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-blue-200 text-blue-800 rounded text-xs">Responsive</span>
                <span className="px-2 py-1 bg-green-200 text-green-800 rounded text-xs">Borders</span>
                <span className="px-2 py-1 bg-yellow-200 text-yellow-800 rounded text-xs">Resizable</span>
              </div>
              <div className="text-center">
                <div className="inline-block w-16 h-16 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full"></div>
              </div>
            </div>
          </div>
        </ICUIFrameContainer>
      </div>
      
      <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded">
        <h4 className="font-semibold mb-2">ICUI Framework Testing Instructions</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h5 className="font-medium mb-1">Border Detection:</h5>
            <ul className="space-y-1">
              <li>• Resize browser window horizontally</li>
              <li>• Watch for right border detection</li>
              <li>• Resize browser window vertically</li>
              <li>• Watch for bottom border detection</li>
            </ul>
          </div>
          <div>
            <h5 className="font-medium mb-1">Resize Handles:</h5>
            <ul className="space-y-1">
              <li>• Hover over right edge for vertical resize</li>
              <li>• Hover over bottom edge for horizontal resize</li>
              <li>• Debug info shows handle positions</li>
              <li>• Console logs show detection events</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ICUITest;
