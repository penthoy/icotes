import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChatMessage } from '../types/chatTypes';

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

/**
 * Chat-scoped search hook.
 *
 * Pass a `containerRef` pointing at the chat panel root element.
 * Keyboard shortcuts (Ctrl+F, Escape, Enter/Shift+Enter) are scoped to that
 * container so they don't interfere with the editor or other panels.
 */
export function useChatSearch(
	messages: ChatMessage[],
	containerRef: React.RefObject<HTMLElement | null>,
) {
	const [query, setQuery] = useState('');
	const [results, setResults] = useState<SearchResult[]>([]);
	const [activeIdx, setActiveIdx] = useState(0);
	const [isOpen, setIsOpen] = useState(false);
	const [options, setOptions] = useState<SearchOptions>({
		caseSensitive: false,
		useRegex: false
	});

	// Keep a ref in sync so keyboard handlers always see current isOpen
	const isOpenRef = useRef(isOpen);
	isOpenRef.current = isOpen;

	const searchInputRef = useRef<HTMLInputElement>(null);

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

	const open = useCallback(() => {
		setIsOpen(true);
		// Focus the search input after React renders it
		requestAnimationFrame(() => {
			searchInputRef.current?.focus();
			searchInputRef.current?.select();
		});
	}, []);

	const close = useCallback(() => {
		setIsOpen(false);
		setQuery('');
	}, []);

	// Scoped keyboard handler — attached to the container element.
	// Ctrl+F opens search when the chat panel (or any descendant) has focus.
	// Escape / Enter / Shift+Enter only fire when the search input itself is focused.
	useEffect(() => {
		const container = containerRef.current;
		if (!container) return;

		const handler = (e: KeyboardEvent) => {
			// Ctrl/Cmd+F: open search — fires for any focus inside the chat panel
			if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
				e.preventDefault();
				e.stopPropagation();
				open();
				return;
			}

			// Remaining shortcuts only apply when the search input itself is focused
			const searchFocused = searchInputRef.current && document.activeElement === searchInputRef.current;
			if (!searchFocused) return;

			if (e.key === 'Escape') {
				e.preventDefault();
				e.stopPropagation();
				close();
				return;
			}

			if (e.key === 'Enter') {
				e.preventDefault();
				if (e.shiftKey) {
					prev();
				} else {
					next();
				}
			}
		};

		container.addEventListener('keydown', handler, true); // capture phase
		return () => container.removeEventListener('keydown', handler, true);
	}, [containerRef, open, close, next, prev]);

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
		open,
		close,
		options,
		toggleCaseSensitive,
		toggleRegex,
		scrollToActiveResult,
		searchInputRef,
	};
}