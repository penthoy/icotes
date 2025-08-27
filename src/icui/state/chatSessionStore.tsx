import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { configService } from '../../services/config-service';
import { chatBackendClient } from '../services/chat-backend-client-impl';
import { emitSessionChange } from '../lib/eventBus';

export interface ChatSessionMeta {
  id: string;
  name: string;
  created: number;
  updated: number;
  message_count?: number;
  last_message_time?: string;
}

interface StoreState {
  sessions: ChatSessionMeta[];
  activeSessionId: string;
  isLoading: boolean;
}

interface StoreApi extends StoreState {
  refresh: () => Promise<void>;
  create: (name?: string) => Promise<string>;
  rename: (id: string, name: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  switchTo: (id: string, source?: string) => void;
}

const ChatSessionStoreContext = createContext<StoreApi | null>(null);

async function getApiBaseUrl(): Promise<string> {
  try {
    const cfg = await configService.getConfig();
    let base = cfg.api_url || cfg.base_url;
    return base.endsWith('/api') ? base.slice(0, -4) : base;
  } catch (e) {
    const base = (window as any).__ICUI_API_URL__ || (import.meta as any).env?.VITE_API_URL || (import.meta as any).env?.VITE_BACKEND_URL || `${window.location.protocol}//${window.location.host}`;
    return base.endsWith('/api') ? base.slice(0, -4) : base;
  }
}

export const ChatSessionStoreProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
  const [activeSessionId, setActiveSessionId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const initializedRef = useRef(false);

  const refresh = async () => {
    try {
      setIsLoading(true);
      const base = await getApiBaseUrl();
      const res = await fetch(`${base}/api/chat/sessions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      const backend = result.data || [];
      const converted: ChatSessionMeta[] = backend.map((s: any) => ({
        id: s.id,
        name: s.name || 'Untitled',
        created: typeof s.created === 'number' ? (s.created > 1e12 ? s.created : s.created * 1000) : Date.now(),
        updated: typeof s.updated === 'number' ? (s.updated > 1e12 ? s.updated : s.updated * 1000) : Date.now(),
        message_count: s.message_count,
        last_message_time: s.last_message_time,
      }));
      setSessions(converted);

      // choose active
      let nextActive = activeSessionId;
      const stored = localStorage.getItem('icui.chat.active_session');
      const ids = new Set(converted.map(s => s.id));
      if (!nextActive) nextActive = stored && ids.has(stored) ? stored : '';
      if (!nextActive && converted.length) {
        nextActive = converted.reduce((a, b) => (a.created >= b.created ? a : b)).id;
      }
      if (nextActive && nextActive !== activeSessionId) {
        setActiveSessionId(nextActive);
        chatBackendClient.setCurrentSession(nextActive);
        localStorage.setItem('icui.chat.active_session', nextActive);
        // suppress initial broadcast; consumers can read from store
        if (initializedRef.current) {
          emitSessionChange({ sessionId: nextActive, action: 'switch', sessionName: converted.find(s => s.id === nextActive)?.name, source: 'chatSessionStore' });
        }
      }
    } catch (e) {
      console.error('[chatSessionStore] refresh failed', e);
      // best-effort fallback: keep current
    } finally {
      setIsLoading(false);
      initializedRef.current = true;
    }
  };

  const create = async (name?: string): Promise<string> => {
    try {
      const base = await getApiBaseUrl();
      const res = await fetch(`${base}/api/chat/sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: name || 'New Chat' }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const result = await res.json();
      const id = result.data.session_id;
      const meta: ChatSessionMeta = { id, name: result.data.name || name || 'New Chat', created: Date.now(), updated: Date.now() };
      setSessions(prev => [meta, ...prev]);
      setActiveSessionId(id);
      chatBackendClient.setCurrentSession(id);
      localStorage.setItem('icui.chat.active_session', id);
      emitSessionChange({ sessionId: id, action: 'create', sessionName: meta.name, source: 'chatSessionStore' });
      return id;
    } catch (e) {
      // client-side fallback
      const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const meta: ChatSessionMeta = { id, name: name || 'New Chat', created: Date.now(), updated: Date.now() };
      setSessions(prev => [meta, ...prev]);
      setActiveSessionId(id);
      chatBackendClient.setCurrentSession(id);
      localStorage.setItem('icui.chat.active_session', id);
      emitSessionChange({ sessionId: id, action: 'create', sessionName: meta.name, source: 'chatSessionStore' });
      return id;
    }
  };

  const rename = async (id: string, name: string) => {
    try {
      const base = await getApiBaseUrl();
      const res = await fetch(`${base}/api/chat/sessions/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch {}
    setSessions(prev => prev.map(s => (s.id === id ? { ...s, name, updated: Date.now() } : s)));
    if (activeSessionId === id) {
      emitSessionChange({ sessionId: id, action: 'switch', sessionName: name, source: 'chatSessionStore' });
    }
  };

  const remove = async (id: string) => {
    try {
      const base = await getApiBaseUrl();
      await fetch(`${base}/api/chat/sessions/${id}`, { method: 'DELETE' });
    } catch {}
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id);
      // Notify deletion first
      const deletedName = prev.find(s => s.id === id)?.name;
      emitSessionChange({ sessionId: id, action: 'delete', sessionName: deletedName, source: 'chatSessionStore' });
      if (activeSessionId === id) {
        const nextId = next[0]?.id || '';
        setActiveSessionId(nextId);
        chatBackendClient.setCurrentSession(nextId);
        if (nextId) {
          emitSessionChange({ sessionId: nextId, action: 'switch', sessionName: next.find(s => s.id === nextId)?.name, source: 'chatSessionStore' });
          localStorage.setItem('icui.chat.active_session', nextId);
        } else {
          localStorage.removeItem('icui.chat.active_session');
        }
      }
      return next;
    });
  };

  const switchTo = (id: string, source?: string) => {
    if (!id || id === activeSessionId) return;
    setActiveSessionId(id);
    chatBackendClient.setCurrentSession(id);
    localStorage.setItem('icui.chat.active_session', id);
    emitSessionChange({ sessionId: id, action: 'switch', sessionName: sessions.find(s => s.id === id)?.name, source: source || 'chatSessionStore' });
  };

  useEffect(() => { refresh(); }, []);

  const value: StoreApi = useMemo(() => ({ sessions, activeSessionId, isLoading, refresh, create, rename, remove, switchTo }), [sessions, activeSessionId, isLoading]);
  return (
    <ChatSessionStoreContext.Provider value={value}>
      {children}
    </ChatSessionStoreContext.Provider>
  );
};

export function useChatSessionStore(): StoreApi {
  const ctx = useContext(ChatSessionStoreContext);
  if (!ctx) throw new Error('useChatSessionStore must be used within ChatSessionStoreProvider');
  return ctx;
}
