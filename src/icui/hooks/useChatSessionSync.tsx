import { useCallback } from 'react';

// Global event system for session synchronization
const SESSION_CHANGE_EVENT = 'icui.chat.session.change';

interface SessionChangeEvent extends CustomEvent {
	detail: {
		sessionId: string;
		sessionName?: string;
		action: 'switch' | 'create' | 'delete';
	};
}

export function useChatSessionSync() {
	// Emit session change event
	const emitSessionChange = useCallback((sessionId: string, action: 'switch' | 'create' | 'delete', sessionName?: string) => {
		const event = new CustomEvent(SESSION_CHANGE_EVENT, {
			detail: { sessionId, action, sessionName }
		});
		window.dispatchEvent(event);
	}, []);

	// Listen for session change events
	const onSessionChange = useCallback((callback: (sessionId: string, action: 'switch' | 'create' | 'delete', sessionName?: string) => void) => {
		const handler = (event: SessionChangeEvent) => {
			callback(event.detail.sessionId, event.detail.action, event.detail.sessionName);
		};
		
		window.addEventListener(SESSION_CHANGE_EVENT, handler as EventListener);
		
		return () => {
			window.removeEventListener(SESSION_CHANGE_EVENT, handler as EventListener);
		};
	}, []);

	return {
		emitSessionChange,
		onSessionChange
	};
} 