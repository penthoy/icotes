import React, { useEffect } from 'react';
import { confirmService, useConfirmRequest } from '../../services/confirmService';

/**
 * ConfirmDialogHost
 *
 * Mount once near the app root. It listens for confirmService requests
 * and renders a centered, theme-integrated modal.
 */
const ConfirmDialogHost: React.FC = () => {
  const req = useConfirmRequest();

  useEffect(() => {
    // Disable background scroll while modal is open
    if (req) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [req]);

  if (!req) return null;

  const { message, title, confirmText = 'Confirm', cancelText = 'Cancel', danger } = req.options;

  return (
    <div
      className="fixed inset-0 z-[11000] flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      onClick={() => confirmService.resolve(false)}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="icui-confirm-title"
        aria-describedby="icui-confirm-message"
        className="rounded-lg shadow-xl w-full max-w-md mx-4"
        style={{ backgroundColor: 'var(--icui-bg-secondary)', color: 'var(--icui-text-primary)', border: '1px solid var(--icui-border)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="px-5 pt-4">
            <h3 id="icui-confirm-title" className="text-lg font-semibold" style={{ color: 'var(--icui-text-primary)' }}>
              {title}
            </h3>
          </div>
        )}
        <div className="px-5 py-4">
          <p id="icui-confirm-message" className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
            {message}
          </p>
        </div>
        <div className="px-5 pb-4 flex justify-end gap-2">
          <button
            className="px-3 py-1.5 rounded text-sm border"
            style={{ borderColor: 'var(--icui-border)', color: 'var(--icui-text-primary)', backgroundColor: 'transparent' }}
            onClick={() => confirmService.resolve(false)}
          >
            {cancelText}
          </button>
          <button
            className="px-3 py-1.5 rounded text-sm"
            style={{
              backgroundColor: danger ? 'var(--icui-text-error)' : 'var(--icui-accent)',
              color: danger ? '#fff' : 'var(--icui-text-primary)'
            }}
            onClick={() => confirmService.resolve(true)}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialogHost;
