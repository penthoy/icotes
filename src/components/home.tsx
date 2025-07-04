import React, { useState } from "react";
import { Sun, Moon, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import CodeEditor from "./CodeEditor";
import OutputPanel from "./OutputPanel";
import ThemeToggle from "./ThemeToggle";

const Home = () => {
  const [code, setCode] = useState<string>(
    '// Write your JavaScript code here\nconsole.log("Hello, world!");',
  );
  const [output, setOutput] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [isOutputVisible, setIsOutputVisible] = useState<boolean>(true);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const handleRunCode = () => {
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
      const result = new Function(code)();

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

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const toggleOutputPanel = () => {
    setIsOutputVisible(!isOutputVisible);
  };

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
        <div className="flex-grow">
          <CodeEditor code={code} setCode={setCode} theme={theme} />
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
