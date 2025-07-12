import React, { useState, useRef, useEffect } from "react";
import { Button } from "../ui/button";
import { Trash2, X } from "lucide-react";

interface TerminalProps {
  theme?: "light" | "dark";
  onClear?: () => void;
  className?: string;
}

interface TerminalLine {
  id: string;
  content: string;
  type: 'input' | 'output' | 'error';
  timestamp: Date;
}

const Terminal: React.FC<TerminalProps> = ({
  theme = "light",
  onClear,
  className = "",
}) => {
  const [lines, setLines] = useState<TerminalLine[]>([
    {
      id: "welcome",
      content: "Welcome to iLabors Code Terminal",
      type: "output",
      timestamp: new Date(),
    },
  ]);
  const [currentInput, setCurrentInput] = useState("");
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto-scroll to bottom when new lines are added
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines]);

  const addLine = (content: string, type: 'input' | 'output' | 'error') => {
    const newLine: TerminalLine = {
      id: Date.now().toString(),
      content,
      type,
      timestamp: new Date(),
    };
    setLines(prev => [...prev, newLine]);
  };

  const executeCommand = (command: string) => {
    // Add command to history
    setCommandHistory(prev => [...prev, command]);
    setHistoryIndex(-1);

    // Add input line
    addLine(`$ ${command}`, 'input');

    // Simple command processing
    const cmd = command.trim().toLowerCase();
    
    if (cmd === 'clear') {
      setLines([]);
      return;
    }
    
    if (cmd === 'help') {
      addLine("Available commands:", 'output');
      addLine("  clear - Clear the terminal", 'output');
      addLine("  help - Show this help message", 'output');
      addLine("  echo <text> - Echo the text", 'output');
      addLine("  date - Show current date and time", 'output');
      return;
    }

    if (cmd.startsWith('echo ')) {
      const text = command.slice(5);
      addLine(text, 'output');
      return;
    }

    if (cmd === 'date') {
      addLine(new Date().toString(), 'output');
      return;
    }

    // Default: command not found
    addLine(`Command not found: ${command}`, 'error');
    addLine("Type 'help' for available commands", 'output');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (currentInput.trim()) {
        executeCommand(currentInput.trim());
        setCurrentInput("");
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length > 0) {
        const newIndex = historyIndex + 1;
        if (newIndex < commandHistory.length) {
          setHistoryIndex(newIndex);
          setCurrentInput(commandHistory[commandHistory.length - 1 - newIndex]);
        }
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCurrentInput(commandHistory[commandHistory.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setCurrentInput("");
      }
    }
  };

  const handleClear = () => {
    setLines([]);
    onClear?.();
  };

  const getLineClassName = (type: 'input' | 'output' | 'error') => {
    switch (type) {
      case 'input':
        return 'text-blue-400';
      case 'error':
        return 'text-red-400';
      case 'output':
      default:
        return '';
    }
  };

  const getLineStyle = (type: 'input' | 'output' | 'error') => {
    switch (type) {
      case 'input':
        return { color: 'var(--icui-accent)' };
      case 'error':
        return { color: 'var(--icui-danger)' };
      case 'output':
      default:
        return { color: 'var(--icui-text-primary)' };
    }
  };

  return (
    <div className={`flex flex-col h-full bg-background ${className}`}>
      <div className="flex items-center justify-between p-2 border-b border-border bg-muted/30">
        <span className="text-sm font-medium">Terminal</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          className="h-6 w-6 p-0"
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>
      
      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-2 font-mono text-sm"
        style={{ 
          backgroundColor: 'var(--icui-bg-primary)',
          color: 'var(--icui-text-primary)'
        }}
        onClick={() => inputRef.current?.focus()}
      >
        {lines.map((line) => (
          <div key={line.id} className={`mb-1 ${getLineClassName(line.type)}`} style={getLineStyle(line.type)}>
            {line.content}
          </div>
        ))}
        
        <div className="flex items-center">
          <span className="mr-2" style={{ color: 'var(--icui-accent)' }}>$</span>
          <input
            ref={inputRef}
            type="text"
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent outline-none"
            style={{ color: 'var(--icui-text-primary)' }}
            placeholder="Enter command..."
            autoFocus
          />
        </div>
      </div>
    </div>
  );
};

export default Terminal;
