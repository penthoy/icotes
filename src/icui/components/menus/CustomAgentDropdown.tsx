import React, { useState, useEffect } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { RefreshCw, Settings } from 'lucide-react';
import { useConfiguredAgents, ConfiguredAgent } from '@/hooks/useConfiguredAgents';
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket';
import { toast } from '@/components/ui/use-toast';
import { ApiKeyModal } from '@/components/modals/ApiKeyModal';

interface CustomAgentDropdownProps {
  selectedAgent: string;
  onAgentChange: (agent: string) => void;
  className?: string;
  disabled?: boolean;
  showCategories?: boolean;
  showDescriptions?: boolean;
}

/**
 * Custom Agent Dropdown Component
 * 
 * Features workspace-controlled agent configuration with:
 * - Custom display names and icons
 * - Categories and descriptions  
 * - Hot reload functionality
 * - Workspace .icotes/agents.json configuration
 */
export const CustomAgentDropdown: React.FC<CustomAgentDropdownProps> = ({
  selectedAgent,
  onAgentChange,
  className = '',
  disabled = false,
  showCategories = true,
  showDescriptions = true,
}) => {
  const { agents, settings, isLoading, error, refetch, getAgentsByCategory, getSortedCategories } = useConfiguredAgents();
  const [isReloading, setIsReloading] = useState(false);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);

  // WebSocket auto-refresh
  const { isConnected } = useAgentWebSocket({
    onAgentsReloaded: async (reloadedAgents) => {
      console.log('🔄 Auto-refreshing agents due to WebSocket event:', reloadedAgents);
      
      // Show toast notification
      toast({
        title: "Agents Updated",
        description: `${reloadedAgents.length} agents were automatically reloaded.`,
        duration: 3000,
      });
      
      // Refresh the agent list
      await refetch();
    },
    onError: (error) => {
      console.warn('WebSocket error:', error);
      // Don't show error toast for WebSocket issues as it's not critical
    },
    enabled: true
  });

  // Set default agent when agents and settings are loaded
  useEffect(() => {
    if (!isLoading && agents.length > 0 && settings?.defaultAgent && !selectedAgent) {
      // Check if the default agent exists in the available agents
      const defaultAgentExists = agents.some(agent => agent.name === settings.defaultAgent);
      if (defaultAgentExists) {
        onAgentChange(settings.defaultAgent);
        console.log(`🎯 Set default agent: ${settings.defaultAgent}`);
      }
    }
  }, [agents, settings, isLoading, selectedAgent, onAgentChange]);

  const handleReload = async () => {
    setIsReloading(true);
    try {
      // Call the reload endpoint first
      const response = await fetch('/api/custom-agents/reload', { method: 'POST' });
      const result = await response.json();
      
      if (result.success) {
        // Show success toast
        toast({
          title: "Agents Reloaded",
          description: result.message || `Successfully reloaded ${result.agents?.length || 0} agents.`,
          duration: 3000,
        });
        
        // Then refetch the configured agents
        await refetch();
        
        console.log('🔄 Agents reloaded successfully:', result.agents);
      } else {
        throw new Error(result.error || 'Failed to reload agents');
      }
    } catch (error) {
      console.error('❌ Failed to reload agents:', error);
      
      // Show error toast
      toast({
        title: "Reload Failed",
        description: `Failed to reload agents: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
        duration: 5000,
      });
    } finally {
      setIsReloading(false);
    }
  };

  // Find the selected agent's display info
  const selectedAgentInfo = agents.find(agent => agent.name === selectedAgent);
  const selectedDisplayName = selectedAgentInfo?.displayName || selectedAgent;
  const selectedIcon = selectedAgentInfo?.icon || '';

  // Handle loading state
  if (isLoading) {
    return (
      <div className={`flex items-center justify-start gap-2 ${className}`}>
        <div className="flex items-center space-x-2 px-2 py-1 text-xs">
          <div className="w-3 h-3 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
          <span className="text-xs">Loading agents...</span>
        </div>
      </div>
    );
  }

  // Handle error state - fall back to showing selected agent without dropdown
  if (error) {
    return (
      <div className={`flex items-center justify-start gap-2 ${className}`}>
        <div className="flex items-center space-x-2 px-2 py-1 text-xs">
          <span className="text-xs">{selectedIcon}</span>
          <span className="text-xs">{selectedDisplayName}</span>
          <span className="text-xs text-red-500" title={`Failed to load configured agents: ${error}`}>⚠</span>
        </div>
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReload}
            disabled={isReloading}
            className="h-7 w-7 p-0"
            title={`Reload agents${isConnected ? ' (Auto-refresh enabled)' : ' (Manual only)'}`}
          >
            <RefreshCw className={`h-3 w-3 ${isReloading ? 'animate-spin' : ''}`} />
          </Button>
          <div 
            className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-400'
            }`}
            title={isConnected ? 'Auto-refresh connected' : 'Auto-refresh disconnected'}
          />
        </div>
      </div>
    );
  }

  // Handle empty agents state
  if (agents.length === 0) {
    return (
      <div className={`flex items-center justify-start gap-2 ${className}`}>
        <div className="flex items-center space-x-2 px-2 py-1 text-xs">
          <span className="text-xs">No agents available</span>
        </div>
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReload}
            disabled={isReloading}
            className="h-7 w-7 p-0"
            title={`Reload agents${isConnected ? ' (Auto-refresh enabled)' : ' (Manual only)'}`}
          >
            <RefreshCw className={`h-3 w-3 ${isReloading ? 'animate-spin' : ''}`} />
          </Button>
          <div 
            className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-400'
            }`}
            title={isConnected ? 'Auto-refresh connected' : 'Auto-refresh disconnected'}
          />
        </div>
      </div>
    );
  }

  const renderAgentsByCategory = () => {
    if (!showCategories) {
      // Simple flat list
      return agents.map((agent) => (
        <SelectItem 
          key={agent.name} 
          value={agent.name}
          className="text-xs hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 px-3 py-2 cursor-pointer"
        >
          <div className="flex items-center space-x-2 w-full">
            <span className="text-sm">{agent.icon}</span>
            <div className="flex flex-col items-start">
              <span className="font-medium text-xs">{agent.displayName}</span>
              {showDescriptions && agent.description && (
                <span className="text-xs text-gray-500 dark:text-gray-400">{agent.description}</span>
              )}
            </div>
          </div>
        </SelectItem>
      ));
    }

    // Grouped by category
    const agentsByCategory = getAgentsByCategory();
    const categories = getSortedCategories();

    return categories.map((category, categoryIndex) => (
      <div key={category}>
        {categoryIndex > 0 && <div className="h-px bg-gray-200 dark:bg-gray-700 mx-2 my-1" />}
        <div className="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
          {category}
        </div>
        {agentsByCategory[category]?.map((agent) => (
          <SelectItem 
            key={agent.name} 
            value={agent.name}
            className="text-xs hover:bg-gray-100 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 px-3 py-2 cursor-pointer ml-2"
          >
            <div className="flex items-center space-x-2 w-full">
              <span className="text-sm">{agent.icon}</span>
              <div className="flex flex-col items-start">
                <span className="font-medium text-xs">{agent.displayName}</span>
                {showDescriptions && agent.description && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">{agent.description}</span>
                )}
              </div>
            </div>
          </SelectItem>
        ))}
      </div>
    ));
  };

  return (
    <div className={`flex items-center justify-start gap-1 ${className}`}>
      <Select value={selectedAgent} onValueChange={onAgentChange} disabled={disabled}>
        <SelectTrigger className="w-auto min-w-[180px] h-7 text-xs bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-600 focus:bg-gray-100 dark:focus:bg-gray-600 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 px-2 rounded-md cursor-pointer transition-colors">
          <SelectValue placeholder="Select an agent">
            <div className="flex items-center space-x-2">
              {selectedIcon && <span className="text-sm">{selectedIcon}</span>}
              <span className="text-xs font-medium">{selectedDisplayName}</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        
        <SelectContent className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 shadow-lg rounded-md min-w-[250px] max-w-[350px] z-50">
          {renderAgentsByCategory()}
        </SelectContent>
      </Select>
      
      <div className="relative">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleReload}
          disabled={isReloading}
          className="h-7 w-7 p-0 hover:bg-gray-100 dark:hover:bg-gray-600"
          title={`Reload agents${isConnected ? ' (Auto-refresh enabled)' : ' (Manual only)'}`}
        >
          <RefreshCw className={`h-3 w-3 ${isReloading ? 'animate-spin' : ''}`} />
        </Button>
        {/* WebSocket connection indicator */}
        <div 
          className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-gray-400'
          }`}
          title={isConnected ? 'Auto-refresh connected' : 'Auto-refresh disconnected'}
        />
      </div>
      
      <Button
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0 hover:bg-gray-100 dark:hover:bg-gray-600"
        title="Configure API keys"
        onClick={() => setIsApiKeyModalOpen(true)}
      >
        <Settings className="h-3 w-3" />
      </Button>
      
      <ApiKeyModal 
        isOpen={isApiKeyModalOpen} 
        onClose={() => setIsApiKeyModalOpen(false)} 
      />
    </div>
  );
}; 