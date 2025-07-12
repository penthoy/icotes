import React, { useState } from "react";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import { ChevronDown, ChevronUp, XCircle } from "lucide-react";

interface OutputPanelProps {
  output: string[];
  errors?: string[];
  isVisible?: boolean;
  toggleVisibility?: () => void;
  theme?: "light" | "dark";
  isOpen?: boolean;
  onToggle?: () => void;
  onClear?: () => void;
}

const OutputPanel = ({
  output = [],
  errors = [],
  isVisible = true,
  toggleVisibility = () => {},
  theme = "light",
  isOpen = true,
  onToggle = () => {},
  onClear = () => {},
}: OutputPanelProps) => {
  const [isPanelOpen, setIsPanelOpen] = useState(isVisible ?? isOpen);

  const handleToggle = () => {
    const newState = !isPanelOpen;
    setIsPanelOpen(newState);
    toggleVisibility?.();
    onToggle?.();
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
            <span className="ml-1">Output</span>
          </Button>
          {(output.length > 0 || errors.length > 0) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              className="p-1 h-8"
            >
              <XCircle className="h-4 w-4 mr-1" />
              Clear
            </Button>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          {errors.length > 0 && (
            <span className="text-destructive mr-3">
              {errors.length} error(s)
            </span>
          )}
          {output.length > 0 && <span>{output.length} log(s)</span>}
        </div>
      </div>

      {isPanelOpen && (
        <Card className="rounded-none border-0 shadow-none">
          <CardContent className="p-0">
            <div className="max-h-[200px] overflow-y-auto p-4">
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
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default OutputPanel;
