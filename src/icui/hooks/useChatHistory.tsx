import { useCallback, useMemo } from 'react';
import { useChatSessionStore, ChatSessionMeta } from '../state/chatSessionStore';
import { emitSessionChange } from '../lib/eventBus';

export function useChatHistory() {
	const store = useChatSessionStore();

	const createSession = useCallback(async (name?: string): Promise<string> => {
		const id = await store.create(name);
		return id;
	}, [store]);

	const renameSession = useCallback(async (id: string, name: string) => {
		await store.rename(id, name);
	}, [store]);

	const deleteSession = useCallback(async (id: string) => {
		await store.remove(id);
	}, [store]);

	const switchSession = useCallback((id: string) => {
		if (id && id !== store.activeSessionId) {
			store.switchTo(id, 'useChatHistory');
		}
	}, [store]);

	const activeSession = useMemo(() => store.sessions.find(s => s.id === store.activeSessionId) || null, [store.sessions, store.activeSessionId]);

	return {
		sessions: store.sessions,
		activeSessionId: store.activeSessionId,
		activeSession,
		isLoading: store.isLoading,
		createSession,
		renameSession,
		deleteSession,
		switchSession,
		refreshSessions: store.refresh
	};
}