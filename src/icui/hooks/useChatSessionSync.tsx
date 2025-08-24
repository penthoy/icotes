import { useCallback } from 'react';
import { emitSessionChange as busEmit, subscribeSessionChange } from '../lib/eventBus';

export function useChatSessionSync(source: string = 'useChatSessionSync') {
	// Emit via typed bus
	const emitSessionChange = useCallback((sessionId: string, action: 'switch' | 'create' | 'delete', sessionName?: string) => {
		busEmit({ sessionId, action, sessionName, source });
	}, [source]);

	// Subscribe via typed bus
	const onSessionChange = useCallback((callback: (sessionId: string, action: 'switch' | 'create' | 'delete', sessionName?: string, payload?: any) => void) => {
		return subscribeSessionChange((payload) => {
			if (payload.source && payload.source === source) return; // self-ignore
			callback(payload.sessionId, payload.action, payload.sessionName, payload);
		});
	}, [source]);

	return { emitSessionChange, onSessionChange };
} 