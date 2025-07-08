/**
 * ICUI Framework Test Component
 * Demonstrates Frame Container and Split Panel functionality
 */

import React from 'react';
import { ICUIFrameContainer, ICUISplitPanel, ICUILayoutPresetSelector } from '../../../src/icui';

interface ICUITestProps {
  className?: string;
}

/**
 * Test component for ICUI Framework
 * Shows Frame Container (1.1), Split Panel (1.2), and Layout State (1.3) functionality
 */
export const ICUITest: React.FC<ICUITestProps> = ({ className = '' }) => {
  return (
    <div className={`icui-test-container p-4 ${className}`}>
      <h2 className="text-xl font-bold mb-4">ICUI Framework Test - v1.3.0</h2>
      
      <div className="space-y-6">
        {/* Frame Container Tests (Step 1.1) */}
        <div>
          <h3 className="text-lg font-semibold mb-3">Step 1.1: Frame Container Tests</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-64">
            <ICUIFrameContainer
              id="icui-frame-1"
              config={{
                responsive: true,
                borderDetection: true,
                minPanelSize: { width: 200, height: 100 },
                resizeHandleSize: 8,
                snapThreshold: 20,
              }}
              className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700"
              onResize={(size) => console.log('Frame 1 resized:', size)}
              onBorderDetected={(borders) => console.log('Frame 1 borders:', borders)}
            >
              <div className="p-4 h-full">
                <h4 className="font-medium mb-2">Border Detection</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Resize window to see border detection. Blue handles appear when not at viewport edges.
                </p>
              </div>
            </ICUIFrameContainer>
            
            <ICUIFrameContainer
              id="icui-frame-2"
              config={{
                responsive: true,
                borderDetection: true,
                minPanelSize: { width: 200, height: 100 },
              }}
              className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700"
            >
              <div className="p-4 h-full">
                <h4 className="font-medium mb-2">Responsive Frame</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  This frame adapts to viewport changes with proper border detection.
                </p>
              </div>
            </ICUIFrameContainer>
          </div>
        </div>

        {/* Layout State Management Tests (Step 1.3) */}
        <div>
          <h3 className="text-lg font-semibold mb-3">Step 1.3: Layout State Management</h3>
          
          <div className="mb-4">
            <h4 className="font-medium mb-2">Layout Presets & Persistence</h4>
            <ICUILayoutPresetSelector 
              className="max-w-2xl"
              showExportImport={true}
            />
          </div>
        </div>

        {/* Split Panel Tests (Step 1.2) */}
        <div>
          <h3 className="text-lg font-semibold mb-3">Step 1.2: Split Panel Tests</h3>
          
          {/* Horizontal Split Test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Horizontal Split Panel</h4>
            <div className="h-64 border border-gray-300 dark:border-gray-600 rounded">
              <ICUISplitPanel
                id="icui-horizontal-split"
                config={{
                  direction: 'horizontal',
                  initialSplit: 40,
                  minSize: 2, // Very small minimum for unrestricted dragging
                  collapsible: true,
                  resizable: true,
                }}
                onSplitChange={(split) => console.log('Horizontal split changed:', split)}
                onPanelCollapse={(panel, collapsed) => console.log(`Panel ${panel} collapsed:`, collapsed)}
                firstPanel={
                  <div className="p-4 h-full bg-green-50 dark:bg-green-900">
                    <h5 className="font-medium">Left Panel</h5>
                    <p className="text-sm mt-2">Drag the vertical handle to resize.</p>
                    <p className="text-sm">Double-click handle to reset to 50%.</p>
                    <p className="text-sm">Use collapse buttons in top-right.</p>
                    <p className="text-sm mt-2"><strong>New:</strong> Smooth drag - no rubberband!</p>
                  </div>
                }
                secondPanel={
                  <div className="p-4 h-full bg-purple-50 dark:bg-purple-900">
                    <h5 className="font-medium">Right Panel</h5>
                    <p className="text-sm mt-2">This panel can be resized and collapsed.</p>
                    <p className="text-sm"><strong>Performance:</strong> No rubberband effect!</p>
                    <div className="mt-4 space-y-2">
                      <div className="w-full bg-purple-200 h-3 rounded"></div>
                      <div className="w-3/4 bg-purple-300 h-3 rounded"></div>
                      <div className="w-1/2 bg-purple-400 h-3 rounded"></div>
                    </div>
                  </div>
                }
              />
            </div>
          </div>

          {/* Vertical Split Test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Vertical Split Panel</h4>
            <div className="h-64 border border-gray-300 dark:border-gray-600 rounded">
              <ICUISplitPanel
                id="icui-vertical-split"
                config={{
                  direction: 'vertical',
                  initialSplit: 60,
                  minSize: 2, // Very small minimum for unrestricted dragging
                  collapsible: true,
                  resizable: true,
                }}
                onSplitChange={(split) => console.log('Vertical split changed:', split)}
                onPanelCollapse={(panel, collapsed) => console.log(`Panel ${panel} collapsed:`, collapsed)}
                firstPanel={
                  <div className="p-4 h-full bg-yellow-50 dark:bg-yellow-900">
                    <h5 className="font-medium">Top Panel</h5>
                    <p className="text-sm mt-2">Drag the horizontal handle below to resize vertically.</p>
                    <p className="text-sm"><strong>Smooth:</strong> No rubberband drag!</p>
                  </div>
                }
                secondPanel={
                  <div className="p-4 h-full bg-pink-50 dark:bg-pink-900">
                    <h5 className="font-medium">Bottom Panel</h5>
                    <p className="text-sm mt-2">Vertical split panels work the same way.</p>
                    <div className="flex gap-2 mt-4">
                      <div className="w-8 h-8 bg-pink-300 rounded"></div>
                      <div className="w-8 h-8 bg-pink-400 rounded"></div>
                      <div className="w-8 h-8 bg-pink-500 rounded"></div>
                    </div>
                  </div>
                }
              />
            </div>
          </div>

          {/* Nested Split Test */}
          <div className="mb-4">
            <h4 className="font-medium mb-2">Nested Split Panels</h4>
            <div className="h-64 border border-gray-300 dark:border-gray-600 rounded">
              <ICUISplitPanel
                id="icui-nested-outer"
                config={{
                  direction: 'horizontal',
                  initialSplit: 50,
                  minSize: 2, // Very small minimum for unrestricted dragging
                  collapsible: false,
                  resizable: true,
                }}
                firstPanel={
                  <div className="h-full bg-orange-50 dark:bg-orange-900 p-2">
                    <h5 className="font-medium text-sm mb-2">Outer Left</h5>
                    <ICUISplitPanel
                      id="icui-nested-inner"
                      config={{
                        direction: 'vertical',
                        initialSplit: 30,
                        minSize: 2, // Very small minimum for unrestricted dragging
                        collapsible: true,
                        resizable: true,
                      }}
                      firstPanel={
                        <div className="p-2 h-full bg-red-100 dark:bg-red-900">
                          <p className="text-xs">Nested Top</p>
                        </div>
                      }
                      secondPanel={
                        <div className="p-2 h-full bg-red-200 dark:bg-red-800">
                          <p className="text-xs">Nested Bottom</p>
                        </div>
                      }
                    />
                  </div>
                }
                secondPanel={
                  <div className="p-4 h-full bg-teal-50 dark:bg-teal-900">
                    <h5 className="font-medium">Outer Right</h5>
                    <p className="text-sm mt-2">Demonstrates nested split panels.</p>
                    <p className="text-sm">The left side contains a vertical split inside the horizontal split.</p>
                  </div>
                }
              />
            </div>
          </div>
        </div>
      </div>
      
      {/* Instructions */}
      <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded">
        <h4 className="font-semibold mb-2">ICUI Framework v1.3.0 - Testing Instructions</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h5 className="font-medium mb-1">Frame Containers (v1.1):</h5>
            <ul className="space-y-1">
              <li>• Resize browser window to test border detection</li>
              <li>• Hover over frame edges for resize handles</li>
              <li>• Check debug info and console logs</li>
            </ul>
          </div>
          <div>
            <h5 className="font-medium mb-1">Layout State (v1.3):</h5>
            <ul className="space-y-1">
              <li>• Switch between layout presets (Default, Code Focused, Terminal Focused)</li>
              <li>• Export current layout to JSON</li>
              <li>• Import layouts from JSON</li>
              <li>• Undo layout changes</li>
              <li>• Persistent storage (survives browser reload)</li>
            </ul>
          </div>
          <div>
            <h5 className="font-medium mb-1">Split Panels (v1.2):</h5>
            <ul className="space-y-1">
              <li>• Drag split handles to resize panels (no rubberband!)</li>
              <li>• Double-click handles to reset to 50%</li>
              <li>• Use collapse buttons in top-right</li>
              <li>• Test nested splits for complex layouts</li>
              <li>• <strong>Fixed:</strong> Smooth drag with 2px minimum</li>
            </ul>
          </div>
        </div>
        <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900 rounded">
          <p className="text-sm"><strong>New in v1.3:</strong> Layout State Management with persistent storage, presets (Default, Code Focused, Terminal Focused), export/import functionality, and undo support.</p>
          <p className="text-sm mt-1"><strong>Performance:</strong> All previous improvements maintained - smooth dragging, 2px minimum, no rubberband effect.</p>
        </div>
      </div>
    </div>
  );
};

export default ICUITest;
