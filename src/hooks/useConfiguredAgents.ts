import { useState, useEffect } from 'react';

// In-memory fetch suppression + caching to prevent duplicate log spam when
// multiple components mount the hook simultaneously (e.g. chat + dropdown).
let cachedResponse: ConfiguredAgentsResponse | null = null;
let inFlight: Promise<ConfiguredAgentsResponse> | null = null;
let lastFetchTs = 0;
const CACHE_TTL_MS = 5000; // Collapse duplicate fetches in short window

export interface ConfiguredAgent {
  name: string;
  displayName: string;
  description: string;
  category: string;
  order: number;
  icon: string;
}

interface ConfiguredAgentsResponse {
  success: boolean;
  agents: ConfiguredAgent[];
  settings?: {
    defaultAgent?: string;
    showCategories?: boolean;
    showDescriptions?: boolean;
    autoReloadOnChange?: boolean;
  };
  categories?: {
    [categoryName: string]: {
      icon?: string;
      order?: number;
    };
  };
  error?: string;
  message?: string;
}

export const useConfiguredAgents = () => {
  const [agents, setAgents] = useState<ConfiguredAgent[]>([]);
  const [settings, setSettings] = useState<ConfiguredAgentsResponse['settings']>({});
  const [categories, setCategories] = useState<ConfiguredAgentsResponse['categories']>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConfiguredAgents = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const now = Date.now();
      if (cachedResponse?.success && (now - lastFetchTs) < CACHE_TTL_MS) {
        const data = cachedResponse;
        setAgents(data.agents);
        setSettings(data.settings || {});
        setCategories(data.categories || {});
        return; // Silent reuse – original logs only on fresh network fetch
      }

      if (!inFlight) {
        const p = (async () => {
          const response = await fetch('/api/custom-agents/configured');
          if (!response.ok) {
            let errBody: any = null;
            try {
              errBody = await response.json();
            } catch {
              // ignore parse error
            }
            return {
              success: false,
              error: errBody?.error || `Failed to fetch configured agents (HTTP ${response.status})`
            } as ConfiguredAgentsResponse;
          }
          const data: ConfiguredAgentsResponse = await response.json();
          if (data.success) {
            cachedResponse = data;
            lastFetchTs = Date.now();
          }
          return data;
        })();
        inFlight = p;
        p.finally(() => {
          if (inFlight === p) inFlight = null;
        });
      }

      const data = await inFlight!;
      
      if (data.success) {
        setAgents(data.agents);
        setSettings(data.settings || {});
        setCategories(data.categories || {});
        if ((import.meta as any).env?.VITE_DEBUG_AGENTS === 'true') {
          console.log(`✅ Agents loaded (${data.agents.length})`, { agents: data.agents, settings: data.settings, categories: data.categories });
        }
      } else {
        setError(data.error || 'Failed to fetch configured agents');
        setAgents([]);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch configured agents';
      setError(errorMessage);
      setAgents([]);
      console.error('Exception while fetching configured agents:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfiguredAgents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once per mounting set; cache prevents duplicate network trips

  // Group agents by category
  const getAgentsByCategory = () => {
    const grouped: Record<string, ConfiguredAgent[]> = {};
    
    agents.forEach(agent => {
      if (!grouped[agent.category]) {
        grouped[agent.category] = [];
      }
      grouped[agent.category].push(agent);
    });
    
    // Sort agents within each category by order, then by displayName
    Object.keys(grouped).forEach(category => {
      grouped[category].sort((a, b) => {
        if (a.order !== b.order) {
          return a.order - b.order;
        }
        return a.displayName.localeCompare(b.displayName);
      });
    });
    
    return grouped;
  };

  // Get categories sorted by their order
  const getSortedCategories = () => {
    const categoryNames = [...new Set(agents.map(agent => agent.category))];
    
    // Sort categories by their order from the configuration
    return categoryNames.sort((a, b) => {
      const orderA = categories[a]?.order ?? 999; // Default high order if not specified
      const orderB = categories[b]?.order ?? 999;
      
      // If orders are the same, fall back to alphabetical
      if (orderA === orderB) {
        return a.localeCompare(b);
      }
      
      return orderA - orderB;
    });
  };

  return {
    agents,
    settings,
    categories,
    isLoading,
    error,
    refetch: fetchConfiguredAgents,
    getAgentsByCategory,
    getSortedCategories
  };
}; 