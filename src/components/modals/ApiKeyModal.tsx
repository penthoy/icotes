import React, { useState, useEffect } from 'react';
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

const API_KEY_GROUPS = {
  'AI Models': [
    { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', placeholder: 'sk-...', description: 'Required for OpenAI GPT models' },
    { key: 'OPENROUTER_API_KEY', label: 'OpenRouter API Key', placeholder: 'sk-or-...', description: 'Access multiple AI models via OpenRouter' },
    { key: 'GOOGLE_API_KEY', label: 'Google API Key', placeholder: 'AIza...', description: 'For Google Gemini models' },
    { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', placeholder: 'sk-...', description: 'For DeepSeek AI models' },
    { key: 'GROQ_API_KEY', label: 'Groq API Key', placeholder: 'gsk_...', description: 'For fast inference with Groq' },
    { key: 'DASHSCOPE_API_KEY', label: 'DashScope API Key', placeholder: 'sk-...', description: 'For Alibaba Cloud AI models' },
  ],
  'Services': [
    { key: 'MAILERSEND_API_KEY', label: 'MailerSend API Key', placeholder: 'mlsn...', description: 'For email notifications' },
    { key: 'PUSHOVER_USER', label: 'Pushover User Key', placeholder: 'u...', description: 'Pushover user key for notifications' },
    { key: 'PUSHOVER_TOKEN', label: 'Pushover App Token', placeholder: 'a...', description: 'Pushover application token' },
  ]
};

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ isOpen, onClose }) => {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [keyStatus, setKeyStatus] = useState<Record<string, ApiKeyStatus>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadApiKeyStatus();
    }
  }, [isOpen]);

  const loadApiKeyStatus = async () => {
    setIsLoading(true);
    try {
      const config = await configService.getConfig();
      const baseUrl = config.base_url;
      
      const response = await fetch(`${baseUrl}/api/environment/keys`);
      const data = await response.json();
      
      if (data.success) {
        setKeyStatus(data.keys);
        console.log('✅ Loaded API key status:', data.keys);
      } else {
        throw new Error(data.error || 'Failed to load API key status');
      }
    } catch (error) {
      console.error('❌ Failed to load API key status:', error);
      toast({
        title: "Error",
        description: `Failed to load API key status: ${error instanceof Error ? error.message : 'Unknown error'}`,
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

  const toggleShowKey = (key: string) => {
    setShowKeys(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
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
          description: "No API keys were modified.",
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
          title: "API Keys Updated",
          description: data.message || `Updated ${data.updated_keys?.length || 0} API keys successfully.`,
          duration: 3000,
        });

        // Clear the input fields
        setApiKeys({});
        
        // Reload the status to show updated masked values
        await loadApiKeyStatus();
        
        console.log('✅ API keys updated:', data.updated_keys);
      } else {
        throw new Error(data.error || 'Failed to update API keys');
      }
    } catch (error) {
      console.error('❌ Failed to update API keys:', error);
      toast({
        title: "Update Failed",
        description: `Failed to update API keys: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
        duration: 5000,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const renderKeyInput = (keyConfig: typeof API_KEY_GROUPS['AI Models'][0]) => {
    const { key, label, placeholder, description } = keyConfig;
    const status = keyStatus[key];
    const currentValue = apiKeys[key] || '';
    const isVisible = showKeys[key] || false;

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
            type={isVisible ? "text" : "password"}
            placeholder={status?.is_set ? status.masked_value : placeholder}
            value={currentValue}
            onChange={(e) => handleKeyChange(key, e.target.value)}
            className="pr-10 text-sm"
          />
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
            onClick={() => toggleShowKey(key)}
          >
            {isVisible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </Button>
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
            <span>API Key Management</span>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 animate-spin mr-2" />
            <span>Loading API key status...</span>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-blue-800">
                  <p className="font-medium mb-1">Hot Reload Enabled</p>
                  <p>API keys are updated in real-time without server restart. Only enter keys you want to update or add.</p>
                </div>
              </div>
            </div>

            <Tabs defaultValue="ai-models" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="ai-models">AI Models</TabsTrigger>
                <TabsTrigger value="services">Services</TabsTrigger>
              </TabsList>

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
                  Save Keys
                </>
              )}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}; 