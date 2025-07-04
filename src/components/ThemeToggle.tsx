import React, { useState, useEffect } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "./ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

interface ThemeToggleProps {
  className?: string;
  theme?: "light" | "dark";
  toggleTheme?: () => void;
}

const ThemeToggle = ({
  className = "",
  theme: propTheme,
  toggleTheme: propToggleTheme,
}: ThemeToggleProps) => {
  const [internalTheme, setInternalTheme] = useState<"light" | "dark">(() => {
    // Check if window is defined (client-side)
    if (typeof window !== "undefined") {
      // Check for stored theme preference or system preference
      const storedTheme = localStorage.getItem("theme") as
        | "light"
        | "dark"
        | null;
      if (storedTheme) {
        return storedTheme;
      }

      // Check system preference
      if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
      }
    }

    // Default to light theme
    return "light";
  });

  const theme = propTheme || internalTheme;

  useEffect(() => {
    // Only update if using internal theme (not controlled by parent)
    if (!propTheme) {
      // Update the document class when theme changes
      const root = window.document.documentElement;
      root.classList.remove("light", "dark");
      root.classList.add(theme);

      // Save the theme preference
      localStorage.setItem("theme", theme);
    }
  }, [theme, propTheme]);

  const handleToggleTheme = () => {
    if (propToggleTheme) {
      propToggleTheme();
    } else {
      setInternalTheme(theme === "light" ? "dark" : "light");
    }
  };

  return (
    <div className={`bg-background ${className}`}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggleTheme}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              {theme === "light" ? (
                <Moon className="h-5 w-5" />
              ) : (
                <Sun className="h-5 w-5" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{theme === "light" ? "Dark" : "Light"} mode</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
};

export default ThemeToggle;
