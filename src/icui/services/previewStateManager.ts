/**
 * Preview State Manager
 * 
 * Manages preview state persistence across component unmount/remount cycles.
 * This ensures that when a Live Preview panel is dragged between dock areas,
 * the preview content (iframe URL, project state, etc.) is preserved.
 */

interface PreviewProject {
  id: string;
  files: Record<string, string>;
  projectType: string;
  status: 'building' | 'ready' | 'error';
  url?: string;
  error?: string;
}

interface PreviewState {
  currentProject: PreviewProject | null;
  previewUrl: string;
  error: string | null;
  isLoading: boolean;
  connectionStatus: boolean;
}

interface PreviewStateUpdate {
  currentProject?: PreviewProject | null;
  previewUrl?: string;
  error?: string | null;
  isLoading?: boolean;
  connectionStatus?: boolean;
}

class PreviewStateManager {
  private static instance: PreviewStateManager | null = null;
  private state: PreviewState;
  private listeners: Set<(state: PreviewState) => void>;
  private readonly STORAGE_KEY = 'icui-preview-state';

  private constructor() {
    this.listeners = new Set();
    this.state = this.loadFromStorage();
  }

  static getInstance(): PreviewStateManager {
    if (!PreviewStateManager.instance) {
      PreviewStateManager.instance = new PreviewStateManager();
    }
    return PreviewStateManager.instance;
  }

  private loadFromStorage(): PreviewState {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          currentProject: parsed.currentProject || null,
          previewUrl: parsed.previewUrl || '',
          error: null, // Don't persist errors
          isLoading: false, // Don't persist loading state
          connectionStatus: false, // Will be updated by component
        };
      }
    } catch (error) {
      console.warn('Failed to load preview state from storage:', error);
    }

    return {
      currentProject: null,
      previewUrl: '',
      error: null,
      isLoading: false,
      connectionStatus: false,
    };
  }

  private saveToStorage(): void {
    try {
      // Only persist the data that should survive across sessions
      const persistentState = {
        currentProject: this.state.currentProject,
        previewUrl: this.state.previewUrl,
      };
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(persistentState));
    } catch (error) {
      console.warn('Failed to save preview state to storage:', error);
    }
  }

  getState(): PreviewState {
    return { ...this.state };
  }

  updateState(updates: PreviewStateUpdate): void {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...updates };
    
    // Save to storage for persistence
    this.saveToStorage();
    
    // Notify listeners only if state actually changed
    if (JSON.stringify(prevState) !== JSON.stringify(this.state)) {
      this.notifyListeners();
    }
  }

  subscribe(listener: (state: PreviewState) => void): () => void {
    this.listeners.add(listener);
    
    // Immediately notify the new listener with current state
    listener(this.getState());
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifyListeners(): void {
    const currentState = this.getState();
    this.listeners.forEach(listener => {
      try {
        listener(currentState);
      } catch (error) {
        console.error('Error in preview state listener:', error);
      }
    });
  }

  // Clear all state (for manual clear operations)
  clearState(): void {
    this.state = {
      currentProject: null,
      previewUrl: '',
      error: null,
      isLoading: false,
      connectionStatus: false,
    };
    this.saveToStorage();
    this.notifyListeners();
  }

  // Check if there's a persisted preview available
  hasPersistedPreview(): boolean {
    return !!(this.state.currentProject && this.state.previewUrl);
  }
}

// Export singleton instance
export const previewStateManager = PreviewStateManager.getInstance();
export type { PreviewState, PreviewProject, PreviewStateUpdate };