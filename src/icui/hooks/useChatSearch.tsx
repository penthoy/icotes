import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChatMessage } from '../types/chatTypes';

export interface SearchResult {
	messageId: string;
	index: number; // occurrence index in message
	snippet: string;
}

export function useChatSearch(messages: ChatMessage[]) {
	const [query, setQuery] = useState('');
	const [results, setResults] = useState<SearchResult[]>([]);
	const [activeIdx, setActiveIdx] = useState(0);
	const [isOpen, setIsOpen] = useState(false);

	const computeResults = useCallback((q: string): SearchResult[] => {
		if (!q.trim()) return [];
		const lower = q.toLowerCase();
		const found: SearchResult[] = [];
		for (const m of messages) {
			const content = (m.content || '').toLowerCase();
			let pos = 0, idx = 0;
			while (true) {
				const hit = content.indexOf(lower, pos);
				if (hit === -1) break;
				const start = Math.max(0, hit - 20);
				const end = Math.min(content.length, hit + lower.length + 20);
				found.push({ messageId: m.id, index: idx++, snippet: m.content.slice(start, end) });
				pos = hit + lower.length;
			}
		}
		return found;
	}, [messages]);

	useEffect(() => {
		setResults(computeResults(query));
		setActiveIdx(0);
	}, [query, computeResults]);

	// Keyboard handler for Ctrl+F
	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
				e.preventDefault();
				setIsOpen(true);
			}
			if (isOpen && e.key === 'Escape') {
				setIsOpen(false);
			}
		};
		document.addEventListener('keydown', handler);
		return () => document.removeEventListener('keydown', handler);
	}, [isOpen]);

	const next = useCallback(() => setActiveIdx(i => Math.min(i + 1, Math.max(0, results.length - 1))), [results.length]);
	const prev = useCallback(() => setActiveIdx(i => Math.max(i - 1, 0)), []);

	return { query, setQuery, results, activeIdx, setActiveIdx, next, prev, isOpen, setIsOpen };
} 