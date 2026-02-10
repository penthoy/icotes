/**
 * Save Layout Dialog
 * Allows users to save current layout configuration as a named YAML preset
 */

import React, { useState } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../../../components/ui/dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Textarea } from '../../../components/ui/textarea';
import { layoutConfigService } from '../../services/layoutConfigService';
import { notificationService } from '../../services/notificationService';
import type { ICUILayoutConfig } from '../ICUILayout';

export interface SaveLayoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentLayout: ICUILayoutConfig;
}

export const SaveLayoutDialog: React.FC<SaveLayoutDialogProps> = ({
  open,
  onOpenChange,
  currentLayout,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) {
      notificationService.error('Layout name is required');
      return;
    }

    setSaving(true);
    try {
      // Generate layout ID from name
      const layoutId = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      
      // Create layout config with metadata
      const layoutToSave: ICUILayoutConfig = {
        ...currentLayout,
        name: name.trim(),
        id: layoutId,
        description: description.trim() || undefined,
        version: 1,
        deviceTarget: 'desktop',
      };

      // Save to file
      const filePath = `${layoutConfigService.layoutDir}/${layoutId}.yaml`;
      await layoutConfigService.saveToFile(layoutToSave, filePath);

      notificationService.success(`Layout "${name}" saved successfully`);
      onOpenChange(false);
      
      // Reset form
      setName('');
      setDescription('');
    } catch (error) {
      console.error('Failed to save layout:', error);
      notificationService.error(`Failed to save layout: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Save Custom Layout</DialogTitle>
          <DialogDescription>
            Save your current panel arrangement as a reusable layout preset.
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="layout-name">Layout Name *</Label>
            <Input
              id="layout-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Custom Layout"
              disabled={saving}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="layout-description">Description (optional)</Label>
            <Textarea
              id="layout-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your layout configuration..."
              rows={3}
              disabled={saving}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving || !name.trim()}>
            {saving ? 'Saving...' : 'Save Layout'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
