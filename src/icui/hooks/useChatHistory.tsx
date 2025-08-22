import { useCallback, useEffect, useMemo, useState } from 'react';
import { enhancedChatBackendClient as chatClient } from '../services/chat-backend-client-impl';
import { configService } from '../../services/config-service';

export interface ChatSessionMeta {
	id: string;
	name: string;
	created: number;
	updated: number;
	message_count?: number;
	last_message_time?: string;
}

const STORAGE_KEY = 'icui.chat.sessions.v1';

export function useChatHistory() {
	const [sessions, setSessions] = useState<ChatSessionMeta[]>([]);
	const [activeSessionId, setActiveSessionId] = useState<string>('');
	const [isLoading, setIsLoading] = useState<boolean>(true);

	// Backend API helpers
	const getApiUrl = async (): Promise<string> => {
		try {
			const config = await configService.getConfig();
			let baseUrl = config.api_url || config.base_url;
			if (baseUrl.endsWith('/api')) {
				baseUrl = baseUrl.slice(0, -4);
			}
			return baseUrl;
		} catch (error) {
			console.warn('[useChatHistory] Failed to get config, using fallbacks:', error);
			// Fallback to environment variables
			const baseUrl = (window as any).__ICUI_API_URL__ || 
							(import.meta as any).env?.VITE_API_URL || 
							(import.meta as any).env?.VITE_BACKEND_URL ||
							`${window.location.protocol}//${window.location.host}`;
			return baseUrl.endsWith('/api') ? baseUrl.slice(0, -4) : baseUrl;
		}
	};

	// Load sessions from backend API
	const loadSessions = async (): Promise<void> => {
		try {
			const baseUrl = await getApiUrl();
			const response = await fetch(`${baseUrl}/api/chat/sessions`);
			if (!response.ok) {
				throw new Error(`Failed to load sessions: ${response.status}`);
			}
			const result = await response.json();
			const backendSessions = result.data || [];
			
			// Convert backend format to frontend format
			const convertedSessions: ChatSessionMeta[] = backendSessions.map((s: any) => ({
				id: s.id,
				name: s.name || 'Untitled',
				created: s.created * 1000, // Convert to milliseconds
				updated: s.updated * 1000, // Convert to milliseconds
				message_count: s.message_count,
				last_message_time: s.last_message_time
			}));

			setSessions(convertedSessions);

			// Set active session (prefer localStorage, then backend, then first session)
			const storedActive = localStorage.getItem('icui.chat.active_session');
			const availableIds = new Set(convertedSessions.map(s => s.id));
			let activeId = '';

			if (storedActive && availableIds.has(storedActive)) {
				activeId = storedActive;
			} else if (convertedSessions.length > 0) {
				activeId = convertedSessions[0].id;
			}

			if (activeId) {
				setActiveSessionId(activeId);
				chatClient.setCurrentSession(activeId);
				localStorage.setItem('icui.chat.active_session', activeId);
			}

		} catch (error) {
			console.error('[useChatHistory] Failed to load sessions from backend:', error);
			// Fallback to localStorage for backward compatibility
			await loadFromLocalStorage();
		}
	};

	// Fallback: Load from localStorage (backward compatibility)
	const loadFromLocalStorage = async (): Promise<void> => {
		const createDefault = async () => {
			try {
				const baseUrl = await getApiUrl();
				const response = await fetch(`${baseUrl}/api/chat/sessions`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ name: 'Default Chat' })
				});
				
				if (response.ok) {
					const result = await response.json();
					const newSession: ChatSessionMeta = {
						id: result.data.session_id,
						name: result.data.name || 'Default Chat',
						created: Date.now(),
						updated: Date.now()
					};
					setSessions([newSession]);
					setActiveSessionId(newSession.id);
					chatClient.setCurrentSession(newSession.id);
					localStorage.setItem('icui.chat.active_session', newSession.id);
				} else {
					throw new Error('Failed to create default session');
				}
			} catch (error) {
				console.error('[useChatHistory] Failed to create default session:', error);
				// Ultimate fallback - client-side only
				const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
				const now = Date.now();
				const meta: ChatSessionMeta = { id, name: 'Default Chat', created: now, updated: now };
				setSessions([meta]);
				setActiveSessionId(id);
				chatClient.setCurrentSession(id);
			}
		};

		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw) as { sessions: ChatSessionMeta[]; active?: string };
				const loaded = Array.isArray(parsed.sessions) ? parsed.sessions : [];
				if (loaded.length === 0) return await createDefault();
				setSessions(loaded);
				const candidate = parsed.active || chatClient.currentSession || loaded[0]?.id || '';
				const ids = new Set(loaded.map(s => s.id));
				const activeId = ids.has(candidate) ? candidate : loaded[0]?.id || '';
				setActiveSessionId(activeId);
				if (activeId) {
					chatClient.setCurrentSession(activeId);
					localStorage.setItem('icui.chat.active_session', activeId);
				}
			} else {
				await createDefault();
			}
		} catch {
			await createDefault();
		}
	};

	// Initial load
	useEffect(() => {
		const initializeSessions = async () => {
			setIsLoading(true);
			await loadSessions();
			setIsLoading(false);
		};
		initializeSessions();
	}, []);

	// Persist to localStorage (for active session only, sessions are managed by backend)
	useEffect(() => {
		if (activeSessionId) {
			localStorage.setItem('icui.chat.active_session', activeSessionId);
		}
	}, [activeSessionId]);

	const createSession = useCallback(async (name?: string): Promise<string> => {
		try {
			const baseUrl = await getApiUrl();
			const response = await fetch(`${baseUrl}/api/chat/sessions`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: name || 'New Chat' })
			});

			if (!response.ok) {
				throw new Error(`Failed to create session: ${response.status}`);
			}

			const result = await response.json();
			const newSession: ChatSessionMeta = {
				id: result.data.session_id,
				name: result.data.name || name || 'New Chat',
				created: Date.now(),
				updated: Date.now()
			};

			// Add to frontend state
			setSessions(prev => [newSession, ...prev]);
			setActiveSessionId(newSession.id);
			chatClient.setCurrentSession(newSession.id);

			return newSession.id;
		} catch (error) {
			console.error('[useChatHistory] Failed to create session:', error);
			// Fallback to client-side session creation
			const id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
			const now = Date.now();
			const meta: ChatSessionMeta = { id, name: name || 'New Chat', created: now, updated: now };
			setSessions(prev => [meta, ...prev]);
			setActiveSessionId(id);
			chatClient.setCurrentSession(id);
			return id;
		}
	}, []);

	const renameSession = useCallback(async (id: string, name: string): Promise<void> => {
		try {
			const baseUrl = await getApiUrl();
			const response = await fetch(`${baseUrl}/api/chat/sessions/${id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name })
			});

			if (!response.ok) {
				throw new Error(`Failed to rename session: ${response.status}`);
			}

			// Update frontend state
			setSessions(prev => prev.map(s => s.id === id ? { ...s, name, updated: Date.now() } : s));
		} catch (error) {
			console.error('[useChatHistory] Failed to rename session:', error);
			// Fallback to client-side update
			setSessions(prev => prev.map(s => s.id === id ? { ...s, name, updated: Date.now() } : s));
		}
	}, []);

	const deleteSession = useCallback(async (id: string): Promise<void> => {
		try {
			const baseUrl = await getApiUrl();
			const response = await fetch(`${baseUrl}/api/chat/sessions/${id}`, {
				method: 'DELETE'
			});

			if (!response.ok) {
				throw new Error(`Failed to delete session: ${response.status}`);
			}

			// Update frontend state
			setSessions(prev => {
				const next = prev.filter(s => s.id !== id);
				if (activeSessionId === id) {
					const nextId = next[0]?.id || '';
					setActiveSessionId(nextId);
					chatClient.setCurrentSession(nextId);
				}
				return next;
			});
		} catch (error) {
			console.error('[useChatHistory] Failed to delete session:', error);
			// Fallback to client-side delete
			setSessions(prev => {
				const next = prev.filter(s => s.id !== id);
				if (activeSessionId === id) {
					const nextId = next[0]?.id || '';
					setActiveSessionId(nextId);
					chatClient.setCurrentSession(nextId);
				}
				return next;
			});
		}
	}, [activeSessionId]);

	const switchSession = useCallback((id: string) => {
		setActiveSessionId(id);
		chatClient.setCurrentSession(id);
	}, []);

	const refreshSessions = useCallback(async (): Promise<void> => {
		await loadSessions();
	}, []);

	const activeSession = useMemo(() => sessions.find(s => s.id === activeSessionId) || null, [sessions, activeSessionId]);

	return {
		sessions,
		activeSessionId,
		activeSession,
		isLoading,
		createSession,
		renameSession,
		deleteSession,
		switchSession,
		refreshSessions
	};
} 