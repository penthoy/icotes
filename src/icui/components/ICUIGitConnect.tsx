/**
 * ICUI Git Connect Component
 * 
 * Component displayed when no Git repository is detected.
 * Provides options to connect to GitHub and initialize a Git repository.
 */

import React, { useState, useCallback } from 'react';
import { 
  GitBranch, 
  Github, 
  ExternalLink,
  FolderGit2,
  Globe,
  Settings,
  Loader2
} from "lucide-react";
import { Button } from './ui/button';
import { backendService } from '../services';

interface ICUIGitConnectProps {
  className?: string;
  onGitInitialized?: () => void;
}

const ICUIGitConnect: React.FC<ICUIGitConnectProps> = ({
  className = '',
  onGitInitialized,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redirectWarning, setRedirectWarning] = useState<string | null>(null);

  // Check if we're in test mode
  const isTestMode = import.meta.env.VITE_TEST_GIT_CONNECT === 'true';

  const handleInitializeGit = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      if (isTestMode) {
        // Dry run mode - simulate git initialization without actually doing it
        console.log('[ICUIGitConnect] TEST MODE: Would initialize Git repository');
        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
        onGitInitialized?.();
        return;
      }
      
      // Initialize git repository
      const success = await backendService.initializeGitRepo();
      if (success) {
        onGitInitialized?.();
      } else {
        setError('Failed to initialize Git repository');
      }
    } catch (error) {
      console.error('[ICUIGitConnect] Git initialization failed:', error);
      setError(error instanceof Error ? error.message : 'Failed to initialize Git repository');
    } finally {
      setLoading(false);
    }
  }, [onGitInitialized, isTestMode]);

  const handleConnectGitHub = useCallback(() => {
    setRedirectWarning(null);
    const clientId = import.meta.env.VITE_GIT_CLIENT_ID;
    if (!clientId) {
      setError('GitHub Client ID not configured');
      return;
    }

    // Optional explicit redirect URI (must exactly match the one configured in GitHub OAuth App)
    const explicitRedirect = import.meta.env.VITE_GIT_REDIRECT_URI as string | undefined;
    // Optionally allow a list of origins (comma separated) to use dynamic origin callback
    const allowedOrigins = (import.meta.env.VITE_GIT_ALLOWED_REDIRECT_ORIGINS || '')
      .split(',')
      .map(o => o.trim())
      .filter(Boolean);

    let redirectUri: string | undefined = undefined;
    if (explicitRedirect) {
      redirectUri = explicitRedirect; // trusted env override
    } else if (allowedOrigins.includes(window.location.origin)) {
      redirectUri = `${window.location.origin}/auth/github/callback`;
    } else {
      // Omit redirect_uri param so GitHub falls back to the default configured callback
      setRedirectWarning(
        'Redirect URI not whitelisted for this origin. Using app default; configure VITE_GIT_REDIRECT_URI or add this origin in allowed list.'
      );
    }

    const params = new URLSearchParams({
      client_id: clientId,
      scope: 'repo,user:email'
    });
    if (redirectUri) params.set('redirect_uri', redirectUri);

    console.log('[ICUIGitConnect] Opening GitHub OAuth flow', { testMode: isTestMode, redirectUri: redirectUri || '(omitted -> use app default)' });
    const githubAuthUrl = `https://github.com/login/oauth/authorize?${params.toString()}`;
    window.open(githubAuthUrl, '_blank', 'width=600,height=700');
  }, [isTestMode]);

  const handleOpenGitHub = useCallback(() => {
    window.open('https://github.com', '_blank');
  }, []);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center space-x-2">
          <GitBranch className="h-4 w-4" />
          <h3 className="text-sm font-medium">Source Control</h3>
          {isTestMode && (
            <span className="text-xs bg-yellow-500 text-white px-1.5 py-0.5 rounded-full">
              TEST
            </span>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-2 bg-red-50 border-b border-red-200 dark:bg-red-900/20 dark:border-red-800">
          <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setError(null)}
            className="ml-2 h-4 w-4 p-0 text-red-600 dark:text-red-400"
          >
            ✕
          </Button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-6">
        <div className="text-center space-y-3">
          <GitBranch className="h-16 w-16 mx-auto opacity-50 text-gray-400" />
          <div>
            <h4 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No Git Repository Found
            </h4>
            <p className="text-sm text-gray-600 dark:text-gray-400 max-w-sm">
              Get started with source control by initializing a Git repository or connecting to GitHub.
            </p>
            {isTestMode && (
              <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2">
                <strong>Test Mode:</strong> Actions will be simulated (dry run)
              </p>
            )}
          </div>
        </div>

  {/* Action Buttons */}
        <div className="space-y-3 w-full max-w-xs">
          {/* Initialize Git Repository */}
          <Button
            onClick={handleInitializeGit}
            disabled={loading}
            className="w-full justify-start space-x-2"
            variant="default"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <FolderGit2 className="h-4 w-4" />
            )}
            <span>{isTestMode ? 'Test Initialize Repository' : 'Initialize Repository'}</span>
          </Button>

          {/* Connect to GitHub */}
          <Button
            onClick={handleConnectGitHub}
            className="w-full justify-start space-x-2"
            variant="outline"
          >
            <Github className="h-4 w-4" />
            <span>Connect to GitHub</span>
            <ExternalLink className="h-3 w-3 ml-auto" />
          </Button>

          {redirectWarning && (
            <div className="text-[10px] leading-snug p-2 border rounded bg-yellow-50 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300">
              {redirectWarning}
            </div>
          )}

          {/* Open GitHub */}
          <Button
            onClick={handleOpenGitHub}
            className="w-full justify-start space-x-2"
            variant="ghost"
          >
            <Globe className="h-4 w-4" />
            <span>Open GitHub.com</span>
            <ExternalLink className="h-3 w-3 ml-auto" />
          </Button>
        </div>

        {/* Help Text */}
        <div className="text-xs text-gray-500 dark:text-gray-400 text-center space-y-1 max-w-sm">
          <p>
            <strong>Initialize Repository:</strong> Create a new Git repository in the current workspace
          </p>
          <p>
            <strong>Connect to GitHub:</strong> Set up GitHub integration for collaborative development
          </p>
        </div>
      </div>
    </div>
  );
};

export default ICUIGitConnect;
