import React, { useState } from "react";
import { Button } from "./ui/button";
import { ChevronDown, ChevronUp } from "lucide-react";
import Terminal from "./Terminal";

interface OutputTerminalPanelProps {
  output: string[];
  errors?: string[];
  isVisible?: boolean;
  toggleVisibility?: () => void;
  theme?: "light" | "dark";
  onClear?: () => void;
}

type TabType = 'output' | 'terminal';

const OutputTerminalPanel: React.FC<OutputTerminalPanelProps> = ({
  output = [],
  errors = [],
  isVisible = true,
  toggleVisibility = () => {},
  theme = "light",
  onClear = () => {},
}) => {
  const [isPanelOpen, setIsPanelOpen] = useState(isVisible);
  const [activeTab, setActiveTab] = useState<TabType>('output');

  const handleToggle = () => {
    const newState = !isPanelOpen;
    setIsPanelOpen(newState);
    toggleVisibility?.();
  };

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
    <Terminal theme={theme} onClear={() => {}} />
  );

  const getTabClassName = (tab: TabType) => {
    const baseClass = "px-3 py-1 text-sm border-b-2 transition-colors";
    const activeClass = "border-primary text-primary";
    const inactiveClass = "border-transparent text-muted-foreground hover:text-foreground";
    
    return `${baseClass} ${activeTab === tab ? activeClass : inactiveClass}`;
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
        <div className="flex flex-col h-[300px]">
          {/* Tab Headers */}
          <div className="flex border-b border-border">
            <button
              onClick={() => setActiveTab('output')}
              className={getTabClassName('output')}
            >
              Output
            </button>
            <button
              onClick={() => setActiveTab('terminal')}
              className={getTabClassName('terminal')}
            >
              Terminal
            </button>
            <div className="flex-1 border-b-2 border-transparent"></div>
            {activeTab === 'output' && (output.length > 0 || errors.length > 0) && (
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
            {activeTab === 'output' ? renderOutputTab() : renderTerminalTab()}
          </div>
        </div>
      )}
    </div>
  );
};

export default OutputTerminalPanel;
