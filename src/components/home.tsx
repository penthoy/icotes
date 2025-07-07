import React, { useState, useEffect, useRef } from "react";
import { Play, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import CodeEditor, { SupportedLanguage } from "./CodeEditor";
import OutputTerminalPanel from "./OutputTerminalPanel";
import { XTerminalRef } from "./XTerminal";
import ThemeToggle from "./ThemeToggle";
import FileTabs, { FileData } from "./FileTabs";
import FileExplorer from "./FileExplorer";
import ResizablePanel from "./ResizablePanel";
import VerticalResizablePanel from "./VerticalResizablePanel";
import { CodeExecutor } from "@/lib/codeExecutor";

// File explorer data structure
interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  isExpanded?: boolean;
}

const Home = () => {
  const [files, setFiles] = useState<FileData[]>([
    {
      id: "default",
      name: "main.py",
      content:
        '# Write your Python code here\nprint("Hello, world!")',
      isModified: false,
    },
  ]);
  
  // File explorer structure
  const [explorerFiles, setExplorerFiles] = useState<FileNode[]>([
    {
      id: "main",
      name: "main.py",
      type: "file",
      path: "/main.py",
    },
  ]);
  
  const [activeFileId, setActiveFileId] = useState<string>("default");
  const [isExplorerVisible, setIsExplorerVisible] = useState<boolean>(true);
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>('python');
  const [output, setOutput] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [isOutputVisible, setIsOutputVisible] = useState<boolean>(true);
  const [codeExecutor] = useState(() => new CodeExecutor());
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    // Check system preference first
    if (typeof window !== "undefined") {
      const storedTheme = localStorage.getItem("theme") as
        | "light"
        | "dark"
        | null;
      if (storedTheme) {
        return storedTheme;
      }
      // Default to dark mode if no system preference is detected
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
      }
    }
    return "dark"; // Default to dark mode
  });

  const terminalRef = useRef<XTerminalRef>({} as XTerminalRef);

  const activeFile = files.find((file) => file.id === activeFileId);

  // Determine language based on file extension
  const getLanguageFromFileName = (fileName: string): SupportedLanguage => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'js':
      case 'jsx':
        return 'javascript';
      case 'py':
        return 'python';
      default:
        return 'python'; // Default to Python
    }
  };

  // Initialize code executor
  useEffect(() => {
    const initializeExecutor = async () => {
      try {
        await codeExecutor.connect();
        console.log('Code executor connected');
      } catch (error) {
        console.warn('Failed to connect to backend:', error);
      }
    };

    initializeExecutor();

    // Cleanup on unmount
    return () => {
      codeExecutor.disconnect();
    };
  }, [codeExecutor]);

  // Update current language when active file changes
  useEffect(() => {
    if (activeFile) {
      setCurrentLanguage(getLanguageFromFileName(activeFile.name));
    }
  }, [activeFile]);

  const handleRunCode = async () => {
    if (!activeFile || isExecuting) return;

    // Clear previous output and errors
    setOutput([]);
    setErrors([]);
    setIsExecuting(true);

    try {
      if (currentLanguage === 'javascript') {
        // JavaScript execution (existing logic for client-side execution)
        const logs: string[] = [];

        // Override console.log to capture outputs
        const originalConsoleLog = console.log;
        console.log = (...args) => {
          logs.push(
            args
              .map((arg) =>
                typeof arg === "object" ? JSON.stringify(arg) : String(arg),
              )
              .join(" "),
          );
          originalConsoleLog(...args);
        };

        // Execute the code
        const result = new Function(activeFile.content)();

        // Restore original console.log
        console.log = originalConsoleLog;

        // Add the result to the output if it's not undefined
        if (result !== undefined) {
          logs.push(`Result: ${result}`);
        }

        setOutput(logs);
      } else {
        // Use backend execution for Python and other languages
        const result = await codeExecutor.executeCode(activeFile.content, currentLanguage);
        
        setOutput(result.output);
        setErrors(result.errors);
        
        // Add execution time info
        if (result.execution_time > 0) {
          setOutput(prev => [...prev, `Execution time: ${(result.execution_time * 1000).toFixed(2)}ms`]);
        }
      }

      // Make sure output panel is visible
      if (!isOutputVisible) {
        setIsOutputVisible(true);
      }
    } catch (error) {
      setErrors([`Error: ${error instanceof Error ? error.message : String(error)}`]);

      // Make sure output panel is visible on error
      if (!isOutputVisible) {
        setIsOutputVisible(true);
      }
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCodeChange = (newCode: string) => {
    if (!activeFile) return;

    setFiles((prevFiles) =>
      prevFiles.map((file) =>
        file.id === activeFileId
          ? { ...file, content: newCode, isModified: file.content !== newCode }
          : file,
      ),
    );
  };

  const handleFileTabSelect = (fileId: string) => {
    setActiveFileId(fileId);
  };

  const handleFileClose = (fileId: string) => {
    if (files.length === 1) return; // Don't close the last file

    const fileIndex = files.findIndex((file) => file.id === fileId);
    if (fileIndex === -1) return;

    const newFiles = files.filter((file) => file.id !== fileId);
    setFiles(newFiles);

    // If we closed the active file, switch to the adjacent file
    if (activeFileId === fileId) {
      const newActiveIndex = fileIndex > 0 ? fileIndex - 1 : 0;
      setActiveFileId(newFiles[newActiveIndex]?.id || newFiles[0]?.id);
    }
  };

  // File explorer handlers (placeholder implementations)
  const handleFileSelect = (filePath: string) => {
    // TODO: Load file content and add to tabs
    console.log("File selected:", filePath);
  };

  const handleFileCreate = (folderPath: string) => {
    // TODO: Create new file
    console.log("Create file in:", folderPath);
  };

  const handleFolderCreate = (folderPath: string) => {
    // TODO: Create new folder
    console.log("Create folder in:", folderPath);
  };

  const handleFileDelete = (filePath: string) => {
    // TODO: Delete file
    console.log("Delete file:", filePath);
  };

  const handleFileRename = (oldPath: string, newName: string) => {
    // TODO: Rename file
    console.log("Rename file:", oldPath, "to", newName);
  };

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const toggleOutputPanel = () => {
    setIsOutputVisible(!isOutputVisible);
  };

  const handleTerminalResize = () => {
    // Add a small delay to allow the panel to resize before fitting the terminal
    setTimeout(() => {
      if (terminalRef.current) {
        terminalRef.current.fit();
      }
    }, 50);
  };

  // Apply theme to document on mount and theme change
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <div className={`h-screen w-screen flex flex-col font-sans ${theme}`}>
      {/* Top bar */}
      <header className="p-4 flex justify-between items-center border-b flex-shrink-0">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExplorerVisible(!isExplorerVisible)}
            className="h-8 w-8 p-0"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-xl font-bold">iLabors Code</h1>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
          <Button
            onClick={handleRunCode}
            disabled={isExecuting}
            className="bg-green-600 hover:bg-green-700 text-white disabled:opacity-50"
          >
            <Play className="mr-2 h-4 w-4" />
            {isExecuting ? 'Running...' : 'Run'}
          </Button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top section (Editor and optional File Explorer) */}
        <div className="flex-1 flex overflow-hidden">
          {isExplorerVisible && (
            <ResizablePanel
              initialWidth={250}
              minWidth={200}
              maxWidth={500}
            >
              <FileExplorer
                files={explorerFiles}
                onFileSelect={handleFileSelect}
                onFileCreate={handleFileCreate}
                onFolderCreate={handleFolderCreate}
                onFileDelete={handleFileDelete}
                onFileRename={handleFileRename}
              />
            </ResizablePanel>
          )}
          <div className="flex-1 flex flex-col min-w-0">
            <FileTabs
              files={files}
              activeFileId={activeFileId}
              onFileSelect={handleFileTabSelect}
              onFileClose={handleFileClose}
              onNewFile={() => { /* TODO */ }}
            />
            <div className="flex-1 relative">
              {activeFile && (
                <CodeEditor
                  code={activeFile.content}
                  language={currentLanguage}
                  onCodeChange={handleCodeChange}
                  theme={theme}
                />
              )}
            </div>
          </div>
        </div>

        {/* Bottom section (Output/Terminal) */}
        {isOutputVisible && (
          <VerticalResizablePanel
            initialHeight={300}
            minHeight={100}
            maxHeight={600}
            onResize={(height) => terminalRef.current?.fit()}
          >
            <OutputTerminalPanel
              ref={terminalRef}
              output={output}
              errors={errors}
              theme={theme}
              onClear={() => {
                setOutput([]);
                setErrors([]);
              }}
            />
          </VerticalResizablePanel>
        )}
      </main>
    </div>
  );
};

export default Home;
