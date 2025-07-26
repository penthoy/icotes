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
      
      const response = await fetch('/api/custom-agents');
      const data: CustomAgentsResponse = await response.json();
      
      if (data.success) {
        setAgents(data.agents);
      } else {
        setError(data.error || 'Failed to fetch custom agents');
        setAgents([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch custom agents');
      setAgents([]);
    } finally {
      setIsLoading(false);
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
