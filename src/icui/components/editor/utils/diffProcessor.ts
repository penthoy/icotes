/**
 * Diff Processing Utilities
 * 
 * Handles unified diff parsing and preprocessing for syntax highlighting
 */

export interface DiffMetadata {
  added: Set<number>;
  removed: Set<number>;
  hunk: Set<number>;
  originalPath?: string;
}

export interface ProcessedDiff {
  content: string;
  metadata: DiffMetadata;
}

/**
 * Process a unified diff patch for syntax highlighting
 * 
 * Strips leading diff markers (+, -, space) from code lines and records
 * line numbers for added/removed/hunk lines to apply background decorations
 * 
 * @param patch - Raw unified diff patch string
 * @returns Processed content and metadata
 */
export function processDiffPatch(patch: string): ProcessedDiff {
  const rawLines = patch.split('\n');
  const added = new Set<number>();
  const removed = new Set<number>();
  const hunk = new Set<number>();
  const processed: string[] = [];
  
  for (const line of rawLines) {
    // Keep file headers as-is
    if (
      line.startsWith('+++ ') || line.startsWith('--- ') ||
      line.startsWith('index ') || line.startsWith('diff ') ||
      line.startsWith('new file mode') || line.startsWith('deleted file mode') ||
      line.startsWith('rename from') || line.startsWith('rename to') ||
      line.startsWith('similarity index')
    ) {
      processed.push(line);
      continue;
    }
    
    // Hunk headers
    if (line.startsWith('@@')) {
      hunk.add(processed.length + 1);
      processed.push(line);
      continue;
    }
    
    // Added lines (but not +++ header)
    if (line.startsWith('+') && !line.startsWith('+++ ')) {
      added.add(processed.length + 1);
      processed.push(line.slice(1));
      continue;
    }
    
    // Removed lines (but not --- header)
    if (line.startsWith('-') && !line.startsWith('--- ')) {
      removed.add(processed.length + 1);
      processed.push(line.slice(1));
      continue;
    }
    
    // Unchanged lines (unified diff prefix space)
    if (line.startsWith(' ')) {
      processed.push(line.slice(1));
      continue;
    }
    
    // Fallback
    processed.push(line);
  }
  
  return {
    content: processed.join('\n'),
    metadata: { added, removed, hunk }
  };
}
