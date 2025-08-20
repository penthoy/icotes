/**
 * GPT-5 Model Helper
 * 
 * Contains GPT-5 specific parsing logic and helper functions for:
 * - Tool execution text parsing
 * - Tool call extraction from message content
 * - Tool name mapping and categorization
 * - Content cleaning and formatting
 * - Widget data parsing
 */

import { ChatMessage as ChatMessageType, ToolCallMeta } from '../../../types/chatTypes';
import { ToolCallData } from '../ToolCallWidget';

export interface ModelHelper {
  stripAllToolText(text: string): string;
  parseToolCalls(content: string, message: ChatMessageType): { content: string; toolCalls: ToolCallData[] };
  tryParseArgs(text: string): any;
  mapToolNameToCategory(toolName: string): { category: 'file' | 'code' | 'data' | 'network' | 'custom'; mappedName: string };
  parseFileEditData(toolCall: ToolCallData): any;
  parseCodeExecutionData(toolCall: ToolCallData): any;
  parseSemanticSearchData(toolCall: ToolCallData): any;
}

export class GPT5ModelHelper implements ModelHelper {
  
  /**
   * Remove GPT-5 specific tool execution text blocks and executing indicators
   */
  stripAllToolText(text: string): string {
    return text
      .replace(/🔧\s*\*\*Executing tools\.\.\.\*\*[\s\S]*?🔧\s*\*\*Tool execution complete\. Continuing\.\.\.\*\*/g, '')
      .replace(/🔧\s*\*\*Executing tools\.\.\.\*\*\s*\n?/g, '')
      .trim();
  }

