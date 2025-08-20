/**
 * Chat Phase 4.5 Integration Test
 * 
 * Tests the enhanced tool call processing features:
 * - Enhanced tool call detection and parsing
 * - Real-time progress indicators with spinning icons
 * - Proper tool execution state management
 * - SemanticSearchWidget for search results
 * - ProgressWidget for "🔧 Executing tools..." indicators
 * - Collapsible tool execution details
 * - Fixed text-based output rendering (no code highlighting for non-code)
 */

import React, { useState, useCallback } from 'react';
import { SemanticSearchWidget, FileEditWidget, CodeExecutionWidget, ProgressWidget } from '../../src/icui/components/chat/widgets';
import { ToolCallData } from '../../src/icui/components/chat/ToolCallWidget';
import { listRegisteredWidgets, getWidgetForTool } from '../../src/icui/services/widgetRegistry';

const ChatPhase45Test: React.FC = () => {
  const [testResults, setTestResults] = useState<{ [key: string]: boolean }>({});

  // Mock tool call data for testing enhanced parsing
  const mockSemanticSearchTool: ToolCallData = {
    id: 'search-1',
    toolName: 'semantic_search',
    category: 'data',
    status: 'success',
    progress: 100,
    input: {
      query: 'AGENT_NAME',
      scope: '/home/penthoy/icotes/workspace',
      fileTypes: ['py']
    },
    output: {
      result: `[{'file': '/home/penthoy/icotes/workspace/plugins/example_tool_using_agent.py', 'line': 24, 'snippet': 'AGENT_NAME = "ExampleToolUser"'}, {'file': '/home/penthoy/icotes/workspace/plugins/agent_creator_agent.py', 'line': 24, 'snippet': 'AGENT_NAME = "AgentCreator"'}]`
    },
    startTime: new Date(Date.now() - 2000),
    endTime: new Date(),
    metadata: {
      originalToolName: 'semantic_search'
    }
  };

  const mockProgressTool: ToolCallData = {
    id: 'progress-1',
    toolName: 'progress',
    category: 'custom',
    status: 'running',
    progress: 45,
    input: { action: 'Executing tools...' },
    output: undefined,
    startTime: new Date(Date.now() - 3000),
    endTime: undefined,
    metadata: {
      isProgress: true,
      originalText: '🔧 **Executing tools...**'
    }
  };

  const mockTerminalTool: ToolCallData = {
    id: 'terminal-1',
    toolName: 'code_execution',
    category: 'code',
    status: 'success',
    progress: 100,
    input: {
      command: 'ls -la /home/penthoy/icotes/workspace',
      explanation: 'List files and directories in the workspace root'
    },
    output: {
      output: `total 20
drwxrwxr-x  4 penthoy penthoy 4096 Aug 19 09:42 .
drwxrwxr-x 14 penthoy penthoy 4096 Aug 18 18:35 ..
drwxrwxr-x  3 penthoy penthoy 4096 Aug 19 01:41 .icotes
-rw-rw-r--  1 penthoy penthoy   34 Aug  8 06:36 README.md
drwxrwxr-x  3 penthoy penthoy 4096 Aug 18 18:35 plugins`,
      exit_code: 0,
      execution_time: 0.12
    },
    startTime: new Date(Date.now() - 1000),
    endTime: new Date(),
    metadata: {
      originalToolName: 'run_in_terminal'
    }
  };

  const mockFileReadTool: ToolCallData = {
    id: 'file-read-1',
    toolName: 'file_edit',
    category: 'file',
    status: 'success',
    progress: 100,
    input: {
      filePath: '/home/penthoy/icotes/workspace/README.md',
      startLine: 1,
      endLine: 400
    },
    output: {
      content: `# Demo Files for Simple Editor



`,
      operation: 'read'
    },
    startTime: new Date(Date.now() - 500),
    endTime: new Date(),
    metadata: {
      originalToolName: 'read_file'
    }
  };

  // Sample tool execution text that should be parsed
  const sampleToolExecutionText = `🔧 **Executing tools...**

📋 **semantic_search**: {'query': 'AGENT_NAME', 'scope': '/home/penthoy/icotes/workspace', 'fileTypes': ['py']}
✅ **Success**: [{'file': '/home/penthoy/icotes/workspace/plugins/example_tool_using_agent.py', 'line': 24, 'snippet': 'AGENT_NAME = "ExampleToolUser"'}, {'file': '/home/penthoy/icotes/workspace/plugins/agent_creator_agent.py', 'line': 24, 'snippet': 'AGENT_NAME = "AgentCreator"'}]

🔧 **Tool execution complete. Continuing...**`;

  const sampleProgressText = `🔧 **Executing tools...**

I'm currently working on your request. This may take a moment...`;

  // Run enhanced widget tests
  const runEnhancedTests = useCallback(() => {
    const results: { [key: string]: boolean } = {};

    try {
      // Test enhanced widget registry
      const registeredWidgets = listRegisteredWidgets();
      results['semantic_search_widget_registered'] = registeredWidgets.includes('semantic_search');
      results['progress_widget_registered'] = registeredWidgets.includes('progress');
      results['file_edit_widget_registered'] = registeredWidgets.includes('file_edit');
      results['code_execution_widget_registered'] = registeredWidgets.includes('code_execution');

      // Test widget resolution
      const searchWidget = getWidgetForTool('semantic_search');
      const progressWidget = getWidgetForTool('progress');
      const fileWidget = getWidgetForTool('file_edit');
      const codeWidget = getWidgetForTool('code_execution');
      const defaultWidget = getWidgetForTool('unknown_tool');
      
      results['search_widget_resolved'] = searchWidget !== defaultWidget;
      results['progress_widget_resolved'] = progressWidget !== defaultWidget;
      results['file_widget_resolved'] = fileWidget !== defaultWidget;
      results['code_widget_resolved'] = codeWidget !== defaultWidget;

      // Test widget component names (check if they're the right components)
      results['search_widget_correct'] = searchWidget.name?.includes('SemanticSearch') || false;
      results['progress_widget_correct'] = progressWidget.name?.includes('Progress') || false;

      console.log('Enhanced widget registry test results:', results);
    } catch (error) {
      console.error('Enhanced widget registry test error:', error);
      results['enhanced_widget_test_error'] = true;
    }

    setTestResults(results);
  }, []);

  return (
    <div className="p-6 space-y-8" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      <h1 className="text-3xl font-bold mb-6">Chat Phase 4.5 Integration Test</h1>
      <p className="text-lg mb-4" style={{ color: 'var(--icui-text-secondary)' }}>
        Enhanced tool call processing with proper parsing, progress indicators, and specialized widgets.
      </p>

      {/* Test Results */}
      <div className="bg-white rounded-lg border p-4" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}>
        <h2 className="text-xl font-semibold mb-4">Enhanced Widget Registry Tests</h2>
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
          onClick={runEnhancedTests}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Run Enhanced Tests
        </button>
      </div>

      {/* Phase 4.5: Enhanced Tool Call Processing */}
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Phase 4.5: Enhanced Tool Call Processing</h2>

        {/* Semantic Search Widget */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">SemanticSearchWidget - Enhanced Search Results Display</h3>
          <SemanticSearchWidget
            toolCall={mockSemanticSearchTool}
            expandable={true}
            defaultExpanded={true}
          />
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Features:</strong> Proper search result parsing, file path display, snippet formatting without code highlighting, 
            search parameters display, copy functionality, result count indicators
          </div>
        </div>

        {/* Progress Widget - Running */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">ProgressWidget - Real-time Tool Execution Progress</h3>
          <ProgressWidget
            toolCall={mockProgressTool}
            expandable={true}
            defaultExpanded={true}
          />
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Features:</strong> Spinning progress indicators, step-by-step execution display, 
            collapsible details, execution timing, real-time status updates
          </div>
        </div>

        {/* Code Execution Widget - Terminal Output */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">CodeExecutionWidget - Terminal Command Results</h3>
          <CodeExecutionWidget
            toolCall={mockTerminalTool}
            expandable={true}
            defaultExpanded={false}
          />
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Enhanced:</strong> Proper text output formatting (no syntax highlighting for terminal output), 
            exit code display, execution timing, command parameter display
          </div>
        </div>

        {/* File Edit Widget - Read Operation */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">FileEditWidget - File Read Operation</h3>
          <FileEditWidget
            toolCall={mockFileReadTool}
            expandable={true}
            defaultExpanded={false}
          />
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Enhanced:</strong> Proper text content display (no code highlighting for README.md), 
            file path display, operation type indicators, collapsible by default
          </div>
        </div>
      </div>

      {/* Sample Tool Execution Parsing */}
      <div className="space-y-6">
        <h2 className="text-2xl font-semibold">Enhanced Tool Call Parsing Examples</h2>

        {/* Tool execution block example */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Tool Execution Block Parsing</h3>
          <div className="border rounded p-3" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}>
            <h4 className="font-medium mb-2">Original Agent Response:</h4>
            <pre className="text-sm font-mono whitespace-pre-wrap p-2 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}>
              {sampleToolExecutionText}
            </pre>
          </div>
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Parsing Result:</strong> This text would be parsed to extract semantic_search tool call, 
            create SemanticSearchWidget, and remove the execution markers from the displayed content.
          </div>
        </div>

        {/* Progress indicator example */}
        <div className="space-y-4">
          <h3 className="text-lg font-medium">Progress Indicator Detection</h3>
          <div className="border rounded p-3" style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}>
            <h4 className="font-medium mb-2">Original Agent Response:</h4>
            <pre className="text-sm font-mono whitespace-pre-wrap p-2 rounded" style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}>
              {sampleProgressText}
            </pre>
          </div>
          <div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            <strong>Parsing Result:</strong> This text would be parsed to create a ProgressWidget with spinning icon, 
            and the "🔧 Executing tools..." text would be removed from the displayed content.
          </div>
        </div>
      </div>

      {/* Implementation Notes */}
      <div className="bg-blue-50 rounded-lg p-4" style={{ backgroundColor: 'var(--icui-bg-tertiary)' }}>
        <h3 className="font-medium mb-2">Phase 4.5 Implementation Status</h3>
        <ul className="text-sm space-y-1">
          <li>✅ Enhanced tool call detection with regex pattern matching</li>
          <li>✅ Real-time progress indicators with spinning icons</li>
          <li>✅ Proper tool execution state management</li>
          <li>✅ SemanticSearchWidget for search results (no code highlighting)</li>
          <li>✅ ProgressWidget for "🔧 Executing tools..." indicators</li>
          <li>✅ Collapsible tool execution details by default</li>
          <li>✅ Fixed text-based output rendering</li>
          <li>✅ Widget registry auto-registration</li>
          <li>✅ Tool execution timing and status updates</li>
          <li>✅ Enhanced parsing from actual agent responses</li>
        </ul>
      </div>
    </div>
  );
};

export default ChatPhase45Test; 