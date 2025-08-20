/**
 * Cursor Style Test Component
 * 
 * Demonstrates the new Cursor-inspired styling with gray borders
 * and transparent backgrounds for better readability
 */

import React from 'react';
import { FileEditWidget } from '../../src/icui/components/chat/widgets';
import { ToolCallData } from '../../src/icui/components/chat/ToolCallWidget';

const CursorStyleTest: React.FC = () => {
  // Sample file edit tool call with realistic data
  const mockFileEditTool: ToolCallData = {
    id: 'file-edit-cursor-style',
    toolName: 'file_edit',
    category: 'file',
    status: 'success',
    progress: 100,
    input: {
      file_path: '/home/penthoy/icotes/src/components/Example.tsx',
      operation: 'update',
      original_content: `import React from 'react';

const Example = () => {
  return <div>Hello World</div>;
};

export default Example;`,
      content: `import React, { useState } from 'react';

const Example: React.FC = () => {
  const [count, setCount] = useState(0);
  
  return (
    <div className="p-4">
      <h1 className="text-xl font-bold">Hello World</h1>
      <p>Count: {count}</p>
      <button 
        onClick={() => setCount(count + 1)}
        className="px-3 py-1 bg-blue-500 text-white rounded"
      >
        Increment
      </button>
    </div>
  );
};

export default Example;`
    },
    output: {
      file_path: '/home/penthoy/icotes/src/components/Example.tsx',
      operation: 'update',
      success: true
    },
    startTime: new Date(Date.now() - 2000),
    endTime: new Date(),
    metadata: {
      originalToolName: 'edit_file'
    }
  };

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#ffffff' }}>
      <h1 className="text-2xl font-bold text-gray-900">Cursor-Style Widget Design</h1>
      
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">File Edit Widget - New Cursor Style</h2>
        <p className="text-gray-600 text-sm">
          Clean design with gray borders, transparent backgrounds, and improved readability
        </p>
        
        {/* New Cursor-style widget */}
        <FileEditWidget
          toolCall={mockFileEditTool}
          expandable={true}
          defaultExpanded={false}
        />
        
        <div className="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
          <h3 className="font-medium text-gray-900 mb-2">Design Features:</h3>
          <ul className="text-sm text-gray-700 space-y-1">
            <li>• Gray border (#d1d5db) instead of flat background</li>
            <li>• Transparent background for better readability</li>
            <li>• Subtle hover effects on interactive elements</li>
            <li>• Clean typography with proper gray color hierarchy</li>
            <li>• Minimal padding and spacing like Cursor</li>
            <li>• Border-separated sections instead of background changes</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default CursorStyleTest; 