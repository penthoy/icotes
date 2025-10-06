import React, { useEffect, useState, useCallback } from 'react';
import { backendService } from '../../services';
import { promptService } from '../../services/promptService';
import { notificationService } from '../../services/notificationService';

interface Credential {
  id: string;
  name: string;
  host: string;
  port: number;
  username?: string;
  auth?: 'password' | 'privateKey' | 'agent';
  privateKeyId?: string;
  defaultPath?: string;
}

// Set to false to silence hop debug logs
const DEBUG_HOP = true;

const logHop = (...args: any[]) => { if (DEBUG_HOP) { // eslint-disable-next-line no-console
  console.debug('[HopUI]', ...args); } };

const ICUIHop: React.FC<{ className?: string }> = ({ className = '' }) => {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<any>(null);
  const [sessions, setSessions] = useState<any[]>([]);  // All active sessions
  const [newCred, setNewCred] = useState<Partial<Credential>>({ port: 22, auth: 'password' });
  const [uploadedKeyId, setUploadedKeyId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCred, setEditCred] = useState<Partial<Credential>>({});
  const [showAddForm, setShowAddForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [creds, status, allSessions] = await Promise.all([
        (backendService as any).listHopCredentials?.(),
        (backendService as any).getHopStatus?.(),
        (backendService as any).listHopSessions?.().catch(() => []),
      ]);
      if (Array.isArray(creds)) setCredentials(creds);
      setSession(status || null);
      if (Array.isArray(allSessions)) {
        setSessions(allSessions);
      }
      logHop('load() complete', { status, sessions: allSessions, credsCount: creds?.length });
    } catch (e: any) {
      setError(e?.message || 'Failed to load hop data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Subscribe to hop websocket topics for realtime updates
    (backendService as any).notify?.('subscribe', { topics: ['hop.*'] }).catch(() => {/* ignore */});
    const onHop = (s: any) => { logHop('event: hop_status direct', s); setSession(s); };
    const onHopEvent = (evt: any) => {
      const name = evt?.event || '';
      logHop('event: hop_event', name, evt);
      if (name.startsWith('hop.credentials.')) {
        load();
      }
      if (name === 'hop.status') {
        setSession(evt?.data);
      }
      if (name === 'hop.sessions') {
        // Update session list when it changes
        const sessions = evt?.data?.sessions;
        if (Array.isArray(sessions)) {
          setSessions(sessions);
        }
      }
    };
    (backendService as any).on?.('hop_status', onHop);
    (backendService as any).on?.('hop_event', onHopEvent);
    (backendService as any).on?.('hop_credentials_updated', load);
    return () => {
      (backendService as any).notify?.('unsubscribe', { topics: ['hop.*'] }).catch(() => {/* ignore */});
      (backendService as any).off?.('hop_status', onHop);
      (backendService as any).off?.('hop_event', onHopEvent);
      (backendService as any).off?.('hop_credentials_updated', load);
    };
  }, [load]);

  const handleConnect = async (cred: Credential) => {
    try {
      setLoading(true);
      let opts: any = {};
      if (cred.auth === 'password') {
  const pw = await promptService.prompt({ title: 'SSH Password', message: `Password for ${cred.username || ''}@${cred.host}`, placeholder: 'Enter password', password: true });
        if (pw === null) { setLoading(false); return; }
        opts.password = pw || undefined;
      }
      notificationService.info(`Connecting to ${cred.username ? cred.username + '@' : ''}${cred.host}...`);
      const session = await (backendService as any).connectHop?.(cred.id, opts);
      logHop('handleConnect result', { credId: cred.id, session });
      if (session?.status === 'connected' || session?.connected) {
        notificationService.success(`Connected to ${cred.username ? cred.username + '@' : ''}${cred.host}`);
        // Reload to update sessions list
        await load();
      } else if (session?.status === 'error') {
        notificationService.error(`Connection failed: ${session?.lastError || 'Unknown error'}`);
      } else {
        notificationService.info(`Connection status: ${session?.status || 'unknown'}`);
      }
    } catch (e: any) {
      setError(e?.message || 'Connect failed');
      notificationService.error(e?.message || 'Connect failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async (contextId?: string) => {
    try {
      setLoading(true);
      logHop('disconnect requested', { contextId });
      await (backendService as any).disconnectHop?.(contextId);
      notificationService.success(contextId ? `Disconnected from ${contextId}` : 'Disconnected');
      // Reload to update sessions list
      await load();
    } catch (e: any) {
      setError(e?.message || 'Disconnect failed');
      notificationService.error(e?.message || 'Disconnect failed');
    } finally {
      setLoading(false);
    }
  };

  const handleHopTo = async (contextId: string) => {
    try {
      setLoading(true);
      logHop('hopTo requested', { contextId });
      await (backendService as any).hopTo?.(contextId);
      const ses = sessions.find(s => s.contextId === contextId);
      const label = ses?.host ? `${ses.username || ''}@${ses.host}` : contextId;
      notificationService.success(`Switched to ${label}`);
      // Reload to update active session
      await load();
    } catch (e: any) {
      setError(e?.message || 'Hop failed');
      notificationService.error(e?.message || 'Hop failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      setLoading(true);
      setError(null);
      const payload: any = {
        name: newCred.name?.trim(),
        host: newCred.host?.trim(),
        port: Number(newCred.port) || 22,
        username: newCred.username || '',
        auth: newCred.auth || 'password',
        defaultPath: newCred.defaultPath || undefined,
        privateKeyId: undefined as string | undefined,
      };
      if (payload.auth === 'privateKey' && uploadedKeyId) {
        payload.privateKeyId = uploadedKeyId;
      }
      if (!payload.name || !payload.host) {
        setError('Name and host are required');
        return;
      }
      await (backendService as any).createHopCredential?.(payload);
      setNewCred({ port: 22, auth: 'password' });
      setUploadedKeyId(null);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Create credential failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      if (!confirm('Delete this credential?')) return;
      setLoading(true);
      await (backendService as any).deleteHopCredential?.(id);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Delete failed');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (cred: Credential) => {
    setEditingId(cred.id);
    setEditCred({ ...cred });
    setUploadedKeyId(null); // Clear any previously uploaded key
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditCred({});
    setUploadedKeyId(null); // Clear any uploaded key when canceling
  };

  const handleSaveEdit = async () => {
    try {
      if (!editingId) return;
      setLoading(true);
      setError(null);
      const payload: any = {
        name: editCred.name?.trim(),
        host: editCred.host?.trim(),
        port: Number(editCred.port) || 22,
        username: editCred.username || '',
        auth: editCred.auth || 'password',
        defaultPath: editCred.defaultPath || undefined,
        privateKeyId: undefined as string | undefined,
      };
      // If auth is privateKey and we have an uploaded key, use it; otherwise keep existing
      if (payload.auth === 'privateKey' && uploadedKeyId) {
        payload.privateKeyId = uploadedKeyId;
      } else if (payload.auth === 'privateKey') {
        payload.privateKeyId = editCred.privateKeyId;
      }
      if (!payload.name || !payload.host) {
        setError('Name and host are required');
        return;
      }
      await (backendService as any).updateHopCredential?.(editingId, payload);
      setEditingId(null);
      setEditCred({});
      setUploadedKeyId(null);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Update credential failed');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyUpload = async (file: File) => {
    try {
      setLoading(true);
      const keyId = await (backendService as any).uploadHopKey?.(file);
      setUploadedKeyId(keyId);
      setNewCred(prev => ({ ...prev, auth: 'privateKey' }));
    } catch (e: any) {
      setError(e?.message || 'Key upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`h-full w-full p-3 text-sm ${className} flex flex-col`} style={{ color: 'var(--icui-text-primary)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="font-medium">SSH Hop</div>
        <div className="flex items-center space-x-2">
          {(() => {
            const activeContextId = session?.contextId || session?.context_id || 'local';
            const isLocal = activeContextId === 'local';
            const isConnected = isLocal || session?.connected || session?.status === 'connected';
            const label = isLocal
              ? 'local context'
              : (isConnected ? `${session?.username || ''}@${session?.host || 'remote'}:${session?.cwd || ''}` : 'disconnected');
            return (
              <>
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: isConnected ? 'var(--icui-success)' : 'var(--icui-error)' }} />
                <span className="opacity-80">{label}</span>
              </>
            );
          })()}
        </div>
      </div>

      {error && <div className="mb-2 text-red-400">{error}</div>}

      {/* Scrollable content area */}
      <div className="flex-1 min-h-0 overflow-auto custom-scroll thin-scroll pr-1" style={{ scrollbarWidth: 'thin' }}>
        {/* Available connections */}
        <div className="border rounded mb-3" style={{ borderColor: 'var(--icui-border-subtle)' }}>
          <div className="p-2 border-b flex items-center justify-between" style={{ borderColor: 'var(--icui-border-subtle)' }}>
            <span>Available connections</span>
            <button
              className="px-2 py-1 rounded border border-green-400 text-green-300 text-xs hover:bg-[var(--icui-bg-tertiary)]"
              onClick={() => setShowAddForm(!showAddForm)}
              title={showAddForm ? 'Hide add form' : 'Add new credential'}
            >
              {showAddForm ? '−' : '+'} Add
            </button>
          </div>
          {/* Local row */}
          {(() => {
            const activeContextId = session?.contextId || session?.context_id || 'local';
            const isActive = activeContextId === 'local';
            const anyRemote = sessions.some(s => (s.contextId || s.context_id) !== 'local' && s.status === 'connected');
            return (
              <div className={`p-2 flex items-center justify-between ${isActive ? 'bg-[var(--icui-bg-tertiary)]' : 'hover:bg-[var(--icui-bg-tertiary)]'}`}>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 rounded-full" style={isActive ? { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #4facfe 75%, #00f2fe 100%)', animation: 'pulse 2s ease-in-out infinite' } : { backgroundColor: 'var(--icui-success)' }} />
                  <span className={isActive ? 'font-medium' : ''}>local</span>
                  <span className="opacity-60 text-xs">localhost</span>
                  {isActive && <span className="ml-1 opacity-50 text-xs">(active)</span>}
                </div>
                <div>
                  {anyRemote && (
                    <button className={`px-2 py-1 rounded border border-blue-400 text-blue-300 text-xs ${isActive ? 'opacity-50 cursor-default' : ''}`} onClick={() => !isActive && handleHopTo('local')} disabled={loading || isActive}>Hop</button>
                  )}
                </div>
              </div>
            );
          })()}
          <div className="border-b opacity-20" style={{ borderColor: 'var(--icui-border-subtle)' }} />
          {credentials.length === 0 && <div className="p-3 opacity-70">No remote credentials yet.</div>}
          {credentials.map(c => {
            const activeContextId = session?.contextId || session?.context_id || 'local';
            const credSession = sessions.find(s => (s.credentialId === c.id || s.credential_id === c.id) || (s.contextId === c.id || s.context_id === c.id));
            const isConnected = !!credSession && credSession.status === 'connected';
            const isActive = !!credSession && ((credSession.contextId || credSession.context_id) === activeContextId);
            const statusDotStyle = isActive 
              ? { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #4facfe 75%, #00f2fe 100%)', animation: 'pulse 2s ease-in-out infinite' }
              : { backgroundColor: isConnected ? 'var(--icui-success)' : 'var(--icui-error)' };
            return (
              <div key={c.id} className={`p-2 flex items-center justify-between ${isActive ? 'bg-[var(--icui-bg-tertiary)]' : 'hover:bg-[var(--icui-bg-tertiary)]'}`}>
                {editingId === c.id ? (
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-2">
                    <input className="px-2 py-1 rounded border bg-transparent" placeholder="Name" value={editCred.name || ''} onChange={e => setEditCred(v => ({ ...v, name: e.target.value }))} />
                    <input className="px-2 py-1 rounded border bg-transparent" placeholder="Host" value={editCred.host || ''} onChange={e => setEditCred(v => ({ ...v, host: e.target.value }))} />
                    <input className="px-2 py-1 rounded border bg-transparent" placeholder="Port" type="number" value={editCred.port || 22} onChange={e => setEditCred(v => ({ ...v, port: Number(e.target.value) }))} />
                    <input className="px-2 py-1 rounded border bg-transparent" placeholder="Username (optional)" value={editCred.username || ''} onChange={e => setEditCred(v => ({ ...v, username: e.target.value }))} />
                    <select className="px-2 py-1 rounded border bg-transparent" value={editCred.auth || 'password'} onChange={e => setEditCred(v => ({ ...v, auth: e.target.value as any }))}>
                      <option value="password">Password</option>
                      <option value="privateKey">Private Key</option>
                      <option value="agent">SSH Agent</option>
                    </select>
                    <input className="px-2 py-1 rounded border bg-transparent" placeholder="Default Path (optional)" value={editCred.defaultPath || ''} onChange={e => setEditCred(v => ({ ...v, defaultPath: e.target.value }))} />
                    {editCred.auth === 'privateKey' && (
                      <div className="md:col-span-2 flex items-center space-x-2">
                        <label className="px-3 py-1 rounded border cursor-pointer hover:bg-[var(--icui-bg-tertiary)]">
                          Choose File
                          <input type="file" className="hidden" onChange={e => e.target.files && e.target.files[0] && handleKeyUpload(e.target.files[0])} />
                        </label>
                        {uploadedKeyId && <span className="opacity-70">Key uploaded: {uploadedKeyId.slice(0,8)}…</span>}
                      </div>
                    )}
                    <div className="flex space-x-2">
                      <button className="px-3 py-1 rounded border border-green-400 text-green-300" onClick={handleSaveEdit} disabled={loading}>Save</button>
                      <button className="px-3 py-1 rounded border" onClick={handleCancelEdit} disabled={loading}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 rounded-full" style={statusDotStyle} />
                      <span className={isActive ? 'font-medium' : ''}>{c.name}</span>
                      <span className="opacity-60 text-xs">{c.username ? `${c.username}@` : ''}{c.host}:{c.port}</span>
                      {isActive && <span className="ml-1 opacity-50 text-xs">(active)</span>}
                    </div>
                    <div className="flex items-center space-x-2">
                      {isConnected ? (
                        <>
                          <button className={`px-2 py-1 rounded border border-blue-400 text-blue-300 text-xs ${isActive ? 'opacity-50 cursor-default' : ''}`} onClick={() => !isActive && credSession && handleHopTo(credSession.contextId || credSession.context_id)} disabled={loading || !credSession || isActive}>Hop</button>
                          <button className="px-2 py-1 rounded border text-xs" onClick={() => credSession && handleDisconnect(credSession.contextId || credSession.context_id)} disabled={loading || !credSession}>Disconnect</button>
                        </>
                      ) : (
                        <button className="px-2 py-1 rounded border text-xs" onClick={() => handleConnect(c)} disabled={loading}>Connect</button>
                      )}
                      <button className="px-2 py-1 rounded border text-xs" onClick={() => handleEdit(c)} disabled={loading}>Edit</button>
                      <button className="px-2 py-1 rounded border border-red-400 text-red-300 text-xs" onClick={() => handleDelete(c.id)} disabled={loading}>Delete</button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>

        {/* Add Credential */}
        {showAddForm && (
        <div className="border rounded" style={{ borderColor: 'var(--icui-border-subtle)' }}>
          <div className="p-2 border-b" style={{ borderColor: 'var(--icui-border-subtle)' }}>Add credential</div>
          <div className="p-3 grid grid-cols-1 md:grid-cols-3 gap-2">
            <input className="px-2 py-1 rounded border bg-transparent" placeholder="Name" value={newCred.name || ''} onChange={e => setNewCred(v => ({ ...v, name: e.target.value }))} />
            <input className="px-2 py-1 rounded border bg-transparent" placeholder="Host" value={newCred.host || ''} onChange={e => setNewCred(v => ({ ...v, host: e.target.value }))} />
            <input className="px-2 py-1 rounded border bg-transparent" placeholder="Port" type="number" value={newCred.port || 22} onChange={e => setNewCred(v => ({ ...v, port: Number(e.target.value) }))} />
            <input className="px-2 py-1 rounded border bg-transparent" placeholder="Username (optional)" value={newCred.username || ''} onChange={e => setNewCred(v => ({ ...v, username: e.target.value }))} />
            <select className="px-2 py-1 rounded border bg-transparent" value={newCred.auth || 'password'} onChange={e => setNewCred(v => ({ ...v, auth: e.target.value as any }))}>
              <option value="password">Password</option>
              <option value="privateKey">Private Key</option>
              <option value="agent">SSH Agent</option>
            </select>
            <input className="px-2 py-1 rounded border bg-transparent" placeholder="Default Path (optional)" value={newCred.defaultPath || ''} onChange={e => setNewCred(v => ({ ...v, defaultPath: e.target.value }))} />
            {newCred.auth === 'privateKey' && (
              <div className="md:col-span-2 flex items-center space-x-2">
                <label className="px-3 py-1 rounded border cursor-pointer hover:bg-[var(--icui-bg-tertiary)]">
                  Choose File
                  <input type="file" className="hidden" onChange={e => e.target.files && e.target.files[0] && handleKeyUpload(e.target.files[0])} />
                </label>
                {uploadedKeyId && <span className="opacity-70">Key uploaded: {uploadedKeyId.slice(0,8)}…</span>}
              </div>
            )}
            <div>
              <button className="px-3 py-1 rounded border" onClick={handleCreate} disabled={loading}>Add</button>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

export default ICUIHop;
