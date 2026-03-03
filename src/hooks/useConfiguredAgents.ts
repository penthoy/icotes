import { useState, useEffect, useRef } from 'react';

// In-memory fetch suppression + caching to prevent duplicate log spam when
// multiple components mount the hook simultaneously (e.g. chat + dropdown).
let cachedResponse: ConfiguredAgentsResponse | null = null;
let inFlight: Promise<ConfiguredAgentsResponse> | null = null;
let lastFetchTs = 0;
const CACHE_TTL_MS = 5000; // Collapse duplicate fetches in short window
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

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
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchConfiguredAgents = async (isRetry = false) => {
    setIsLoading(true);
    if (!isRetry) {
      setError(null);
      retryCount.current = 0;
    }

    const scheduleRetry = () => {
      retryCount.current += 1;
      retryTimer.current = setTimeout(() => fetchConfiguredAgents(true), RETRY_DELAY_MS);
      // stay in loading state — do NOT call setIsLoading(false)
    };

    try {
      const now = Date.now();
      if (cachedResponse?.success && cachedResponse.agents.length > 0 && (now - lastFetchTs) < CACHE_TTL_MS) {
        const data = cachedResponse;
        setAgents(data.agents);
        setSettings(data.settings || {});
        setCategories(data.categories || {});
        setIsLoading(false);
        return;
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

      if (data.success && data.agents.length > 0) {
        setAgents(data.agents);
        setSettings(data.settings || {});
        setCategories(data.categories || {});
        if ((import.meta as any).env?.VITE_DEBUG_AGENTS === 'true') {
          console.log(`✅ Agents loaded (${data.agents.length})`, { agents: data.agents, settings: data.settings, categories: data.categories });
        }
        setIsLoading(false);
      } else if (retryCount.current < MAX_RETRIES) {
        // Empty agents or failure — retry before giving up; stay in loading state
        scheduleRetry();
      } else {
        // Exhausted retries
        if (!data.success) {
          setError(data.error || 'Failed to fetch configured agents');
        }
        setAgents(data.agents ?? []);
        setSettings(data.settings || {});
        setCategories(data.categories || {});
        setIsLoading(false);
      }
    } catch (err) {
      if (retryCount.current < MAX_RETRIES) {
        scheduleRetry();
      } else {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch configured agents';
        setError(errorMessage);
        setAgents([]);
        setSettings({});
        setCategories({});
        setIsLoading(false);
        console.error('Exception while fetching configured agents:', err);
      }
    }
  };

  useEffect(() => {
    fetchConfiguredAgents();
    return () => {
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
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