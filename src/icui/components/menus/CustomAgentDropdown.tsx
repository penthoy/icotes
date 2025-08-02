import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCustomAgents } from '@/hooks/useCustomAgents';

interface CustomAgentDropdownProps {
  selectedAgent: string;
  onAgentChange: (agent: string) => void;
  className?: string;
  disabled?: boolean;
}

/**
 * Custom Agent Dropdown Component
 * 
 * A dropdown component for selecting custom agents, similar to GitHub Copilot's agent selector.
 * This component fetches available custom agents from the `/api/custom-agents` endpoint
 * and provides a clean dropdown interface for agent selection.
 */
export const CustomAgentDropdown: React.FC<CustomAgentDropdownProps> = ({
  selectedAgent,
  onAgentChange,
  className = '',
  disabled = false,
}) => {
  const { agents, isLoading, error } = useCustomAgents();

  // Handle loading state
  if (isLoading) {
    return (
      <div className={`flex items-center justify-start ${className}`}>
        <div className="flex items-center space-x-2 px-2 py-1 text-xs">
          <div className="w-3 h-3 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
          <span className="text-xs">Loading...</span>
        </div>
      </div>
    );
  }

  // Handle error state - fall back to showing selected agent without dropdown
  if (error) {
    return (
      <div className={`flex items-center justify-start ${className}`}>
        <div className="flex items-center space-x-2 px-2 py-1 text-xs">
          <div className="w-3 h-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full" />
          <span className="text-xs">{selectedAgent || 'Default Agent'}</span>
          <span className="text-xs text-red-500" title="Failed to load custom agents">⚠</span>
        </div>
      </div>
    );
  }

  // Handle empty agents state - show selected agent without dropdown
  if (agents.length === 0) {
    return (
      <div className={`flex items-center justify-start ${className}`}>
        <div className="flex items-center space-x-2 px-2 py-1 text-xs">
          <div className="w-3 h-3 bg-yellow-500 rounded-full" />
          <span className="text-xs">{selectedAgent || 'Default Agent'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex items-center justify-start ${className}`}>
      <Select value={selectedAgent} onValueChange={onAgentChange} disabled={disabled}>
        <SelectTrigger className="w-auto min-w-[180px] h-7 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 focus:bg-gray-100 dark:focus:bg-gray-600 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 px-2 rounded-md cursor-pointer transition-colors">
          <SelectValue placeholder="Select an agent">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full" />
              <span className="text-xs">{selectedAgent || 'Select Agent'}</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        
        <SelectContent className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 shadow-lg rounded-md min-w-[200px] z-50">
          {agents.map((agent) => (
            <SelectItem 
              key={agent} 
              value={agent}
              className="text-xs hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 px-3 py-2 cursor-pointer"
            >
              <div className="flex items-center space-x-2 w-full">
                <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full" />
                <span className="font-medium">{agent}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};
