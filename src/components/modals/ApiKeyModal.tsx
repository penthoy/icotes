import React, { useState, useEffect, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/components/ui/use-toast';
import { Eye, EyeOff, Key, Save, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { configService } from '@/services/config-service';

interface ApiKeyStatus {
  is_set: boolean;
  masked_value: string;
  length: number;
}

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface KeyConfig {
  key: string;
  label: string;
  placeholder: string;
  description: string;
}

const SITE_SETTINGS_GROUP = [
  { key: 'SITE_URL', label: 'Site URL', placeholder: 'wip.icotes.com', description: 'Domain/IP for the application (used for callbacks, webhooks, Docker deployments)' },
  { key: 'WORKSPACE_ROOT', label: 'Workspace Root', placeholder: '/app/workspace', description: 'Absolute path to workspace directory' },
  { key: 'PORT', label: 'Server Port', placeholder: '8000', description: 'Port number for backend server' },
];

const SITE_SETTING_KEYS = new Set(SITE_SETTINGS_GROUP.map(k => k.key));

const API_KEY_GROUPS: Record<string, KeyConfig[]> = {
  'AI Models': [
    { key: 'OPENROUTER_API_KEY', label: 'OpenRouter API Key', placeholder: 'sk-or-...', description: 'Access multiple AI models via OpenRouter' },
    { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...', description: 'Required for OpenAI GPT models' },
    { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', placeholder: 'sk-ant-...', description: 'For Claude models by Anthropic' },
    { key: 'GOOGLE_API_KEY', label: 'Google API Key', placeholder: 'AIza...', description: 'For Google Gemini models' },
    { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', placeholder: 'sk-...', description: 'For DeepSeek AI models' },
    { key: 'GROQ_API_KEY', label: 'Groq API Key', placeholder: 'gsk_...', description: 'For fast inference with Groq' },
    { key: 'CEREBRAS_API_KEY', label: 'Cerebras API Key', placeholder: 'csk-...', description: 'For Cerebras AI models' },
    { key: 'DASHSCOPE_API_KEY', label: 'DashScope API Key', placeholder: 'sk-...', description: 'For Alibaba Cloud AI models' },
    { key: 'MOONSHOT_API_KEY', label: 'Moonshot AI API Key', placeholder: 'sk-...', description: 'For Moonshot AI models' },
    { key: 'OLLAMA_URL', label: 'Ollama URL', placeholder: 'http://localhost:11434/v1', description: 'URL endpoint for Ollama local AI models' },
  ],
  'Services': [
    { key: 'ELEVENLABS_API_KEY', label: 'ElevenLabs API Key', placeholder: 'sk-...', description: 'For text-to-speech audio generation' },
    { key: 'ATLASCLOUD_API_KEY', label: 'AtlasCloud API Key', placeholder: 'sk-...', description: 'For video/image generation via AtlasCloud' },
    { key: 'MAILERSEND_API_KEY', label: 'MailerSend API Key', placeholder: 'mlsn...', description: 'For email notifications' },
    { key: 'PUSHOVER_USER', label: 'Pushover User Key', placeholder: 'u...', description: 'Pushover user key for notifications' },
    { key: 'PUSHOVER_TOKEN', label: 'Pushover App Token', placeholder: 'a...', description: 'Pushover application token' },
    { key: 'TAVILY_API_KEY', label: 'Tavily API Key', placeholder: 'tvly-...', description: 'For Tavily web search' },
    { key: 'SERPER_API_KEY', label: 'Serper API Key', placeholder: 'serp-...', description: 'For Google Serper search' },
  ]
};

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ isOpen, onClose }) => {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [keyStatus, setKeyStatus] = useState<Record<string, ApiKeyStatus>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [revealedValues, setRevealedValues] = useState<Record<string, string>>({});
  const inFlight = useRef<Record<string, boolean>>({});

  const getAllCanonicalKeys = (): string[] => {
    const aiKeys = API_KEY_GROUPS['AI Models'].map(k => k.key);
    const svcKeys = API_KEY_GROUPS['Services'].map(k => k.key);
    const siteKeys = SITE_SETTINGS_GROUP.map(k => k.key);
    return [...aiKeys, ...svcKeys, ...siteKeys];
  };

  useEffect(() => {
    if (isOpen) {
      loadApiKeyStatus();
    }
    // Cleanup revealed values when modal closes
    return () => {
      setRevealedValues({});
      setShowKeys({});
    };
  }, [isOpen]);

  const loadApiKeyStatus = async () => {
    setIsLoading(true);
    try {
      const config = await configService.getConfig();
      const baseUrl = config.base_url;

      // Request exactly the keys we show in the UI to avoid backend hardcoding
      const params = new URLSearchParams({ keys: getAllCanonicalKeys().join(',') });
      const response = await fetch(`${baseUrl}/api/environment/keys?${params.toString()}`);
      const data = await response.json();
      
      if (data.success) {
        setKeyStatus(data.keys);
        setRevealedValues({});
      } else {
        throw new Error(data.error || 'Failed to load environment settings status');
      }
    } catch (error) {
      console.error('❌ Failed to load environment settings status:', error);
      toast({
        title: "Error",
        description: `Failed to load environment settings status: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyChange = (key: string, value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const toggleShowKey = async (key: string) => {
    setShowKeys(prev => ({ ...prev, [key]: !prev[key] }));
    // If toggling to show and no user-entered value, try to fetch full value (dev/allowed only)
    const willShow = !showKeys[key];
    const status = keyStatus[key];
    const userEntered = (apiKeys[key] || '').length > 0;
    if (willShow && status?.is_set && !userEntered && !revealedValues[key] && !inFlight.current[key]) {
      try {
        inFlight.current[key] = true;
        const config = await configService.getConfig();
        const baseUrl = config.base_url;
        const resp = await fetch(`${baseUrl}/api/environment/key?key=${encodeURIComponent(key)}`);
        const data = await resp.json();
        if (resp.ok && data.success && typeof data.value === 'string') {
          setRevealedValues(prev => ({ ...prev, [key]: data.value }));
        } else {
          // Notify user once per session if reveal is blocked
          toast({
            title: 'Reveal disabled',
            description: 'To reveal full values, enable ALLOW_KEY_REVEAL=true or run backend in development. Masked values will be shown instead.',
            duration: 4000
          });
        }
      } catch {
        toast({
          title: 'Reveal failed',
          description: 'Could not fetch full value. Showing masked value instead.',
          duration: 3000
        });
      } finally {
        inFlight.current[key] = false;
      }
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Only send keys that have been modified
      const keysToUpdate = Object.entries(apiKeys).reduce((acc, [key, value]) => {
        if (value && value.trim()) {
          acc[key] = value.trim();
        }
        return acc;
      }, {} as Record<string, string>);

      if (Object.keys(keysToUpdate).length === 0) {
        toast({
          title: "No Changes",
          description: "No environment settings were modified.",
          duration: 3000,
        });
        return;
      }

      const config = await configService.getConfig();
      const baseUrl = config.base_url;
      
      const response = await fetch(`${baseUrl}/api/environment/update-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          api_keys: keysToUpdate
        }),
      });

      const data = await response.json();
      
      if (data.success) {
        toast({
          title: "Settings Updated",
          description: data.message || `Updated ${data.updated_keys?.length || 0} environment settings successfully.`,
          duration: 3000,
        });

        // Clear the input fields
        setApiKeys({});
        
        // Reload the status to show updated masked values
        await loadApiKeyStatus();
        
      } else {
        throw new Error(data.error || 'Failed to update environment settings');
      }
    } catch (error) {
      console.error('❌ Failed to update environment settings:', error);
      toast({
        title: "Update Failed",
        description: `Failed to update environment settings: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
        duration: 5000,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const renderKeyInput = (keyConfig: KeyConfig) => {
    const { key, label, placeholder, description } = keyConfig;
    const status = keyStatus[key];
    const currentValue = apiKeys[key] || '';
    const isVisible = showKeys[key] || false;

    // Site settings keys (SITE_URL, WORKSPACE_ROOT, PORT) are plain text fields
    const isSiteSettingKey = SITE_SETTING_KEYS.has(key);

    // Compute what to show in the input box
    // - If the user typed something, respect that (always editable)
    // - For site settings: show the current value when available
    // - For secret keys: never put masked values into the editable input (prevents saving masked text back)
    //   - If reveal is enabled and the value was fetched, show the revealed value when visible
    // - Otherwise, keep empty and rely on placeholder
    let effectiveValue = currentValue;
    if (!currentValue && status?.is_set) {
      if (isSiteSettingKey) {
        effectiveValue = revealedValues[key] ?? status.masked_value ?? '';
      } else if (isVisible) {
        effectiveValue = revealedValues[key] ?? '';
      } else {
        effectiveValue = '';
      }
    }

    return (
      <div key={key} className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor={key} className="text-sm font-medium">
            {label}
          </Label>
          <div className="flex items-center space-x-2">
            {status?.is_set && (
              <div className="flex items-center space-x-1 text-xs text-green-600">
                <CheckCircle className="w-3 h-3" />
                <span>Set ({status.length} chars)</span>
              </div>
            )}
            {!status?.is_set && (
              <div className="flex items-center space-x-1 text-xs text-orange-600">
                <AlertCircle className="w-3 h-3" />
                <span>Not set</span>
              </div>
            )}
          </div>
        </div>
        
        <div className="relative">
          <Input
            id={key}
            type={isSiteSettingKey || isVisible ? "text" : "password"}
            placeholder={status?.is_set ? status.masked_value : placeholder}
            value={effectiveValue}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            onChange={(e) => handleKeyChange(key, e.target.value)}
            className={isSiteSettingKey ? "text-sm" : "pr-10 text-sm"}
          />
          {!isSiteSettingKey && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
              onClick={() => toggleShowKey(key)}
              aria-label={isVisible ? `Hide ${label}` : `Show ${label}`}
              title={isVisible ? 'Hide value' : 'Show value'}
            >
              {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </Button>
          )}
        </div>
        
        <p className="text-xs text-gray-500">{description}</p>
      </div>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Key className="w-5 h-5" />
            <span>Environment</span>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            <span>Loading environment settings...</span>
          </div>
        ) : (
          <div className="space-y-6">
            <Tabs defaultValue="site-settings" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="site-settings">Site Settings</TabsTrigger>
                <TabsTrigger value="ai-models">AI Models</TabsTrigger>
                <TabsTrigger value="services">Services</TabsTrigger>
              </TabsList>

              <TabsContent value="site-settings" className="space-y-4 mt-6">
                {SITE_SETTINGS_GROUP.map(renderKeyInput)}
              </TabsContent>

              <TabsContent value="ai-models" className="space-y-4 mt-6">
                {API_KEY_GROUPS['AI Models'].map(renderKeyInput)}
              </TabsContent>

              <TabsContent value="services" className="space-y-4 mt-6">
                {API_KEY_GROUPS['Services'].map(renderKeyInput)}
              </TabsContent>
            </Tabs>
          </div>
        )}

        <DialogFooter className="flex items-center justify-between">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <div className="flex space-x-2">
            <Button variant="outline" onClick={loadApiKeyStatus} disabled={isLoading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button onClick={handleSave} disabled={isSaving || isLoading}>
              {isSaving ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Settings
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}; 