  /**
   * Try to parse GPT-5 style arguments (supports both JSON and python-like dicts)
   */
  tryParseArgs(text: string): any {
    try {
      // Quick path: valid JSON
      return JSON.parse(text);
    } catch {}
    try {
      // Replace single quotes with double quotes and quote bare keys
      const quotedKeys = text
        .replace(/([\{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*):/g, '$1"$2"$3')
        .replace(/'/g, '"');
      return JSON.parse(quotedKeys);
    } catch {
      // Fallback: extract common fields from python-like dict string
      const fallback: any = { raw: text };
      const filePathMatch = text.match(/["']filePath["']\s*:\s*["']([^"']+)["']/);
      if (filePathMatch) fallback.filePath = filePathMatch[1];
      const startLineMatch = text.match(/["']startLine["']\s*:\s*(\d+)/);
      if (startLineMatch) fallback.startLine = parseInt(startLineMatch[1], 10);
      const endLineMatch = text.match(/["']endLine["']\s*:\s*(\d+)/);
      if (endLineMatch) fallback.endLine = parseInt(endLineMatch[1], 10);
      return fallback;
    }
  }

  /**
   * Map GPT-5 tool names to categories and normalized names
   */
  mapToolNameToCategory(toolName: string): { category: 'file' | 'code' | 'data' | 'network' | 'custom'; mappedName: string } {
    let category: 'file' | 'code' | 'data' | 'network' | 'custom' = 'custom';
    let mappedName = toolName.toLowerCase().replace(/[^a-z0-9_]/g, '_');

    if (toolName.includes('read_file') || toolName.includes('create_file') || toolName.includes('replace_string')) {
      category = 'file';
      mappedName = 'file_edit';
    } else if (toolName.includes('run_in_terminal') || toolName.includes('execute') || toolName.includes('command')) {
      category = 'code';
      mappedName = 'code_execution';
    } else if (toolName.includes('semantic_search') || toolName.includes('search')) {
      category = 'data';
      mappedName = 'semantic_search';
    }

    return { category, mappedName };
  }

  /**
   * Parse GPT-5 style tool calls from message content
   */
  parseToolCalls(content: string, message: ChatMessageType): { content: string; toolCalls: ToolCallData[] } {
    // Prefer toolCalls provided by backend in metadata
    const metaToolCalls: ToolCallMeta[] | undefined = message.metadata?.toolCalls;
    if (metaToolCalls && metaToolCalls.length > 0) {
      const toolCalls: ToolCallData[] = metaToolCalls.map(tc => ({
        id: tc.id,
        toolName: tc.toolName,
        category: (tc.category as any) || 'custom',
        status: (tc.status as any) || 'running',
        progress: typeof tc.progress === 'number' ? tc.progress : undefined,
        input: tc.input,
        output: tc.output,
        error: tc.error,
        startTime: tc.startedAt ? new Date(tc.startedAt) : undefined,
        endTime: tc.endedAt ? new Date(tc.endedAt) : undefined,
        metadata: tc.metadata
      }));
      return { content, toolCalls };
    }

    // Clean up content first to prevent flashing
    let cleanContent = content;

    // Remove escape sequences and clean up formatting
    cleanContent = cleanContent
      .replace(/\\n\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\"\\n/g, '\n')
      .replace(/logger\.(info|error|debug)\([^)]*\)/g, '')
      .trim();

    // Enhanced pattern matching for GPT-5 tool execution blocks
    const toolExecutionPattern = /🔧\s*\*\*Executing tools\.\.\.\*\*\s*\n([\s\S]*?)🔧\s*\*\*Tool execution complete\. Continuing\.\.\.\*\*/g;
    const toolCalls: ToolCallData[] = [];
    let match;
    let toolCallIndex = 0;

    // First, check for standalone "🔧 **Executing tools...**" without completion
    const standaloneExecutingPattern = /🔧\s*\*\*Executing tools\.\.\.\*\*(?!\s*\n[\s\S]*?🔧\s*\*\*Tool execution complete)/g;
    const standaloneMatches = Array.from(cleanContent.matchAll(standaloneExecutingPattern));

    // Only show progress widget for truly active executions (streaming messages)
    const isActiveStream = message.metadata?.isStreaming && !message.metadata?.streamComplete;

    // We'll add a generic progress widget only if we cannot identify a specific running tool
    let shouldAddGenericProgress = false;
    if (standaloneMatches.length > 0 && isActiveStream) {
      shouldAddGenericProgress = true;
    }

    while ((match = toolExecutionPattern.exec(content)) !== null) {
      const toolBlock = match[1];
      const toolId = `tool-${message.id}-${toolCallIndex++}`;

      // Parse individual completed tool calls (success/error) - GPT-5 specific format
      const individualToolPattern = /📋\s*\*\*([^:]+)\*\*:\s*(\{[^}]*\}|\{[\s\S]*?\}|[^\n]*)\s*\n(✅\s*\*\*Success\*\*:\s*([\s\S]*?)(?=\n\n|📋|\n🔧|$)|❌\s*\*\*Error\*\*:\s*([\s\S]*?)(?=\n\n|📋|\n🔧|$))/g;

      const createdIds: string[] = [];
      let toolMatch;
      while ((toolMatch = individualToolPattern.exec(toolBlock)) !== null) {
        const toolName = toolMatch[1].trim();
        const inputText = toolMatch[2].trim();
        const isSuccess = toolMatch[0].includes('✅ **Success**');
        const resultText = isSuccess ? toolMatch[4] : toolMatch[5];

        // Parse input parameters (support both JSON and python-like dict)
        const input: any = inputText ? this.tryParseArgs(inputText) : {};

        // Parse the result/output for different tool types
        let parsedOutput: any = resultText?.trim();
        let parsedError: any = !isSuccess ? resultText?.trim() : undefined;

        if (isSuccess && parsedOutput) {
          try {
            // Try to parse as JSON first
            const jsonResult = JSON.parse(parsedOutput);
            parsedOutput = jsonResult;
          } catch {
            // For read_file, check if it's a structured response
            if (toolName.includes('read_file') && parsedOutput.includes('content')) {
              try {
                // Extract content from structured response
                const contentMatch = parsedOutput.match(/'content':\s*'([\s\S]*?)',\s*'filePath'/);
                if (contentMatch) {
                  parsedOutput = {
                    content: contentMatch[1].replace(/\\n/g, '\n').replace(/\\'/g, "'"),
                    filePath: input.filePath || 'unknown'
                  };
                }
              } catch {
                // Keep as string if parsing fails
              }
            } else if (toolName.includes('semantic_search') && parsedOutput.startsWith('[')) {
              try {
                // Parse array results
                parsedOutput = JSON.parse(parsedOutput.replace(/'/g, '"'));
              } catch {
                // Keep as string
              }
            }
          }
        }

        // Determine tool category and widget type
        const { category, mappedName } = this.mapToolNameToCategory(toolName);

        const idBase = `${toolId}-${toolName.replace(/[^a-zA-Z0-9]/g, '')}`;
        createdIds.push(idBase);
        const toolCall: ToolCallData = {
          id: idBase,
          toolName: mappedName,
          category,
          status: isSuccess ? 'success' : 'error',
          progress: isSuccess ? 100 : 0,
          input,
          output: parsedOutput,
          error: parsedError,
          startTime: message.timestamp ? new Date(message.timestamp) : new Date(),
          endTime: message.timestamp ? new Date(message.timestamp) : new Date(),
          metadata: {
            originalToolName: toolName,
            executionBlock: toolBlock.trim()
          }
        };

        toolCalls.push(toolCall);
      }

      // Now detect any header-only tools (running) not yet completed in this block
      if (isActiveStream) {
        const headerPattern = /📋\s*\*\*([^:]+)\*\*:\s*([\s\S]*?)(?=\n(?:✅\s*\*\*Success\*\*|❌\s*\*\*Error\*\*|📋|🔧)|$)/g;
        const headerMatches = Array.from(toolBlock.matchAll(headerPattern));
        if (headerMatches.length > 0) {
          // The last header without an associated success/error should be marked running
          const lastHeader = headerMatches[headerMatches.length - 1];
          const headerToolName = lastHeader[1].trim();
          const headerArgsText = lastHeader[2].trim();

          // Check whether this header already had a completed entry created above
          const idBase = `${toolId}-${headerToolName.replace(/[^a-zA-Z0-9]/g, '')}`;
          const alreadyCreated = createdIds.includes(idBase);

          // Determine if this header segment contains success/error
          const hasOutcome = /✅\s*\*\*Success\*\*|❌\s*\*\*Error\*\*/.test(lastHeader[0]);

          if (!alreadyCreated && !hasOutcome) {
            // We have a running tool
            shouldAddGenericProgress = false; // we can attach spinner to this tool instead

            const input: any = headerArgsText ? this.tryParseArgs(headerArgsText) : {};
            const { category, mappedName } = this.mapToolNameToCategory(headerToolName);

            toolCalls.push({
              id: `${idBase}-running`,
              toolName: mappedName,
              category,
              status: 'running',
              progress: undefined,
              input,
              output: undefined,
              error: undefined,
              startTime: message.timestamp ? new Date(message.timestamp) : new Date(),
              metadata: {
                originalToolName: headerToolName,
                executionBlock: toolBlock.trim(),
                running: true
              }
            });
          }
        }
      }
    }

    // Remove tool execution blocks from content but keep the rest
    cleanContent = this.stripAllToolText(content);

    // If we have identified running/completed tools, do not show generic progress
    if (toolCalls.length === 0 && shouldAddGenericProgress) {
      const progressToolCall: ToolCallData = {
        id: `progress-${message.id}`,
        toolName: 'progress',
        category: 'custom',
        status: 'running',
        progress: undefined,
        input: { action: 'Executing tools...' },
        output: undefined,
        startTime: message.timestamp ? new Date(message.timestamp) : new Date(),
        endTime: undefined,
        metadata: {
          isProgress: true
        }
      };
      toolCalls.push(progressToolCall);
    }

    // Also remove standalone "🔧 **Executing tools...**" indicators
    cleanContent = this.stripAllToolText(cleanContent);

    return {
      content: cleanContent,
      toolCalls
    };
  }

  /**
   * Parse GPT-5 specific file edit data
   */
  parseFileEditData(toolCall: ToolCallData): any {
    const input = toolCall.input || {};
    const output = toolCall.output || {};
    
    // Enhanced file path extraction - try multiple possible keys
    let filePath = input.filePath || input.file_path || input.path || 
                   output.filePath || output.file_path || output.path;
    
    // For create_file, the path might be in different locations
    if (!filePath && toolCall.metadata?.originalToolName === 'create_file') {
      filePath = input.filePath || input.file_path || input.path;
    }
    
    // For read_file, check common parameter names
    if (!filePath && toolCall.metadata?.originalToolName === 'read_file') {
      filePath = input.filePath || input.file_path || input.path;
    }
    
    // Fallback to any string that looks like a path
    if (!filePath) {
      const allValues = Object.values({ ...input, ...output });
      filePath = allValues.find((val: any) => 
        typeof val === 'string' && (val.includes('/') || val.includes('\\') || val.endsWith('.py') || val.endsWith('.md') || val.endsWith('.txt'))
      ) as string;
    }
    
    if (!filePath) {
      filePath = 'Unknown file';
    }

    const originalToolName = toolCall.metadata?.originalToolName || toolCall.toolName;
    const operation = originalToolName === 'create_file' ? 'create' : 
                     originalToolName === 'read_file' ? 'read' :
                     originalToolName === 'replace_string_in_file' ? 'update' : 'update';

    return {
      filePath,
      originalContent: input.original_content || output.original_content,
      modifiedContent: input.content || output.content || output.modified_content,
      diff: output.diff,
      timestamp: toolCall.endTime ? new Date(toolCall.endTime).toLocaleString() : undefined,
      operation: operation as any,
      lineNumbers: output.line_numbers,
      startLine: input.startLine || input.start_line,
      endLine: input.endLine || input.end_line
    };
  }

  /**
   * Parse GPT-5 specific code execution data
   */
  parseCodeExecutionData(toolCall: ToolCallData): any {
    const input = toolCall.input || {};
    const output = toolCall.output || {};
    
    let code = '';
    let executionOutput = '';
    let error = '';
    let stackTrace = '';
    
    // Extract code from input
    if (input.command) {
      code = input.command;
    } else if (input.code) {
      code = input.code;
    } else if (input.script) {
      code = input.script;
    }
    
    // Extract output from various formats
    if (output) {
      if (typeof output === 'string') {
        executionOutput = output;
      } else if (output.output) {
        executionOutput = output.output;
      } else if (output.stdout) {
        executionOutput = output.stdout;
      } else if (output.result) {
        executionOutput = output.result;
      }
      
      // Extract error information
      if (output.error) {
        error = output.error;
      } else if (output.stderr) {
        error = output.stderr;
      }
      
      if (output.stackTrace || output.stack_trace) {
        stackTrace = output.stackTrace || output.stack_trace;
      }
    }
    
    return {
      code: code || '',
      output: executionOutput || '',
      error: error || '',
      stackTrace: stackTrace || '',
      language: 'bash', // Default to bash for terminal commands
      exitCode: output?.status || output?.exitCode || (toolCall.status === 'success' ? 0 : 1),
      executionTime: toolCall.endTime && toolCall.startTime 
        ? toolCall.endTime.getTime() - toolCall.startTime.getTime() 
        : undefined,
      environment: input.environment || 'terminal',
      outputFormat: this.detectOutputFormat(executionOutput || error || '')
    };
  }

  /**
   * Parse GPT-5 specific semantic search data
   */
  parseSemanticSearchData(toolCall: ToolCallData): any {
    const input = toolCall.input || {};
    const output = toolCall.output || {};
    
    let results: any[] = [];
    let resultCount = 0;
    
    // Handle different output formats
    if (Array.isArray(output)) {
      // Direct array
      results = output.map((item: any) => ({
        file: item.file || 'Unknown file',
        line: item.line,
        snippet: item.snippet || ''
      }));
    } else if (output.result) {
      try {
        const parsed = JSON.parse(output.result);
        if (Array.isArray(parsed)) {
          results = parsed.map((item: any) => ({
            file: item.file || 'Unknown file',
            line: item.line,
            snippet: item.snippet || ''
          }));
        }
      } catch {
        // If parsing fails, show simple text
      }
    } else if (typeof output === 'string' && output.startsWith('[')) {
      try {
        const parsed = JSON.parse(output.replace(/'/g, '"'));
        if (Array.isArray(parsed)) {
          results = parsed.map((item: any) => ({
            file: item.file || 'Unknown file',
            line: item.line,
            snippet: item.snippet || ''
          }));
        }
      } catch {
        // Keep as empty if parsing fails
      }
    }
    
    resultCount = results.length;
    
    return {
      query: input.query || '',
      scope: input.scope || '',
      fileTypes: input.fileTypes || [],
      results,
      resultCount
    };
  }

  private detectOutputFormat(text: string): 'text' | 'json' | 'html' | 'markdown' {
    if (!text) return 'text';
    
    const trimmed = text.trim();
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        JSON.parse(trimmed);
        return 'json';
      } catch {}
    }
    
    if (trimmed.includes('<html') || trimmed.includes('<!DOCTYPE')) {
      return 'html';
    }
    
    if (trimmed.includes('# ') || trimmed.includes('## ') || trimmed.includes('```')) {
      return 'markdown';
    }
    
    return 'text';
  }
}

// Export the default instance
export const gpt5Helper = new GPT5ModelHelper();
export default gpt5Helper; 