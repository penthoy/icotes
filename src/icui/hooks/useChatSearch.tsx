import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChatMessage } from '../types/chatTypes';

export interface ChatSearchScopeOptions {
	// Return true when Chat panel should own Ctrl+F handling.
	// If not provided, defaults to always active (previous behavior).
	isActive?: () => boolean;
}

export interface SearchResult {
	messageId: string;
	index: number; // occurrence index in message
	snippet: string;
	matchStart: number; // position in original content
	matchEnd: number;
}

export interface SearchOptions {
	caseSensitive: boolean;
	useRegex: boolean;
}

export function useChatSearch(messages: ChatMessage[], scope?: ChatSearchScopeOptions) {
	const [query, setQuery] = useState('');
	const [results, setResults] = useState<SearchResult[]>([]);
	const [activeIdx, setActiveIdx] = useState(0);
	const [isOpen, setIsOpen] = useState(false);
	const [options, setOptions] = useState<SearchOptions>({
		caseSensitive: false,
		useRegex: false
	});

	const computeResults = useCallback((q: string, opts: SearchOptions): SearchResult[] => {
		if (!q.trim()) return [];
		const found: SearchResult[] = [];
		
		let searchPattern: RegExp;
		try {
			if (opts.useRegex) {
				const flags = opts.caseSensitive ? 'g' : 'gi';
				searchPattern = new RegExp(q, flags);
			} else {
				const escapedQuery = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
				const flags = opts.caseSensitive ? 'g' : 'gi';
				searchPattern = new RegExp(escapedQuery, flags);
			}
		} catch (error) {
			// Invalid regex, fall back to literal search
			const escapedQuery = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			const flags = opts.caseSensitive ? 'g' : 'gi';
			searchPattern = new RegExp(escapedQuery, flags);
		}
		
		for (const m of messages) {
			const content = m.content || '';
			let match;
			let idx = 0;
			searchPattern.lastIndex = 0; // Reset regex state
			
			while ((match = searchPattern.exec(content)) !== null) {
				const matchStart = match.index;
				const matchEnd = match.index + match[0].length;
				const start = Math.max(0, matchStart - 20);
				const end = Math.min(content.length, matchEnd + 20);
				
				found.push({
					messageId: m.id,
					index: idx++,
					snippet: content.slice(start, end),
					matchStart,
					matchEnd
				});
				
				// Prevent infinite loop with zero-width matches
				if (match[0].length === 0) {
					searchPattern.lastIndex++;
				}
			}
		}
		return found;
	}, [messages]);

	useEffect(() => {
		setResults(computeResults(query, options));
		setActiveIdx(0);
	}, [query, options, computeResults]);

	// Scroll to active result
	const scrollToActiveResult = useCallback(() => {
		if (results.length === 0 || activeIdx < 0 || activeIdx >= results.length) return;
		
		const activeResult = results[activeIdx];
		const messageElement = document.querySelector(`[data-message-id="${activeResult.messageId}"]`);
		
		if (messageElement) {
			messageElement.scrollIntoView({
				behavior: 'smooth',
				block: 'center'
			});
		}
	}, [results, activeIdx]);

	// Auto-scroll when active result changes
	useEffect(() => {
		if (isOpen && results.length > 0) {
			scrollToActiveResult();
		}
	}, [activeIdx, isOpen, results.length, scrollToActiveResult]);

	const next = useCallback(() => setActiveIdx(i => Math.min(i + 1, Math.max(0, results.length - 1))), [results.length]);
	const prev = useCallback(() => setActiveIdx(i => Math.max(i - 1, 0)), []);

	// Keyboard handler for Ctrl+F
	useEffect(() => {
			const handler = (e: KeyboardEvent) => {
				// Determine if Chat should own this key combo (context sensitive)
				const active = scope?.isActive ? scope.isActive() : true;
				// Only react to keys when chat is the active/focused surface
				if (!active) return;
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
				e.preventDefault();
				setIsOpen(true);
			}
			if (isOpen && e.key === 'Escape') {
				setIsOpen(false);
			}
			if (isOpen && e.key === 'Enter') {
				e.preventDefault();
				if (e.shiftKey) {
					prev();
				} else {
					next();
				}
			}
		};
		document.addEventListener('keydown', handler);
		return () => document.removeEventListener('keydown', handler);
		}, [isOpen, next, prev, scope?.isActive]);

	const toggleCaseSensitive = useCallback(() => {
		setOptions(prev => ({ ...prev, caseSensitive: !prev.caseSensitive }));
	}, []);

	const toggleRegex = useCallback(() => {
		setOptions(prev => ({ ...prev, useRegex: !prev.useRegex }));
	}, []);

	return {
		query,
		setQuery,
		results,
		activeIdx,
		setActiveIdx,
		next,
		prev,
		isOpen,
		setIsOpen,
		options,
		toggleCaseSensitive,
		toggleRegex,
		scrollToActiveResult
	};
} 