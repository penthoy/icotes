import React from "react";
import { X } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "@/lib/utils";

interface FileTabProps {
  fileName: string;
  isActive: boolean;
  isModified: boolean;
  onClick: () => void;
  onClose: () => void;
}

const FileTab = ({
  fileName = "untitled.js",
  isActive = false,
  isModified = false,
  onClick = () => {},
  onClose = () => {},
}: FileTabProps) => {
  const handleClose = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClose();
  };

  return (
    <div className="bg-background">
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2 border-r border-border cursor-pointer hover:bg-muted/50 transition-colors",
          isActive && "bg-muted/20 border-b-2 border-b-primary",
          !isActive && "bg-muted/50",
        )}
        onClick={onClick}
      >
        <span className="text-sm font-medium truncate max-w-[120px]">
          {fileName}
          {isModified && <span className="ml-1 text-muted-foreground">•</span>}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-4 w-4 p-0 hover:bg-muted-foreground/20"
          onClick={handleClose}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
};

export default FileTab;
