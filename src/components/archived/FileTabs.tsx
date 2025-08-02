import React from "react";
import { Plus } from "lucide-react";
import { X } from "lucide-react";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

export interface FileData {
  id: string;
  name: string;
  content: string;
  isModified: boolean;
}

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

interface FileTabsProps {
  files: FileData[];
  activeFileId: string | null;
  onFileSelect: (fileId: string) => void;
  onFileClose: (fileId: string) => void;
  onNewFile: () => void;
}

const FileTabs = ({
  files = [
    {
      id: "default",
      name: "main.py",
      content:
        '# Write your Python code here\nprint("Hello, world!")',
      isModified: false,
    },
  ],
  activeFileId = "default",
  onFileSelect = () => {},
  onFileClose = () => {},
  onNewFile = () => {},
}: FileTabsProps) => {
  return (
    <div className="bg-background border-b border-border">
      <div className="flex items-center">
        <div className="flex items-center overflow-x-auto">
          {files.map((file) => (
            <FileTab
              key={file.id}
              fileName={file.name}
              isActive={file.id === activeFileId}
              isModified={file.isModified}
              onClick={() => onFileSelect(file.id)}
              onClose={() => onFileClose(file.id)}
            />
          ))}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="ml-2 h-8 w-8 p-0 flex-shrink-0"
          onClick={onNewFile}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

export default FileTabs;
