import React, { useCallback, useEffect, useState } from 'react';
import { useChatHistory } from '../../hooks/useChatHistory';
import { configService } from '../../../services/config-service';

interface DebugEntry {
  type: string;
  timestamp: string;
  [key: string]: any;
}

const DebugSidecarPanel: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { activeSessionId } = useChatHistory();
  const [entries, setEntries] = useState<DebugEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState<'minimal' | 'verbose'>('minimal');

  const getBaseUrl = useCallback(async () => {
    try {
      const cfg = await configService.getConfig();
      const base = cfg.api_url || cfg.base_url || '';
      return base.endsWith('/api') ? base.slice(0, -4) : base;
    } catch {
      const base = (window as any).__ICUI_API_URL__ || (import.meta as any).env?.VITE_API_URL || (import.meta as any).env?.VITE_BACKEND_URL || `${window.location.protocol}//${window.location.host}`;
      return base.endsWith('/api') ? base.slice(0, -4) : base;
    }
  }, []);

  const fetchStatus = useCallback(async (sessionId: string) => {
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/debug/status?session_id=${encodeURIComponent(sessionId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    setEnabled(Boolean(json?.data?.enabled));
    setMode((json?.data?.mode || 'minimal') as 'minimal' | 'verbose');
  }, [getBaseUrl]);

  const fetchEntries = useCallback(async (sessionId: string) => {
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/chat/${encodeURIComponent(sessionId)}/debug`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    setEntries(Array.isArray(json?.data) ? json.data : []);
  }, [getBaseUrl]);

  const refresh = useCallback(async () => {
    if (!activeSessionId) return;
    try {
      setIsLoading(true);
      await fetchStatus(activeSessionId);
      await fetchEntries(activeSessionId);
    } catch (error) {
      console.warn('Failed to load debug entries:', error);
      setEntries([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeSessionId, fetchEntries, fetchStatus]);

  const toggleDebug = useCallback(async (nextEnabled: boolean) => {
    if (!activeSessionId) return;
    const base = await getBaseUrl();
    const res = await fetch(`${base}/api/debug/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionId, enabled: nextEnabled, mode })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    setEnabled(Boolean(json?.data?.enabled));
    setMode((json?.data?.mode || mode) as 'minimal' | 'verbose');
  }, [activeSessionId, getBaseUrl, mode]);

  const updateMode = useCallback(async (nextMode: 'minimal' | 'verbose') => {
    setMode(nextMode);
    if (!activeSessionId) return;
    const base = await getBaseUrl();
    await fetch(`${base}/api/debug/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: activeSessionId, enabled, mode: nextMode })
    });
  }, [activeSessionId, getBaseUrl, enabled]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className={`h-full flex flex-col ${className}`} style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)' }}>
      <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--icui-border-subtle)' }}>
        <div className="text-sm font-semibold">Agent Debug</div>
        <div className="flex items-center gap-2 text-xs">
          <select
            value={mode}
            onChange={(e) => updateMode(e.target.value as 'minimal' | 'verbose')}
            className="px-2 py-1 rounded border"
            style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-primary)' }}
          >
            <option value="minimal">minimal</option>
            <option value="verbose">verbose</option>
          </select>
          <button
            onClick={() => toggleDebug(!enabled)}
            className="px-2 py-1 rounded border"
            style={{ backgroundColor: enabled ? 'var(--icui-accent)' : 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)', color: enabled ? '#fff' : 'var(--icui-text-primary)' }}
          >
            {enabled ? 'Disable' : 'Enable'}
          </button>
          <button
            onClick={refresh}
            className="px-2 py-1 rounded border"
            style={{ backgroundColor: 'var(--icui-bg-secondary)', borderColor: 'var(--icui-border-subtle)', color: 'var(--icui-text-primary)' }}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 text-xs">
        {isLoading ? (
          <div style={{ color: 'var(--icui-text-secondary)' }}>Loading…</div>
        ) : entries.length === 0 ? (
          <div style={{ color: 'var(--icui-text-secondary)' }}>No debug entries for this session.</div>
        ) : (
          <div className="space-y-3">
            {entries.map((entry, idx) => (
              <div key={`${entry.type}-${idx}`} className="rounded border p-2" style={{ borderColor: 'var(--icui-border-subtle)', backgroundColor: 'var(--icui-bg-secondary)' }}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold">{entry.type}</span>
                  <span style={{ color: 'var(--icui-text-secondary)' }}>{entry.timestamp}</span>
                </div>
                <pre className="whitespace-pre-wrap" style={{ color: 'var(--icui-text-secondary)' }}>
                  {JSON.stringify(entry, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DebugSidecarPanel;
