/**
 * Reset Layout Confirmation Dialog
 * Confirms before resetting layout to factory defaults
 */

import React from 'react';

export interface ResetLayoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  layoutName?: string;
}

export const ResetLayoutDialog: React.FC<ResetLayoutDialogProps> = ({
  open,
  onOpenChange,
  onConfirm,
  layoutName = 'H Layout',
}) => {
  if (!open) return null;

  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
      }}
      onClick={handleCancel}
    >
      <div
        className="rounded-lg shadow-xl max-w-md w-full mx-4"
        style={{
          backgroundColor: 'var(--icui-bg-primary)',
          border: '1px solid var(--icui-border)',
          padding: '24px',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          className="text-xl font-semibold mb-4"
          style={{ color: 'var(--icui-text-primary)' }}
        >
          Reset Layout?
        </h2>

        <p
          className="mb-6"
          style={{ color: 'var(--icui-text-secondary)', lineHeight: '1.6' }}
        >
          This will reset your current layout to the factory default <strong>{layoutName}</strong>.
          Any custom divider positions and panel arrangements will be lost.
        </p>

        <div className="flex justify-end gap-3">
          <button
            onClick={handleCancel}
            className="px-4 py-2 rounded transition-colors"
            style={{
              backgroundColor: 'var(--icui-bg-secondary)',
              color: 'var(--icui-text-primary)',
              border: '1px solid var(--icui-border)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 rounded transition-colors"
            style={{
              backgroundColor: 'var(--icui-accent)',
              color: 'white',
              border: 'none',
            }}
          >
            Reset Layout
          </button>
        </div>
      </div>
    </div>
  );
};
