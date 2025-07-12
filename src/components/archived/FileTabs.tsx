import React from "react";
import { Plus } from "lucide-react";
import { Button } from "../ui/button";
import FileTab from "./FileTab";

export interface FileData {
  id: string;
  name: string;
  content: string;
  isModified: boolean;
}

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
