import React, { useState, useEffect } from "react";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import CodeEditor from "./CodeEditor";
import OutputPanel from "./OutputPanel";
import ThemeToggle from "./ThemeToggle";
import FileTabs, { FileData } from "./FileTabs";

const Home = () => {
  const [files, setFiles] = useState<FileData[]>([
    {
      id: "default",
      name: "main.js",
      content:
        '// Write your JavaScript code here\nconsole.log("Hello, world!");',
      isModified: false,
    },
  ]);
  const [activeFileId, setActiveFileId] = useState<string>("default");
  const [output, setOutput] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [isOutputVisible, setIsOutputVisible] = useState<boolean>(true);
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

  const handleRunCode = () => {
    if (!activeFile) return;

    // Clear previous output and errors
    setOutput([]);
    setErrors([]);

    try {
      // Create a new array to capture console.log outputs
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

      // Make sure output panel is visible
      if (!isOutputVisible) {
        setIsOutputVisible(true);
      }
    } catch (error) {
      setErrors([`Error: ${error.message}`]);

      // Make sure output panel is visible on error
      if (!isOutputVisible) {
        setIsOutputVisible(true);
      }
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

  const handleFileSelect = (fileId: string) => {
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
    const newFile: FileData = {
      id: newFileId,
      name: `untitled-${files.length}.js`,
      content: '// New file\nconsole.log("Hello from new file!");',
      isModified: false,
    };

    setFiles((prevFiles) => [...prevFiles, newFile]);
    setActiveFileId(newFileId);
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
      className={`min-h-screen flex flex-col ${theme === "dark" ? "bg-gray-900 text-white" : "bg-white text-gray-900"}`}
    >
      <header className="p-4 flex justify-between items-center border-b">
        <h1 className="text-xl font-bold">JavaScript Code Editor</h1>
        <div className="flex items-center gap-2">
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
          <Button
            onClick={handleRunCode}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Play className="mr-2 h-4 w-4" />
            Run
          </Button>
        </div>
      </header>

      <main className="flex-grow flex flex-col">
        <FileTabs
          files={files}
          activeFileId={activeFileId}
          onFileSelect={handleFileSelect}
          onFileClose={handleFileClose}
          onNewFile={handleNewFile}
        />
        <div className="flex-grow">
          <CodeEditor
            code={activeFile?.content || ""}
            onCodeChange={handleCodeChange}
            theme={theme}
          />
        </div>

        <OutputPanel
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
      </main>
    </div>
  );
};

export default Home;
