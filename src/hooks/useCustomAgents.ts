import { useState, useEffect } from 'react';

interface CustomAgentsResponse {
  success: boolean;
  agents: string[];
  error?: string;
}

export const useCustomAgents = () => {
  const [agents, setAgents] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('🔄 [useCustomAgents] Fetching custom agents from /api/custom-agents');
      const response = await fetch('/api/custom-agents');
      console.log('📡 [useCustomAgents] Response status:', response.status);
      
      const data: CustomAgentsResponse = await response.json();
      console.log('📋 [useCustomAgents] Response data:', data);
      
      if (data.success) {
        setAgents(data.agents);
        console.log('✅ [useCustomAgents] Successfully loaded agents:', data.agents);
      } else {
        setError(data.error || 'Failed to fetch custom agents');
        setAgents([]);
        console.error('❌ [useCustomAgents] Failed to fetch agents:', data.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch custom agents');
      setAgents([]);
      console.error('💥 [useCustomAgents] Exception while fetching agents:', err);
    } finally {
      setIsLoading(false);
      console.log('🏁 [useCustomAgents] Fetch complete. Final state:', { agents, isLoading: false, error });
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  return {
    agents,
    isLoading,
    error,
    refetch: fetchAgents
  };
};
