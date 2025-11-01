import React from 'react';
import ToolCallWidget from '../components/chat/ToolCallWidget';
import FileEditWidget from '../components/chat/widgets/FileEditWidget';
import CodeExecutionWidget from '../components/chat/widgets/CodeExecutionWidget';
import SemanticSearchWidget from '../components/chat/widgets/SemanticSearchWidget';
import ProgressWidget from '../components/chat/widgets/ProgressWidget';
import WebSearchWidget from '../components/chat/widgets/WebSearchWidget';
import ImageGenerationWidget from '../components/chat/widgets/ImageGenerationWidget';
import { WebFetchWidget } from '../components/chat/widgets/WebFetchWidget';

// Minimal widget registry for tool call visualization
export interface ToolCallWidgetComponentProps {
	toolCall: any;
	className?: string;
	expandable?: boolean;
	defaultExpanded?: boolean;
	onRetry?: (toolId: string) => void;
}

export interface WidgetConfig {
	toolName: string;
	component: React.ComponentType<ToolCallWidgetComponentProps>;
	category?: 'file' | 'code' | 'data' | 'network' | 'custom';
	priority?: number;
}

const registry = new Map<string, React.ComponentType<ToolCallWidgetComponentProps>>();

// Auto-register built-in widgets
const builtInWidgets: WidgetConfig[] = [
	{
		toolName: 'file_edit',
		component: FileEditWidget as any,
		category: 'file',
		priority: 1
	},
	{
		toolName: 'edit_file',
		component: FileEditWidget as any,
		category: 'file',
		priority: 1
	},
	{
		toolName: 'code_execution',
		component: CodeExecutionWidget as any,
		category: 'code',
		priority: 1
	},
	{
		toolName: 'run_code',
		component: CodeExecutionWidget as any,
		category: 'code',
		priority: 1
	},
	{
		toolName: 'execute_python',
		component: CodeExecutionWidget as any,
		category: 'code',
		priority: 1
	},
	{
		toolName: 'run_in_terminal',
		component: CodeExecutionWidget as any,
		category: 'code',
		priority: 1
	},
	{
		toolName: 'semantic_search',
		component: SemanticSearchWidget as any,
		category: 'data',
		priority: 1
	},
	{
		toolName: 'search',
		component: SemanticSearchWidget as any,
		category: 'data',
		priority: 1
	},
	{
		toolName: 'progress',
		component: ProgressWidget as any,
		category: 'custom',
		priority: 1
	},
	{
		toolName: 'processing',
		component: ProgressWidget as any,
		category: 'custom',
		priority: 1
	}
	,
	{
		toolName: 'web_search',
		component: WebSearchWidget as any,
		category: 'network',
		priority: 1
	},
	{
		toolName: 'web_fetch',
		component: WebFetchWidget as any,
		category: 'network',
		priority: 1
	},
	{
		toolName: 'fetch_url',
		component: WebFetchWidget as any,
		category: 'network',
		priority: 1
	},
	{
		toolName: 'generate_image',
		component: ImageGenerationWidget as any,
		category: 'custom',
		priority: 1
	}
];

// Register built-in widgets
builtInWidgets.forEach(config => {
	registry.set(config.toolName, config.component);
});

export function registerWidget(config: WidgetConfig): void {
	if (!config?.toolName || !config?.component) return;
	registry.set(config.toolName, config.component);
}

export function getWidgetForTool(toolName?: string): React.ComponentType<ToolCallWidgetComponentProps> {
	if (toolName && registry.has(toolName)) return registry.get(toolName)!;
	return ToolCallWidget as unknown as React.ComponentType<ToolCallWidgetComponentProps>;
}

export function listRegisteredWidgets(): string[] {
	return Array.from(registry.keys());
}

// Test-only helper
export function __clearWidgetRegistry(): void {
	registry.clear();
	// Re-register built-in widgets
	builtInWidgets.forEach(config => {
		registry.set(config.toolName, config.component);
	});
} 