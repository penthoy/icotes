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
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw) as { sessions: ChatSessionMeta[]; active?: string };
				setSessions(parsed.sessions || []);
				const activeId = parsed.active || chatClient.currentSession || '';
				setActiveSessionId(activeId);
				if (activeId) {
					chatClient.setCurrentSession(activeId);
				}
			} else {
				// No sessions exist - create a default one
				const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
				const now = Date.now();
				const meta: ChatSessionMeta = { id, name: 'Default Chat', created: now, updated: now };
				setSessions([meta]);
				setActiveSessionId(id);
				chatClient.setCurrentSession(id);
			}
		} catch {
			// ignore
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
		setSessions(prev => prev.filter(s => s.id !== id));
		if (activeSessionId === id) {
			setActiveSessionId('');
			chatClient.setCurrentSession('');
		}
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