/**
 * Chat Phase 3 & 4 Integration Test
 * 
 * Tests the implemented features from Phase 3 and Phase 4:
 * - ImagePreview component with file/URL support
 * - FileUpload component with drag/drop
 * - FileEditWidget with diff display
 * - CodeExecutionWidget with output formatting
 * - Widget registry with auto-registration
 */

import React, { useState, useCallback } from 'react';
import { ImagePreview, FileUpload } from '../../src/icui/components/chat/media';
import { FileEditWidget, CodeExecutionWidget } from '../../src/icui/components/chat/widgets';
import { ToolCallData } from '../../src/icui/components/chat/ToolCallWidget';
import { listRegisteredWidgets, getWidgetForTool } from '../../src/icui/services/widgetRegistry';

const ChatPhase34Test: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [testResults, setTestResults] = useState<{ [key: string]: boolean }>({});

  // Mock tool call data for testing widgets
  const mockFileEditTool: ToolCallData = {
    id: 'file-edit-1',
    toolName: 'file_edit',
    category: 'file',
    status: 'success',
    progress: 100,
    input: {
      file_path: '/src/components/example.tsx',
      operation: 'update',
      original_content: `import React from 'react';

const Example = () => {
  return <div>Hello World</div>;
};

export default Example;`,
      content: `import React from 'react';

const Example: React.FC = () => {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <h1>Hello World</h1>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
};

export default Example;`
    },
    output: {
      file_path: '/src/components/example.tsx',
      operation: 'update',
      success: true
    },
    startTime: new Date(Date.now() - 5000),
    endTime: new Date()
  };

  const mockCodeExecutionTool: ToolCallData = {
    id: 'code-exec-1',
    toolName: 'execute_python',
    category: 'code',
    status: 'success',
    progress: 100,
    input: {
      code: `import numpy as np
import matplotlib.pyplot as plt

# Generate sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, label='sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.title('Sine Wave')
plt.legend()
plt.grid(True)
plt.show()

print("Plot generated successfully!")
print(f"Data points: {len(x)}")`,
      language: 'python'
    },
    output: {
      output: `Plot generated successfully!
Data points: 100`,
      exit_code: 0,
      execution_time: 2.34,
      environment: 'python 3.9.7'
    },
    startTime: new Date(Date.now() - 3000),
    endTime: new Date()
  };

  const mockCodeErrorTool: ToolCallData = {
    id: 'code-error-1',
    toolName: 'execute_python',
    category: 'code',
    status: 'error',
    progress: 0,
    input: {
      code: `# This code has an intentional error
print("Starting calculation...")
result = 10 / 0  # Division by zero error
print(f"Result: {result}")`,
      language: 'python'
    },
    output: {
      error: 'ZeroDivisionError: division by zero',
      stack_trace: `Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
    result = 10 / 0
ZeroDivisionError: division by zero`,
      exit_code: 1,
      execution_time: 0.12,
      environment: 'python 3.9.7'
    },
    startTime: new Date(Date.now() - 1000),
    endTime: new Date(),
    error: 'Code execution failed with exit code 1'
  };

  // Handle file selection
  const handleFilesSelected = useCallback((files: File[]) => {
    setSelectedFiles(files);
    console.log('Files selected:', files.map(f => f.name));
  }, []);

  // Handle file upload
  const handleFilesUploaded = useCallback((files: File[]) => {
    console.log('Files uploaded:', files.map(f => f.name));
  }, []);

  // Run widget registry tests
  const runWidgetTests = useCallback(() => {
    const results: { [key: string]: boolean } = {};

    try {
      // Test widget registry
      const registeredWidgets = listRegisteredWidgets();
      results['widget_registry_populated'] = registeredWidgets.length > 0;
      results['file_edit_widget_registered'] = registeredWidgets.includes('file_edit');
      results['code_execution_widget_registered'] = registeredWidgets.includes('execute_python');

      // Test widget resolution
      const fileEditWidget = getWidgetForTool('file_edit');
      const codeExecWidget = getWidgetForTool('execute_python');
      const defaultWidget = getWidgetForTool('unknown_tool');
      
      results['file_edit_widget_resolved'] = fileEditWidget !== defaultWidget;
      results['code_exec_widget_resolved'] = codeExecWidget !== defaultWidget;

      console.log('Widget registry test results:', results);
    } catch (error) {
      console.error('Widget registry test error:', error);
      results['widget_registry_error'] = true;
    }

    setTestResults(results);
  }, []);

  // Sample images for testing
  const sampleImageUrl = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIFByZXZpZXc8L3RleHQ+PC9zdmc+';

  return (
    <div className="p-6 space-y-8" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      <h1 className="text-3xl font-bold mb-6">Chat Phase 3 & 4 Integration Test</h1>

      {/* Test Results */}
      <div className="bg-white rounded-lg border p-4" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}>
        <h2 className="text-xl font-semibold mb-4">Widget Registry Tests</h2>
        <div className="space-y-2 mb-4">
          {Object.entries(testResults).map(([test, passed]) => (
            <div key={test} className="flex items-center gap-2">
              <span className={passed ? 'text-green-500' : 'text-red-500'}>
                {passed ? '✅' : '❌'}
              </span>
              <span className="font-mono text-sm">{test}</span>
            </div>
          ))}
        </div>
        <button
          onClick={runWidgetTests}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Run Widget Tests
        </button>
      </div>

      {/* Phase 3: Media Components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Phase 3: Media & File Support</h2>

        {/* Image Preview */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">ImagePreview Component</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium mb-2">URL-based Image</h4>
              <ImagePreview
                src={sampleImageUrl}
                alt="Sample SVG image"
                maxWidth={200}
                maxHeight={150}
                showMetadata={true}
              />
            </div>
            <div>
              <h4 className="font-medium mb-2">Features</h4>
              <ul className="text-sm space-y-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <li>• Click to expand full size</li>
                <li>• Copy button on hover</li>
                <li>• Metadata display (dimensions, size)</li>
                <li>• Loading and error states</li>
                <li>• Keyboard navigation (Enter/Space to expand, Esc to close)</li>
              </ul>
            </div>
          </div>
        </div>

        {/* File Upload */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">FileUpload Component</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <FileUpload
                accept="image/*,.pdf,.txt,.json"
                maxSize={5 * 1024 * 1024} // 5MB
                maxFiles={3}
                multiple={true}
                onFilesSelected={handleFilesSelected}
                onFilesUploaded={handleFilesUploaded}
              />
            </div>
            <div>
              <h4 className="font-medium mb-2">Features Demonstrated</h4>
              <ul className="text-sm space-y-1" style={{ color: 'var(--icui-text-secondary)' }}>
                <li>• Drag and drop interface</li>
                <li>• File type validation (images, PDF, text, JSON)</li>
                <li>• Size limits (5MB max)</li>
                <li>• Multiple file selection (max 3)</li>
                <li>• File preview with thumbnails</li>
                <li>• Progress indicators</li>
                <li>• Error handling and validation</li>
              </ul>
              {selectedFiles.length > 0 && (
                <div className="mt-4">
                  <h5 className="font-medium mb-2">Selected Files:</h5>
                  <ul className="text-sm space-y-1">
                    {selectedFiles.map((file, index) => (
                      <li key={index}>
                        {file.name} ({(file.size / 1024).toFixed(1)} KB)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Phase 4: Advanced Tool Call Widgets */}
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Phase 4: Advanced Tool Call Widgets</h2>

        {/* File Edit Widget */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">FileEditWidget - File Modification Display</h3>
          <FileEditWidget
            toolCall={mockFileEditTool}
            expandable={true}
            defaultExpanded={true}
          />
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Features:</strong> Diff display (before/after/diff views), syntax highlighting, 
            file path display, operation type indicators, copy functionality, expand/collapse
          </div>
        </div>

        {/* Code Execution Widget - Success */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">CodeExecutionWidget - Successful Execution</h3>
          <CodeExecutionWidget
            toolCall={mockCodeExecutionTool}
            expandable={true}
            defaultExpanded={true}
          />
        </div>

        {/* Code Execution Widget - Error */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">CodeExecutionWidget - Error Handling</h3>
          <CodeExecutionWidget
            toolCall={mockCodeErrorTool}
            expandable={true}
            defaultExpanded={true}
          />
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Features:</strong> Code/output/error tabs, syntax highlighting, execution timing, 
            exit code display, error messages with stack traces, retry functionality, copy buttons
          </div>
        </div>
      </div>

      {/* Integration Notes */}
      <div className="bg-blue-50 rounded-lg p-4" style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}>
        <h3 className="font-medium mb-2">Integration Status</h3>
        <ul className="text-sm space-y-1">
          <li>✅ All components follow ICUI theme variables</li>
          <li>✅ Widgets auto-register with the widget registry</li>
          <li>✅ Full accessibility support (ARIA labels, keyboard navigation)</li>
          <li>✅ Error handling and loading states</li>
          <li>✅ Copy functionality for all content types</li>
          <li>✅ Responsive design and mobile support</li>
          <li>✅ TypeScript types and clean code architecture</li>
        </ul>
      </div>
    </div>
  );
};

export default ChatPhase34Test; 