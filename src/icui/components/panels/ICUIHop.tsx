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

const ICUIHop: React.FC<{ className?: string }> = ({ className = '' }) => {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<any>(null);
  const [newCred, setNewCred] = useState<Partial<Credential>>({ port: 22, auth: 'password' });
  const [uploadedKeyId, setUploadedKeyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [creds, status] = await Promise.all([
        (backendService as any).listHopCredentials?.(),
        (backendService as any).getHopStatus?.(),
      ]);
      if (Array.isArray(creds)) setCredentials(creds);
      setSession(status || null);
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
    const onHop = (s: any) => setSession(s);
    const onHopEvent = (evt: any) => {
      const name = evt?.event || '';
      if (name.startsWith('hop.credentials.')) {
        load();
      }
      if (name === 'hop.status') {
        setSession(evt?.data);
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
      if (session?.status === 'connected' || session?.connected) {
        notificationService.success(`Connected to ${cred.username ? cred.username + '@' : ''}${cred.host}`);
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

  const handleDisconnect = async () => {
    try {
      setLoading(true);
      await (backendService as any).disconnectHop?.();
    } catch (e: any) {
      setError(e?.message || 'Disconnect failed');
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
    <div className={`h-full w-full p-3 text-sm ${className}`} style={{ color: 'var(--icui-text-primary)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="font-medium">SSH Hop</div>
        <div className="flex items-center space-x-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: (session?.connected ? 'var(--icui-success)' : 'var(--icui-error)') }}
            title={session?.connected ? 'Connected' : 'Disconnected'}
          />
          <span className="opacity-80">
            {session?.connected ? `${session?.username || ''}@${session?.host || 'remote'}:${session?.cwd || ''}` : 'local context'}
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-2 text-red-400">{error}</div>
      )}

      <div className="border rounded mb-3" style={{ borderColor: 'var(--icui-border-subtle)' }}>
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
              <input type="file" onChange={e => e.target.files && e.target.files[0] && handleKeyUpload(e.target.files[0])} />
              {uploadedKeyId && <span className="opacity-70">Key uploaded: {uploadedKeyId.slice(0,8)}…</span>}
            </div>
          )}
          <div>
            <button className="px-3 py-1 rounded border" onClick={handleCreate} disabled={loading}>Add</button>
          </div>
        </div>
      </div>

      <div className="border rounded" style={{ borderColor: 'var(--icui-border-subtle)' }}>
        <div className="p-2 border-b" style={{ borderColor: 'var(--icui-border-subtle)' }}>Saved credentials</div>
        <div className="max-h-64 overflow-auto">
          {credentials.length === 0 && (
            <div className="p-3 opacity-70">No credentials yet.</div>
          )}
          {credentials.map((c) => (
            <div key={c.id} className="p-2 flex items-center justify-between hover:bg-[var(--icui-bg-tertiary)]">
              <div className="space-x-2">
                <span className="font-medium">{c.name}</span>
                <span className="opacity-70">{c.username ? `${c.username}@` : ''}{c.host}:{c.port}</span>
              </div>
              <div className="space-x-2">
                {!session?.connected && (
                  <button className="px-2 py-1 rounded border" onClick={() => handleConnect(c)} disabled={loading}>
                    Connect
                  </button>
                )}
                {session?.connected && session?.credential_id === c.id && (
                  <button className="px-2 py-1 rounded border" onClick={handleDisconnect} disabled={loading}>
                    Disconnect
                  </button>
                )}
                <button className="px-2 py-1 rounded border border-red-400 text-red-300" onClick={() => handleDelete(c.id)} disabled={loading}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ICUIHop;
