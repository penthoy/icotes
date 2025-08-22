import React, { useMemo, useState, useEffect } from 'react';
import { useChatHistory } from '../../hooks/useChatHistory';
import { useChatSessionSync } from '../../hooks/useChatSessionSync';

interface ChatHistoryProps {
	className?: string;
	onSelect?: (sessionId: string) => void;
	compact?: boolean;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({ className = '', onSelect, compact = false }) => {
	const { sessions, activeSessionId, isLoading, createSession, switchSession, renameSession, deleteSession, refreshSessions } = useChatHistory();
	const { onSessionChange, emitSessionChange } = useChatSessionSync();
	const [editingId, setEditingId] = useState<string>('');
	const [tempName, setTempName] = useState<string>('');

	useEffect(() => {
		const handler = async () => {
			try {
				await createSession('New chat');
			} catch (error) {
				console.error('Failed to create new chat session:', error);
			}
		};
		window.addEventListener('icui.chat.new' as any, handler as any);
		return () => window.removeEventListener('icui.chat.new' as any, handler as any);
	}, [createSession]);

	// Listen for session changes from other components
	useEffect(() => {
		return onSessionChange((sessionId, action, sessionName) => {
			if (action === 'create') {
				// Refresh sessions list when a new session is created from another component
				refreshSessions();
			}
		});
	}, [onSessionChange, refreshSessions]);

	const sorted = useMemo(() => sessions.slice().sort((a, b) => b.updated - a.updated), [sessions]);

	const handleCreateSession = async () => {
		try {
			await createSession('New chat');
		} catch (error) {
			console.error('Failed to create session:', error);
		}
	};

	const handleRenameSession = async (id: string, name: string) => {
		try {
			await renameSession(id, name || 'Untitled');
			setEditingId('');
			// If renaming the active session, immediately broadcast the change
			if (activeSessionId === id) {
				emitSessionChange(id, 'switch', name || 'Untitled');
			}
		} catch (error) {
			console.error('Failed to rename session:', error);
			setEditingId('');
		}
	};

	const handleDeleteSession = async (id: string) => {
		try {
			await deleteSession(id);
		} catch (error) {
			console.error('Failed to delete session:', error);
		}
	};

	if (isLoading) {
		return (
			<div className={`flex items-center justify-center p-4 ${className}`}>
				<div className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>Loading sessions...</div>
			</div>
		);
	}

	if (compact) {
		return (
			<div className={className}>
				<select
					value={activeSessionId}
					onChange={(e) => { switchSession(e.target.value); onSelect?.(e.target.value); }}
					className="text-xs px-2 py-1 rounded border"
					style={{ backgroundColor: 'var(--icui-bg-primary)', color: 'var(--icui-text-primary)', borderColor: 'var(--icui-border-subtle)' }}
				>
					{sorted.map(s => (
						<option key={s.id} value={s.id}>{s.name || 'Untitled'}</option>
					))}
				</select>
			</div>
		);
	}

	return (
		<div className={`space-y-2 ${className}`}>
			<div className="flex items-center justify-between">
				<h3 className="text-sm font-semibold" style={{ color: 'var(--icui-text-primary)' }}>Sessions</h3>
				<button
					onClick={handleCreateSession}
					className="px-2 py-1 text-xs rounded border"
					style={{
						backgroundColor: 'var(--icui-bg-secondary)',
						color: 'var(--icui-text-primary)',
						borderColor: 'var(--icui-border-subtle)'
					}}
				>
					New
				</button>
			</div>
			<div className="max-h-64 overflow-y-auto space-y-1">
				{sorted.length === 0 ? (
					<div className="text-xs" style={{ color: 'var(--icui-text-secondary)' }}>No sessions yet.</div>
				) : sorted.map(s => (
					<div key={s.id}
						className={`flex items-center justify-between px-2 py-1 rounded border ${s.id === activeSessionId ? 'ring-1' : ''}`}
						style={{
							backgroundColor: 'var(--icui-bg-primary)',
							borderColor: 'var(--icui-border-subtle)',
							color: 'var(--icui-text-primary)'
						}}
					>
						<div className="flex-1 min-w-0">
							{editingId === s.id ? (
								<input
									value={tempName}
									onChange={e => setTempName(e.target.value)}
									onBlur={() => handleRenameSession(s.id, tempName)}
									onKeyDown={(e) => {
										if (e.key === 'Enter') {
											handleRenameSession(s.id, tempName);
										} else if (e.key === 'Escape') {
											setEditingId('');
										}
									}}
									className="w-full bg-transparent text-xs outline-none"
									autoFocus
								/>
							) : (
								<button className="text-left truncate w-full" onClick={() => { switchSession(s.id); onSelect?.(s.id); }}>
									<span className="text-xs font-medium">{s.name || 'Untitled'}</span>
								</button>
							)}
							<div className="text-[10px] opacity-60">
								{new Date(s.updated).toLocaleString()}
								{s.message_count !== undefined && <span className="ml-1">({s.message_count} msgs)</span>}
							</div>
						</div>
						<div className="flex items-center gap-1">
							<button className="text-[10px] underline" onClick={() => { setEditingId(s.id); setTempName(s.name); }}>Rename</button>
							<button className="text-[10px] underline" onClick={() => handleDeleteSession(s.id)}>Delete</button>
						</div>
					</div>
				))}
			</div>
		</div>
	);
};

export default ChatHistory; 