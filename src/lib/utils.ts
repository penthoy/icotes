import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Explorer preferences utilities
 */
export const explorerPreferences = {
  /**
   * Get the show hidden files preference
   * @returns boolean indicating whether to show hidden files
   */
  getShowHiddenFiles(): boolean {
    try {
      const stored = localStorage.getItem('explorer.showHiddenFiles');
      return stored === 'true';
    } catch (error) {
      console.warn('Failed to read explorer preferences:', error);
      return false; // Default to hiding hidden files
    }
  },

  /**
   * Set the show hidden files preference
   * @param show - whether to show hidden files
   */
  setShowHiddenFiles(show: boolean): void {
    try {
      localStorage.setItem('explorer.showHiddenFiles', show.toString());
    } catch (error) {
      console.warn('Failed to save explorer preferences:', error);
    }
  },

  /**
   * Toggle the show hidden files preference
   * @returns the new state (true if now showing hidden files)
   */
  toggleShowHiddenFiles(): boolean {
    const currentState = this.getShowHiddenFiles();
    const newState = !currentState;
    this.setShowHiddenFiles(newState);
    return newState;
  }
};

/**
 * Check if a file is hidden (starts with dot)
 * @param filename - the filename to check
 * @returns true if the file is hidden
 */
export function isHiddenFile(filename: string): boolean {
  return filename.startsWith('.');
}
