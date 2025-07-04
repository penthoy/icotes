import React, { useState } from "react";
import { Button } from "./ui/button";
import { ChevronDown, ChevronUp, Plus, X } from "lucide-react";
import XTerminal from "./XTerminal";

interface OutputTerminalPanelProps {
  output: string[];
  errors?: string[];
  isVisible?: boolean;
  toggleVisibility?: () => void;
  theme?: "light" | "dark";
  onClear?: () => void;
}

type TabType = 'output' | 'terminal';

interface Tab {
  id: string;
  type: TabType;
  title: string;
  closable: boolean;
}

const OutputTerminalPanel: React.FC<OutputTerminalPanelProps> = ({
  output = [],
  errors = [],
  isVisible = true,
  toggleVisibility = () => {},
  theme = "light",
  onClear = () => {},
}) => {
  const [isPanelOpen, setIsPanelOpen] = useState(isVisible);
  const [tabs, setTabs] = useState<Tab[]>([
    {
      id: 'terminal-1',
      type: 'terminal',
      title: 'Terminal',
      closable: false
    }
  ]);
  const [activeTabId, setActiveTabId] = useState<string>('terminal-1');

  const handleToggle = () => {
    const newState = !isPanelOpen;
    setIsPanelOpen(newState);
    toggleVisibility?.();
  };

  const addNewTab = (type: TabType) => {
    const newTab: Tab = {
      id: `${type}-${Date.now()}`,
      type,
      title: type === 'terminal' ? 'Terminal' : 'Output',
      closable: true
    };
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(newTab.id);
  };

  const closeTab = (tabId: string) => {
    const tabToClose = tabs.find(tab => tab.id === tabId);
    if (!tabToClose || !tabToClose.closable) return;

    const newTabs = tabs.filter(tab => tab.id !== tabId);
    setTabs(newTabs);
    
    // If we closed the active tab, switch to the first available tab
    if (activeTabId === tabId) {
      setActiveTabId(newTabs[0]?.id || '');
    }
  };

  const activeTab = tabs.find(tab => tab.id === activeTabId);

  const renderOutputTab = () => (
    <div className="h-full overflow-y-auto p-4">
      {errors.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-destructive mb-2">
            Errors:
          </h3>
          {errors.map((error, index) => (
            <div
              key={`error-${index}`}
              className="text-sm font-mono bg-destructive/10 text-destructive p-2 rounded mb-1"
            >
              {error}
            </div>
          ))}
        </div>
      )}

      {output.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-2">Console Output:</h3>
          {output.map((log, index) => (
            <div
              key={`log-${index}`}
              className="text-sm font-mono bg-muted p-2 rounded mb-1"
            >
              {log}
            </div>
          ))}
        </div>
      )}

      {errors.length === 0 && output.length === 0 && (
        <div className="text-center text-muted-foreground py-8">
          No output to display. Run your code to see results here.
        </div>
      )}
    </div>
  );

  const renderTerminalTab = () => (
    <XTerminal theme={theme} onClear={() => {}} />
  );

  const renderTabContent = () => {
    if (!activeTab) return null;
    
    switch (activeTab.type) {
      case 'output':
        return renderOutputTab();
      case 'terminal':
        return renderTerminalTab();
      default:
        return null;
    }
  };

  const getTabClassName = (tabId: string) => {
    const baseClass = "px-3 py-1 text-sm border-b-2 transition-colors flex items-center gap-2 relative group";
    const activeClass = "border-primary text-primary";
    const inactiveClass = "border-transparent text-muted-foreground hover:text-foreground";
    
    return `${baseClass} ${activeTabId === tabId ? activeClass : inactiveClass}`;
  };

  return (
    <div className="w-full bg-background border-t border-border">
      <div className="flex items-center justify-between p-2 bg-muted/30">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleToggle}
            className="p-1 h-8"
          >
            {isPanelOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
            <span className="ml-1">Panel</span>
          </Button>
          {(output.length > 0 || errors.length > 0) && (
            <div className="text-xs text-muted-foreground">
              {errors.length > 0 && (
                <span className="text-destructive mr-3">
                  {errors.length} error(s)
                </span>
              )}
              {output.length > 0 && <span>{output.length} log(s)</span>}
            </div>
          )}
        </div>
      </div>

      {isPanelOpen && (
        <div className="flex flex-col h-full">
          {/* Tab Headers */}
          <div className="flex border-b border-border">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTabId(tab.id)}
                className={getTabClassName(tab.id)}
              >
                <span>{tab.title}</span>
                {tab.closable && (
                  <X
                    className="h-3 w-3 opacity-0 group-hover:opacity-100 hover:bg-muted rounded transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation();
                      closeTab(tab.id);
                    }}
                  />
                )}
              </button>
            ))}
            
            {/* Add New Tab Button */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  // Simple implementation: alternate between terminal and output
                  const hasOutput = tabs.some(tab => tab.type === 'output');
                  addNewTab(hasOutput ? 'terminal' : 'output');
                }}
                className="px-2 py-1 h-8 text-muted-foreground hover:text-foreground"
                title="Add new tab"
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="flex-1 border-b-2 border-transparent"></div>
            
            {activeTab?.type === 'output' && (output.length > 0 || errors.length > 0) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClear}
                className="p-1 h-8 mr-2"
              >
                Clear
              </Button>
            )}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-hidden">
            {renderTabContent()}
          </div>
        </div>
      )}
    </div>
  );
};

export default OutputTerminalPanel;
