/**
 * Chat Phase 1 & 2 Integration Test
 * 
 * Tests the implemented features from Phase 1 and Phase 2:
 * - Streaming message support
 * - Tool call widget rendering
 * - Widget registry system
 * - Typing indicators
 * - Enhanced search functionality
 * - Session CRUD operations
 */

import React, { useState, useEffect } from 'react';
import ICUIChat from '../../src/icui/components/panels/ICUIChat';
import { registerWidget, getWidgetForTool, WidgetConfig } from '../../src/icui/services/widgetRegistry';
import { ToolCallData } from '../../src/icui/components/chat/ToolCallWidget';

// Mock tool widget for testing
const MockFileEditWidget: React.FC<{ toolCall: ToolCallData; className?: string; expandable?: boolean; defaultExpanded?: boolean }> = ({ 
  toolCall, 
  className = '',
  defaultExpanded = false 
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  
  return (
    <div 
      className={`border rounded p-2 mb-2 ${className}`}
      style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)' }}
    >
      <div 
        className="flex items-center gap-2 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <span>🔧</span>
        <span className="font-medium">Mock File Edit Tool</span>
        <span className="text-xs opacity-70">({toolCall.status})</span>
      </div>
      {expanded && (
        <div className="mt-2 text-sm opacity-80">
          <div>Tool ID: {toolCall.id}</div>
          <div>Input: {JSON.stringify(toolCall.input)}</div>
          <div>Output: {JSON.stringify(toolCall.output)}</div>
        </div>
      )}
    </div>
  );
};

const ChatPhase12Test: React.FC = () => {
  const [testResults, setTestResults] = useState<{ [key: string]: boolean }>({});
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Register a mock widget for testing
    const widgetConfig: WidgetConfig = {
      toolName: 'file_edit',
      component: MockFileEditWidget as any,
      category: 'file',
      priority: 1
    };
    
    registerWidget(widgetConfig);
    
    // Test widget registry
    const widget = getWidgetForTool('file_edit');
    const defaultWidget = getWidgetForTool('unknown_tool');
    
    setTestResults(prev => ({
      ...prev,
      'widget_registry_custom': widget === MockFileEditWidget,
      'widget_registry_default': defaultWidget !== MockFileEditWidget
    }));
    
    setIsReady(true);
  }, []);

  const runTests = () => {
    const results: { [key: string]: boolean } = {};
    
    // Test 1: Widget registry functionality
    try {
      const customWidget = getWidgetForTool('file_edit');
      const defaultWidget = getWidgetForTool('nonexistent_tool');
      results['widget_registry'] = customWidget !== defaultWidget;
    } catch (error) {
      results['widget_registry'] = false;
    }
    
    // Test 2: Chat component renders
    try {
      const chatElement = document.querySelector('.icui-chat');
      results['chat_component_rendered'] = !!chatElement;
    } catch (error) {
      results['chat_component_rendered'] = false;
    }
    
    // Test 3: Search functionality
    try {
      // Simulate Ctrl+F
      const event = new KeyboardEvent('keydown', { 
        key: 'f', 
        ctrlKey: true, 
        bubbles: true 
      });
      document.dispatchEvent(event);
      
      // Check if search UI appeared (basic check)
      setTimeout(() => {
        const searchInput = document.querySelector('input[placeholder*="Search"]');
        setTestResults(prev => ({
          ...prev,
          'search_functionality': !!searchInput
        }));
      }, 100);
    } catch (error) {
      results['search_functionality'] = false;
    }
    
    setTestResults(prev => ({ ...prev, ...results }));
  };

  if (!isReady) {
    return <div>Loading tests...</div>;
  }

  return (
    <div className="p-4" style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      <h1 className="text-2xl font-bold mb-4">Chat Phase 1 & 2 Integration Test</h1>
      
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Test Results</h2>
        <div className="space-y-2">
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
          onClick={runTests}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Run Tests
        </button>
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Feature Tests</h2>
        <div className="space-y-4">
          <div>
            <h3 className="font-medium mb-1">1. Streaming & Typing Indicators</h3>
            <p className="text-sm opacity-80">Send a message to test streaming responses and typing indicators</p>
          </div>
          
          <div>
            <h3 className="font-medium mb-1">2. Tool Call Widgets</h3>
            <p className="text-sm opacity-80">Messages with tool calls should render interactive widgets</p>
          </div>
          
          <div>
            <h3 className="font-medium mb-1">3. Enhanced Search</h3>
            <p className="text-sm opacity-80">Press Ctrl+F to open search with regex/case-sensitive options</p>
          </div>
          
          <div>
            <h3 className="font-medium mb-1">4. Session Management</h3>
            <p className="text-sm opacity-80">Test creating/switching between chat sessions</p>
          </div>
        </div>
      </div>

      <div className="border rounded" style={{ borderColor: 'var(--icui-border-subtle)' }}>
        <div className="p-2 border-b" style={{ borderColor: 'var(--icui-border-subtle)' }}>
          <h3 className="font-medium">Live Chat Test</h3>
        </div>
        <div style={{ height: '400px' }}>
          <ICUIChat className="h-full" />
        </div>
      </div>
    </div>
  );
};

export default ChatPhase12Test; 