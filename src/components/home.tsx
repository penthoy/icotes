import React, { useState, useEffect } from "react";
import { Play, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import CodeEditor, { SupportedLanguage } from "./CodeEditor";
import OutputTerminalPanel from "./OutputTerminalPanel";
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
    const newFiles = files.filter((file) => file.id !== fileId);
    setFiles(newFiles);

    // If closing the active file, switch to another file
    if (fileId === activeFileId) {
      const newActiveIndex = fileIndex > 0 ? fileIndex - 1 : 0;
      setActiveFileId(newFiles[newActiveIndex]?.id || newFiles[0]?.id);
    }
  };

  const handleNewFile = () => {
    const newFileId = `file-${Date.now()}`;
    const fileName = `untitled-${files.length}.py`;
    const newFile: FileData = {
      id: newFileId,
      name: fileName,
      content: '# New Python file\nprint("Hello from new file!")',
      isModified: false,
    };

    setFiles((prevFiles) => [...prevFiles, newFile]);
    setActiveFileId(newFileId);
    
    // Also add to explorer
    const newExplorerNode: FileNode = {
      id: newFileId,
      name: fileName,
      type: "file",
      path: `/${fileName}`,
    };
    setExplorerFiles((prevFiles) => [...prevFiles, newExplorerNode]);
  };

  // File explorer handlers
  const handleFileSelect = (filePath: string) => {
    // Find the file in our files array by path
    const file = files.find(f => `/${f.name}` === filePath);
    if (file) {
      setActiveFileId(file.id);
    }
  };

  const handleFileCreate = (folderPath: string) => {
    handleNewFile();
  };

  const handleFolderCreate = (folderPath: string) => {
    // TODO: Implement folder creation functionality
    // For now, we'll just create a simple folder structure
    // This can be expanded later for more complex folder management
  };

  const handleFileDelete = (filePath: string) => {
    // Find and remove the file
    const fileToDelete = files.find(f => `/${f.name}` === filePath);
    if (fileToDelete) {
      handleFileClose(fileToDelete.id);
      // Remove from explorer too
      setExplorerFiles(prev => prev.filter(f => f.path !== filePath));
    }
  };

  const handleFileRename = (oldPath: string, newName: string) => {
    // TODO: Implement file renaming functionality
  };

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const toggleOutputPanel = () => {
    setIsOutputVisible(!isOutputVisible);
  };

  // Apply theme to document on mount and theme change
  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <div
      className={`h-screen flex flex-col ${theme === "dark" ? "bg-gray-900 text-white" : "bg-white text-gray-900"}`}
    >
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

      <main className="flex-1 flex overflow-hidden">
        {isExplorerVisible && (
          <ResizablePanel initialWidth={240} minWidth={180} maxWidth={400}>
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
        
        <div className="flex-1 flex flex-col overflow-hidden">
          <FileTabs
            files={files}
            activeFileId={activeFileId}
            onFileSelect={handleFileTabSelect}
            onFileClose={handleFileClose}
            onNewFile={handleNewFile}
          />
          <div className="flex-1 overflow-hidden">
            <CodeEditor
              code={activeFile?.content || ""}
              onCodeChange={handleCodeChange}
              theme={theme}
              language={currentLanguage}
            />
          </div>
          
          {isOutputVisible && (
            <VerticalResizablePanel
              initialHeight={300}
              minHeight={100}
              maxHeight={600}
              className="border-t border-border flex-shrink-0"
            >
              <OutputTerminalPanel
                output={output}
                errors={errors}
                isVisible={isOutputVisible}
                toggleVisibility={toggleOutputPanel}
                theme={theme}
                onClear={() => {
                  setOutput([]);
                  setErrors([]);
                }}
              />
            </VerticalResizablePanel>
          )}
        </div>
      </main>
    </div>
  );
};

export default Home;
