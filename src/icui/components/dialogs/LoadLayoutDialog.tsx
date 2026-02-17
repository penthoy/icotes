/**
 * Load Layout Dialog
 * Displays available layout presets and allows loading/deleting them
 */

import React, { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { ScrollArea } from '../../../components/ui/scroll-area';
import { layoutConfigService } from '../../services/layoutConfigService';
import { notificationService } from '../../services/notificationService';
import type { ICUILayoutConfig } from '../ICUILayout';

export interface LoadLayoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLayoutLoad: (layout: ICUILayoutConfig, sourcePath: string) => void;
}

interface LayoutListItem {
  name: string;
  path: string;
  metadata?: {
    name?: string;
    description?: string;
    deviceTarget?: string;
  };
  isBuiltIn: boolean;
}

export const LoadLayoutDialog: React.FC<LoadLayoutDialogProps> = ({
  open,
  onOpenChange,
  onLayoutLoad,
}) => {
  const [layouts, setLayouts] = useState<LayoutListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);

  const builtInLayouts = ['H.yaml', 'IDE.yaml', 'mobile.yaml'];

  const loadLayoutList = async () => {
    setLoading(true);
    try {
      const files = await layoutConfigService.listLayouts();
      
      // Load metadata for each layout
      const layoutsWithMeta = await Promise.all(
        files.map(async (file) => {
          try {
            const result = await layoutConfigService.loadFromFile(file.path);
            return {
              name: file.name,
              path: file.path,
              metadata: result.ok ? {
                name: result.layout?.name,
                description: result.layout?.description,
                deviceTarget: result.layout?.deviceTarget,
              } : undefined,
              isBuiltIn: builtInLayouts.includes(file.name),
            };
          } catch {
            return {
              name: file.name,
              path: file.path,
              isBuiltIn: builtInLayouts.includes(file.name),
            };
          }
        })
      );

      setLayouts(layoutsWithMeta);
    } catch (error) {
      console.error('Failed to load layout list:', error);
      notificationService.error('Failed to load layout list');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadLayoutList();
    }
  }, [open]);

  const handleLoadLayout = async (path: string) => {
    try {
      const result = await layoutConfigService.loadFromFile(path);
      
      if (!result.ok) {
        notificationService.error(`Invalid layout: ${result.errors.join(', ')}`);
        return;
      }

      if (result.warnings.length > 0) {
        console.warn('Layout warnings:', result.warnings);
      }

      onLayoutLoad(result.layout!, path);
      notificationService.success('Layout loaded successfully');
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to load layout:', error);
      notificationService.error(`Failed to load layout: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleDeleteLayout = async (path: string, name: string) => {
    if (!confirm(`Delete layout "${name}"?`)) {
      return;
    }

    try {
      await fetch(`/api/files?path=${encodeURIComponent(path)}`, {
        method: 'DELETE',
      });
      
      notificationService.success(`Layout "${name}" deleted`);
      loadLayoutList(); // Refresh list
    } catch (error) {
      console.error('Failed to delete layout:', error);
      notificationService.error('Failed to delete layout');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Load Layout</DialogTitle>
          <DialogDescription>
            Select a layout preset to apply to your workspace.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[300px] w-full rounded border p-4">
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading layouts...</div>
          ) : layouts.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No layouts found</div>
          ) : (
            <div className="space-y-2">
              {layouts.map((layout) => (
                <div
                  key={layout.path}
                  className={`p-3 rounded border cursor-pointer hover:bg-accent transition-colors ${
                    selectedPath === layout.path ? 'bg-accent border-primary' : ''
                  }`}
                  onClick={() => setSelectedPath(layout.path)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium">
                        {layout.metadata?.name || layout.name}
                        {layout.isBuiltIn && (
                          <span className="ml-2 text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                            Built-in
                          </span>
                        )}
                      </div>
                      {layout.metadata?.description && (
                        <div className="text-sm text-muted-foreground mt-1">
                          {layout.metadata.description}
                        </div>
                      )}
                      {layout.metadata?.deviceTarget && (
                        <div className="text-xs text-muted-foreground mt-1">
                          Target: {layout.metadata.deviceTarget}
                        </div>
                      )}
                    </div>
                    {!layout.isBuiltIn && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteLayout(layout.path, layout.metadata?.name || layout.name);
                        }}
                        className="ml-2"
                      >
                        Delete
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => selectedPath && handleLoadLayout(selectedPath)}
            disabled={!selectedPath}
          >
            Load Layout
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
