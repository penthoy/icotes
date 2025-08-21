import { useCallback, useEffect, useMemo, useState } from 'react';
import { enhancedChatBackendClient as chatClient } from '../services/chat-backend-client-impl';

export interface ChatSessionMeta {
	id: string;
	name: string;
	created: number;
	updated: number;
}

const STORAGE_KEY = 'icui.chat.sessions.v1';

export function useChatHistory() {
	const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
	const [activeSessionId, setActiveSessionId] = useState<string>('');

	// Load from localStorage
	useEffect(() => {
		const createDefault = () => {
			const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
			const now = Date.now();
			const meta: ChatSessionMeta = { id, name: 'Default Chat', created: now, updated: now };
			setSessions([meta]);
			setActiveSessionId(id);
			chatClient.setCurrentSession(id);
		};

		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw) as { sessions: ChatSessionMeta[]; active?: string };
				const loaded = Array.isArray(parsed.sessions) ? parsed.sessions : [];
				if (loaded.length === 0) return createDefault();
				setSessions(loaded);
				const candidate = parsed.active || chatClient.currentSession || loaded[0]?.id || '';
				const ids = new Set(loaded.map(s => s.id));
				const activeId = ids.has(candidate) ? candidate : loaded[0]?.id || '';
				setActiveSessionId(activeId);
				if (activeId) chatClient.setCurrentSession(activeId);
			} else {
				createDefault();
			}
		} catch {
			// No sessions exist or JSON parse error we silently leave the state empty. Prefer falling back to a default session in both cases.
			createDefault();
		}
	}, []);

	// Persist to localStorage
	useEffect(() => {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessions, active: activeSessionId }));
		} catch {}
	}, [sessions, activeSessionId]);

	const createSession = useCallback((name?: string) => {
		const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
		const now = Date.now();
		const meta: ChatSessionMeta = { id, name: name || 'New Chat', created: now, updated: now };
		setSessions(prev => [meta, ...prev]);
		setActiveSessionId(id);
		chatClient.setCurrentSession(id);
		return id;
	}, []);

	const renameSession = useCallback((id: string, name: string) => {
		setSessions(prev => prev.map(s => s.id === id ? { ...s, name, updated: Date.now() } : s));
	}, []);

	const deleteSession = useCallback((id: string) => {
		setSessions(prev => {
			const next = prev.filter(s => s.id !== id);
			if (activeSessionId === id) {
				const nextId = next[0]?.id || '';
				setActiveSessionId(nextId);
				chatClient.setCurrentSession(nextId);
			}
			return next;
		});
	}, [activeSessionId]);

	const switchSession = useCallback((id: string) => {
		setActiveSessionId(id);
		chatClient.setCurrentSession(id);
	}, []);

	const activeSession = useMemo(() => sessions.find(s => s.id === activeSessionId) || null, [sessions, activeSessionId]);

	return {
		sessions,
		activeSessionId,
		activeSession,
		createSession,
		renameSession,
		deleteSession,
		switchSession
	};
} 