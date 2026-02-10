/**
 * Mobile Layout Settings Dialog
 * Allows users to configure which panels appear in the mobile tab bar and their order
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Checkbox } from '../../../components/ui/checkbox';

export interface MobilePanelConfig {
  id: string;
  type: string;
  title: string;
  icon: string;
  enabled: boolean;
}

export interface MobileLayoutSettingsDialogProps {
  open: boolean;
  onClose: () => void;
  availablePanels: MobilePanelConfig[];
  onSave: (panels: MobilePanelConfig[]) => void;
}

export const MobileLayoutSettingsDialog: React.FC<MobileLayoutSettingsDialogProps> = ({
  open,
  onClose,
  availablePanels,
  onSave,
}) => {
  const [panels, setPanels] = useState<MobilePanelConfig[]>(availablePanels);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [touchStartY, setTouchStartY] = useState<number | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Keep internal state in sync with props (availablePanels loads async in parent).
  useEffect(() => {
    if (open) {
      setPanels(availablePanels);
    }
  }, [availablePanels, open]);

  const handleToggle = useCallback((index: number) => {
    setPanels(prev => {
      const newPanels = [...prev];
      newPanels[index] = { ...newPanels[index], enabled: !newPanels[index].enabled };
      return newPanels;
    });
  }, []);

  // Mouse drag handlers
  const handleDragStart = useCallback((e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    setPanels(prev => {
      const newPanels = [...prev];
      const draggedItem = newPanels[draggedIndex];
      newPanels.splice(draggedIndex, 1);
      newPanels.splice(index, 0, draggedItem);
      return newPanels;
    });
    setDraggedIndex(index);
  }, [draggedIndex]);

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null);
  }, []);

  // Touch drag handlers for mobile
  const handleTouchStart = useCallback((e: React.TouchEvent, index: number) => {
    // Only allow drag from the drag handle
    const touch = e.touches[0];
    const target = e.target as HTMLElement;
    
    // Check if touch started on drag handle area
    if (!target.closest('[data-drag-handle]')) {
      return; // Allow normal scrolling
    }
    
    setTouchStartY(touch.clientY);
    setDraggedIndex(index);
    // Prevent scrolling while dragging from handle
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (draggedIndex === null || touchStartY === null) return;
    
    // Prevent default scrolling
    e.preventDefault();
    
    const touch = e.touches[0];
    const element = document.elementFromPoint(touch.clientX, touch.clientY);
    
    if (element) {
      // Find the panel item element
      let panelElement = element.closest('[data-panel-index]');
      if (panelElement) {
        const targetIndex = parseInt(panelElement.getAttribute('data-panel-index') || '0');
        
        if (targetIndex !== draggedIndex && targetIndex !== hoveredIndex) {
          setHoveredIndex(targetIndex);
          
          setPanels(prev => {
            const newPanels = [...prev];
            const draggedItem = newPanels[draggedIndex];
            newPanels.splice(draggedIndex, 1);
            newPanels.splice(targetIndex, 0, draggedItem);
            return newPanels;
          });
          setDraggedIndex(targetIndex);
        }
      }
    }
  }, [draggedIndex, touchStartY, hoveredIndex]);

  const handleTouchEnd = useCallback(() => {
    setDraggedIndex(null);
    setTouchStartY(null);
    setHoveredIndex(null);
  }, []);

  const handleSave = useCallback(() => {
    onSave(panels);
    onClose();
  }, [panels, onSave, onClose]);

  const handleCancel = useCallback(() => {
    setPanels(availablePanels); // Reset to original
    onClose();
  }, [availablePanels, onClose]);

  const enabledCount = panels.filter(p => p.enabled).length;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md h-[95vh] flex flex-col p-0 gap-0 sm:h-auto">
        <DialogHeader className="px-6 pt-6 pb-4 shrink-0">
          <DialogTitle>Mobile Layout Settings</DialogTitle>
          <p className="text-sm text-muted-foreground mt-2">
            Configure which panels appear in the mobile tab bar and their order.
            Drag to reorder, uncheck to hide.
          </p>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto px-6 space-y-2 min-h-0">{panels.map((panel, index) => (
            <div
              key={panel.id}
              data-panel-index={index}
              className={`
                flex items-center gap-3 p-3 rounded-md border
                transition-all duration-200
                ${draggedIndex === index ? 'opacity-50 scale-95' : 'opacity-100 scale-100'}
                ${panel.enabled ? 'bg-secondary/50' : 'bg-muted/30'}
                hover:border-primary/50
              `}
              style={{
                backgroundColor: panel.enabled ? 'var(--icui-bg-secondary)' : 'var(--icui-bg-primary)',
                borderColor: 'var(--icui-border)',
              }}
            >
              {/* Drag Handle - Wide touch target for mobile */}
              <div 
                data-drag-handle="true"
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
                onTouchStart={(e) => handleTouchStart(e, index)}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
                className="flex items-center justify-center cursor-grab active:cursor-grabbing shrink-0"
                style={{
                  width: '48px',
                  height: '48px',
                  marginLeft: '-12px',
                  touchAction: 'none',
                }}
              >
                <div className="text-muted-foreground">
                  <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                    <circle cx="4" cy="4" r="1.5" />
                    <circle cx="4" cy="8" r="1.5" />
                    <circle cx="4" cy="12" r="1.5" />
                    <circle cx="12" cy="4" r="1.5" />
                    <circle cx="12" cy="8" r="1.5" />
                    <circle cx="12" cy="12" r="1.5" />
                  </svg>
                </div>
              </div>

              {/* Checkbox */}
              <Checkbox
                checked={panel.enabled}
                onCheckedChange={() => handleToggle(index)}
                className="shrink-0"
              />

              {/* Panel Icon */}
              <span className="text-2xl shrink-0">{panel.icon}</span>

              {/* Panel Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm" style={{ color: 'var(--icui-text-primary)' }}>
                  {panel.title}
                </div>
                <div className="text-xs text-muted-foreground">
                  {panel.type}
                </div>
              </div>

              {/* Order indicator */}
              <div className="text-xs text-muted-foreground font-mono shrink-0">
                #{index + 1}
              </div>
            </div>
          ))}
        </div>

        <DialogFooter className="flex items-center justify-between px-6 py-4 border-t shrink-0">
          <div className="text-sm text-muted-foreground">
            {enabledCount} of {panels.length} panels enabled
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              Save Settings
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
