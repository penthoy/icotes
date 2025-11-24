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
  lineNumbers?: Map<number, { old: number | null; new: number | null }>; // Maps display line to actual line numbers
}

export interface ProcessedDiff {
  content: string;
  metadata: DiffMetadata;
}

/**
 * Process a unified diff patch for syntax highlighting
 * 
 * Strips leading diff markers (+, -, space) from code lines and records
 * line numbers for added/removed/hunk lines to apply background decorations.
 * Also tracks actual line numbers from hunk headers.
 * 
 * @param patch - Raw unified diff patch string
 * @returns Processed content and metadata with line number mapping
 */
export function processDiffPatch(patch: string): ProcessedDiff {
  const rawLines = patch.split('\n');
  const added = new Set<number>();
  const removed = new Set<number>();
  const hunk = new Set<number>();
  const processed: string[] = [];
  const lineNumbers = new Map<number, { old: number | null; new: number | null }>();
  
  let oldLineNum = 0;
  let newLineNum = 0;
  let inHunk = false;
  
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
      lineNumbers.set(processed.length, { old: null, new: null });
      continue;
    }
    
    // Hunk headers - parse line numbers
    if (line.startsWith('@@')) {
      inHunk = true;
      hunk.add(processed.length + 1);
      processed.push(line);
      lineNumbers.set(processed.length, { old: null, new: null });
      
      // Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
      const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
      if (match) {
        oldLineNum = parseInt(match[1], 10);
        newLineNum = parseInt(match[2], 10);
      }
      continue;
    }
    
    if (!inHunk) {
      // Before first hunk
      processed.push(line);
      lineNumbers.set(processed.length, { old: null, new: null });
      continue;
    }
    
    // Added lines (but not +++ header)
    if (line.startsWith('+') && !line.startsWith('+++ ')) {
      added.add(processed.length + 1);
      processed.push(line.slice(1));
      lineNumbers.set(processed.length, { old: null, new: newLineNum });
      newLineNum++;
      continue;
    }
    
    // Removed lines (but not --- header)
    if (line.startsWith('-') && !line.startsWith('--- ')) {
      removed.add(processed.length + 1);
      processed.push(line.slice(1));
      lineNumbers.set(processed.length, { old: oldLineNum, new: null });
      oldLineNum++;
      continue;
    }
    
    // Unchanged lines (unified diff prefix space)
    if (line.startsWith(' ')) {
      processed.push(line.slice(1));
      lineNumbers.set(processed.length, { old: oldLineNum, new: newLineNum });
      oldLineNum++;
      newLineNum++;
      continue;
    }
    
    // Fallback
    processed.push(line);
    lineNumbers.set(processed.length, { old: null, new: null });
  }
  
  return {
    content: processed.join('\n'),
    metadata: { added, removed, hunk, lineNumbers }
  };
}
