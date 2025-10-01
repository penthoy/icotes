import React, { useEffect, useState } from 'react';
import { promptService, usePromptRequest } from '../../services/promptService';

const PromptDialogHost: React.FC = () => {
  const req = usePromptRequest();
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (req) {
      setValue(req.options.initialValue ?? '');
      setError(null);
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = prev; };
    }
  }, [req]);

  if (!req) return null;

  const { title, message, placeholder, multiline, password, confirmText = 'OK', cancelText = 'Cancel', validate } = req.options;

  const onConfirm = () => {
    const maybeErr = validate ? validate(value) : null;
    if (maybeErr) { setError(maybeErr); return; }
    promptService.resolve(value);
  };

  const onCancel = () => promptService.resolve(null);

  return (
    <div className="fixed inset-0 z-[11000] flex items-center justify-center" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} onClick={onCancel}>
      <div className="rounded-lg shadow-xl w-full max-w-md mx-4" style={{ backgroundColor: 'var(--icui-bg-secondary)', color: 'var(--icui-text-primary)', border: '1px solid var(--icui-border)' }} onClick={(e) => e.stopPropagation()}>
        {title && (
          <div className="px-5 pt-4">
            <h3 className="text-lg font-semibold" style={{ color: 'var(--icui-text-primary)' }}>{title}</h3>
          </div>
        )}
        <div className="px-5 py-4 space-y-3">
          {message && <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>{message}</p>}
          {multiline ? (
            <textarea
              className="w-full rounded px-3 py-2 text-sm"
              style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)', border: '1px solid var(--icui-border)' }}
              placeholder={placeholder}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              rows={5}
              autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) onConfirm(); if (e.key === 'Escape') onCancel(); }}
            />
          ) : (
            <input
              className="w-full rounded px-3 py-2 text-sm"
              style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)', border: '1px solid var(--icui-border)' }}
              placeholder={placeholder}
              type={password ? 'password' : 'text'}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter') onConfirm(); if (e.key === 'Escape') onCancel(); }}
            />
          )}
          {error && <div className="text-xs" style={{ color: 'var(--icui-text-error)' }}>{error}</div>}
        </div>
        <div className="px-5 pb-4 flex justify-end gap-2">
          <button className="px-3 py-1.5 rounded text-sm border" style={{ borderColor: 'var(--icui-border)', color: 'var(--icui-text-primary)', backgroundColor: 'transparent' }} onClick={onCancel}>
            {cancelText}
          </button>
          <button className="px-3 py-1.5 rounded text-sm" style={{ backgroundColor: 'var(--icui-accent)', color: 'var(--icui-text-primary)' }} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PromptDialogHost;
