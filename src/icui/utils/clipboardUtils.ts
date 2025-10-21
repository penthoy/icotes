/**
 * Clipboard Utilities
 * 
 * Provides cross-browser clipboard functionality with fallback support.
 * Handles cases where navigator.clipboard API is not available or fails.
 */

/**
 * Copy text to clipboard with fallback support
 * @param text The text to copy
 * @throws Error if both modern and fallback methods fail
 */
export async function copyToClipboard(text: string): Promise<void> {
  // Try modern clipboard API first
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
  } catch (error) {
    console.warn('Modern clipboard API failed, trying fallback:', error);
  }

  // Fallback to execCommand for older browsers or insecure contexts
  try {
    fallbackCopyToClipboard(text);
  } catch (error) {
    throw new Error(`Failed to copy to clipboard: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Fallback clipboard copy using deprecated execCommand
 * Works in non-secure contexts where navigator.clipboard is unavailable
 */
function fallbackCopyToClipboard(text: string): void {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  
  // Make the textarea invisible but functional
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  textArea.setAttribute('readonly', '');
  
  document.body.appendChild(textArea);
  
  try {
    // Select the text
    textArea.focus();
    textArea.select();
    
    // Try to copy
    const successful = document.execCommand('copy');
    if (!successful) {
      throw new Error('execCommand("copy") returned false');
    }
  } finally {
    // Always clean up
    document.body.removeChild(textArea);
  }
}

/**
 * Read text from clipboard
 * @returns The clipboard text, or empty string if unavailable
 */
export async function readFromClipboard(): Promise<string> {
  try {
    if (navigator?.clipboard?.readText) {
      return await navigator.clipboard.readText();
    }
  } catch (error) {
    console.warn('Failed to read from clipboard:', error);
  }
  return '';
}

/**
 * Check if clipboard API is available
 */
export function isClipboardAvailable(): boolean {
  return !!(navigator?.clipboard?.writeText);
}
