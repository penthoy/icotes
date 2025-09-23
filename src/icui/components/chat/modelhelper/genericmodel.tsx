/**
 * Generic Model Helper
 * 
 * Contains parsing logic and helper functions for:
 * - Tool execution text parsing
 * - Tool call extraction from message content
 * - Tool name mapping and categorization
 * - Content cleaning and formatting
 * - Widget data parsing
 * 
 * Note: While this helper is designed to be extensible for different model output formats,
 * its current implementation contains several GPT-5-style formatting patterns
 * (e.g., '🔧 **Executing tools...**', '📋 **toolname**:', '✅ **Success**').
 * Update or extend the parsing logic as needed to support other model formats.
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

export class GenericModelHelper implements ModelHelper {
  
  /**
   * Remove model-specific tool execution text blocks and executing indicators
   */
  stripAllToolText(text: string): string {
    // Combine all major removal patterns into a single regex with alternation
    const combinedPattern = new RegExp([
      // Tool execution blocks (complete blocks)
      '🔧\\s*\\*\\*Executing tools\\.\\.\\.\\*\\*[\\s\\S]*?🔧\\s*\\*\\*Tool execution complete\\. Continuing\\.\\.\\.\\*\\*',
      // Standalone tool execution messages
      '🔧\\s*\\*\\*Executing tools\\.\\.\\.\\*\\*\\s*\\n?',
      '🔧\\s*\\*\\*Tool execution complete\\. Continuing\\.\\.\\.\\*\\*\\s*\\n?',
      // Tool header lines (standalone, incomplete, or still running)
      '📋\\s*\\*\\*[^:]+\\*\\*:\\s*(\\{[^}]*\\}|[^\\n]*)\\n?',
      '📋\\s*\\*\\*[^:]+\\*\\*:\\s*\\{[^}]*\\}\\s*$',
      '📋\\s*\\*\\*[^:]+\\*\\*:\\s*[^\\n]*\\s*$',
      // Large success/error blocks with file content
      '✅\\s*\\*\\*Success\\*\\*:\\s*\\{[^}]*\'content\':[^}]*\\}\\s*\\n',
      '✅\\s*\\*\\*Success\\*\\*:\\s*\\{[\\s\\S]*?\'content\':\\s*\'[\\s\\S]*?\'[\\s\\S]*?\\}\\s*\\n',
      // Logger statements and debug output
      'logger\\.(info|error|debug|warning)\\([^)]*\\)',
      // Large blocks of escaped code 
      '([\'"]content[\'"]:\\s*[\'"][^\'\"]*?(?:logger\\.|import |def |class |try:|except |if __name__|yield )[^\'\"]*?[\'"])',
      // Python code artifacts that leak through
      '\\\\n\\s*except Exception as e:\\\\n\\s*logger\\.error.*?\\\\n',
      '\\\\n\\s*yield f[\'\""][^\'\"]*?\\\\n',
      // Raw Python code blocks
      '\\n\\s*logger\\.(info|error|debug|warning)\\([^)]*\\)\\s*\\n',
      '\\n\\s*(import |from |def |class |try:|except |if __name__|yield )[^\\n]*\\n'
    ].join('|'), 'g');

    return text
      .replace(combinedPattern, '')
      // Clean up multiple consecutive newlines
      .replace(/\n{3,}/g, '\n\n')
      // Handle escape sequences in a single pass
      .replace(/\\n\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\"\\n/g, '\n')
      .replace(/\\\\\n/g, '\n')
      .replace(/\\'/g, "'")
      // Remove error handling blocks that leak through
      .replace(/\n\s*except Exception as e:\s*\n[\s\S]*?(?=\n\n|\n[A-Z]|\n#|$)/g, '\n')
      .trim();
  }

  /**
   * Try to parse arguments (supports both JSON and python-like dicts)
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

      // Also attempt to extract web search style parameters
      const queryMatch = text.match(/["']query["']\s*:\s*["']([^"']+)["']/);
      if (queryMatch) fallback.query = queryMatch[1];
      const maxResultsMatch = text.match(/["']maxResults["']\s*:\s*(\d+)/);
      if (maxResultsMatch) fallback.maxResults = parseInt(maxResultsMatch[1], 10);
      const searchDepthMatch = text.match(/["']searchDepth["']\s*:\s*["']([^"']+)["']/);
      if (searchDepthMatch) fallback.searchDepth = searchDepthMatch[1];
      const includeAnswerMatch = text.match(/["']includeAnswer["']\s*:\s*(true|false)/i);
      if (includeAnswerMatch) fallback.includeAnswer = includeAnswerMatch[1].toLowerCase() === 'true';
      return fallback;
    }
  }

  /**
   * Map tool names to categories and normalized names
   */
  mapToolNameToCategory(toolName: string): { category: 'file' | 'code' | 'data' | 'network' | 'custom'; mappedName: string } {
    const name = toolName.toLowerCase();
    let category: 'file' | 'code' | 'data' | 'network' | 'custom' = 'custom';
    let mappedName = name.replace(/[^a-z0-9_]/g, '_');

    // Special-case Tavily web search to preserve tool identity for a custom widget
    if (name.includes('web_search')) {
      category = 'network';
      mappedName = 'web_search';
      return { category, mappedName };
    }

    if (name.includes('read_file') || name.includes('create_file') || name.includes('replace_string')) {
      category = 'file';
      mappedName = 'file_edit';
    } else if (name.includes('run_in_terminal') || name.includes('execute') || name.includes('command')) {
      category = 'code';
      mappedName = 'code_execution';
    } else if (name.includes('semantic_search') || name.includes('search')) {
      category = 'data';
      mappedName = 'semantic_search';
    } else if (name.includes('fetch') || name.includes('http') || name.includes('request')) {
      category = 'network';
      mappedName = 'network_request';
    }

    return { category, mappedName };
  }

  /**
   * Parse tool calls from message content
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
      return { content: this.stripAllToolText(content), toolCalls };
    }

    // Clean up content first to prevent flashing
    let cleanContent = content;

    // Remove escape sequences and clean up formatting
    cleanContent = cleanContent
      .replace(/\\n\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\"\\n/g, '\n')
      .replace(/logger\.(info|error|debug|warning)\([^)]*\)/g, '')
      // Remove large blocks of escaped code that shouldn't be displayed as regular text
      .replace(/(['"]content['"]:\s*['"][^'"]*?(?:logger\.|import |def |class |try:|except |if __name__|yield )[^'"]*?['"])/g, '')
      // Clean up Python code artifacts that leak through
      .replace(/\\n\s*except Exception as e:\\n\s*logger\.error.*?\\n/g, '')
      .replace(/\\n\s*yield f['""][^'"]*?\\n/g, '')
      // Remove blocks that look like raw Python code (starting with logger, import, def, etc.)
      .replace(/\n\s*logger\.(info|error|debug|warning)\([^)]*\)\s*\n/g, '\n')
      .replace(/\n\s*(import |from |def |class |try:|except |if __name__|yield )[^\n]*\n/g, '\n')
      // Remove error handling blocks that leak through
      .replace(/\n\s*except Exception as e:\s*\n[\s\S]*?(?=\n\n|\n[A-Z]|\n#|$)/g, '\n')
      .trim();

    // Enhanced pattern matching for tool execution blocks
  const toolExecutionPattern = /🔧\s*\*\*Executing tools\.\.\.\*\*\s*\n([\s\S]*?)🔧\s*\*\*Tool execution complete\. Continuing\.\.\.\*\*/g;
  const toolCalls: ToolCallData[] = [];
  let match;
  let toolCallIndex = 0;
  let executionBlockIndex = 0; // Track which Executing tools block we're in
  let globalOrder = 0; // Global order of tools as parsed

    // First, check for standalone "🔧 **Executing tools...**" without completion
    const standaloneExecutingPattern = /🔧\s*\*\*Executing tools\.\.\.\*\*(?!\s*\n[\s\S]*?🔧\s*\*\*Tool execution complete)/g;
    const standaloneMatches = Array.from(cleanContent.matchAll(standaloneExecutingPattern));

    // Also check for individual tool headers that are still running (incomplete)
    const incompleteToolPattern = /📋\s*\*\*([^:]+)\*\*:\s*(\{[^}]*\}|[^\n]*)(?:\n(?!✅|❌))?/g;
    const incompleteToolMatches = Array.from(cleanContent.matchAll(incompleteToolPattern));

    // Only show progress widget for truly active executions (streaming messages)
    const isActiveStream = message.metadata?.isStreaming && !message.metadata?.streamComplete;

    // We'll add a generic progress widget only if we cannot identify a specific running tool
    let shouldAddGenericProgress = false;
    if (standaloneMatches.length > 0 && isActiveStream && incompleteToolMatches.length === 0) {
      shouldAddGenericProgress = true;
    }

  while ((match = toolExecutionPattern.exec(content)) !== null) {
      const toolBlock = match[1];
      const toolId = `tool-${message.id}-${toolCallIndex++}`;

      // Parse individual completed tool calls (success/error) - generic format
      // Updated to handle very large content blocks that might span many lines
      const individualToolPattern = /📋\s*\*\*([^:]+)\*\*:\s*(\{[^}]*\}|\{[\s\S]*?\}|[^\n]*)\s*\n(✅\s*\*\*Success\*\*:\s*([\s\S]*?)(?=\n\n📋|\n🔧|$)|❌\s*\*\*Error\*\*:\s*([\s\S]*?)(?=\n\n📋|\n🔧|$))/g;

      const createdIds: string[] = [];
      const createdNames = new Set<string>(); // track by sanitized tool name
  let toolMatch;
  let innerToolIndex = 0; // Track tool calls within this block
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
                // Extract content from structured response - handle large content blocks
                const contentMatch = parsedOutput.match(/'content':\s*'([\s\S]*?)',\s*'filePath'/);
                if (contentMatch) {
                  let content = contentMatch[1].replace(/\\n/g, '\n').replace(/\\'/g, "'");
                  // Clean up any logger statements or debug output in the content
                  content = content
                    .replace(/logger\.(info|error|debug|warning)\([^)]*\)/g, '')
                    .replace(/print\([^)]*\)/g, '')
                    .trim();
                  
                  // Truncate large content for read_file operations to prevent UI overflow
                  // Show only first 10 lines and a summary for display purposes
                  const lines = content.split('\n');
                  if (lines.length > 10) {
                    const truncatedContent = lines.slice(0, 10).join('\n');
                    content = `${truncatedContent}\n\n... (${lines.length - 10} more lines, ${content.length} total characters)`;
                  }
                  
                  parsedOutput = {
                    content: content,
                    filePath: input.filePath || 'unknown',
                    totalLines: lines.length,
                    totalSize: contentMatch[1].length
                  };
                }
              } catch {
                // Keep as string if parsing fails
              }
            } else if (toolName.includes('semantic_search')) {
              try {
                // Parse array results - handle both direct arrays and success messages with arrays
                let arrayText = parsedOutput;
                
                // If it's a success message, extract the array part
                const arrayMatch = parsedOutput.match(/\[[\s\S]*\]/);
                if (arrayMatch) {
                  arrayText = arrayMatch[0];
                }
                
                // Parse the array, handling Python-style syntax more comprehensively
                const cleanedText = arrayText
                  .replace(/'/g, '"')           // Single to double quotes
                  .replace(/None/g, 'null')     // Python None to JSON null
                  .replace(/True/g, 'true')     // Python True to JSON true  
                  .replace(/False/g, 'false')   // Python False to JSON false
                  .replace(/,(\s*[}\]])/g, '$1'); // Remove trailing commas
                
                parsedOutput = JSON.parse(cleanedText);
              } catch {
                // Keep as string if parsing fails - let the widget parser handle it
              }
            } else if (toolName.includes('web_search')) {
              try {
                // Extract an object block from the success text and parse it
                // Look for a JSON-ish object
                const objMatch = parsedOutput.match(/\{[\s\S]*\}/);
                if (objMatch && objMatch[0]) {
                  const objText = objMatch[0]
                    .replace(/'/g, '"')
                    .replace(/None/g, 'null')
                    .replace(/True/g, 'true')
                    .replace(/False/g, 'false')
                    .replace(/,(\s*[}\]])/g, '$1');
                  const parsed = JSON.parse(objText);
                  parsedOutput = parsed;
                }
              } catch {
                // Fallback: keep as string
              }
            }
          }
        }

        // Determine tool category and widget type
        const { category, mappedName } = this.mapToolNameToCategory(toolName);

        // Create unique ID using both outer and inner indexes to avoid collisions
        const sanitizedName = toolName.replace(/[^a-zA-Z0-9]/g, '');
        const idBase = `${toolId}-${innerToolIndex}-${sanitizedName}`;
        createdIds.push(idBase);
        createdNames.add(sanitizedName);
    const indexInBlock = innerToolIndex; // capture before increment for metadata
    innerToolIndex++; // Increment inner tool index for uniqueness
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
      executionBlock: toolBlock.trim(),
      blockIndex: executionBlockIndex,
      indexInBlock,
      order: globalOrder++,
      argsText: inputText
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
          const headerToolKey = headerToolName.replace(/[^a-zA-Z0-9]/g, '');
          const alreadyCreated = createdNames.has(headerToolKey);

          // Determine if this header segment contains success/error
          const hasOutcome = /✅\s*\*\*Success\*\*|❌\s*\*\*Error\*\*/.test(lastHeader[0]);

      if (!alreadyCreated && !hasOutcome) {
            // We have a running tool
            shouldAddGenericProgress = false; // we can attach spinner to this tool instead

            const input: any = headerArgsText ? this.tryParseArgs(headerArgsText) : {};
            const { category, mappedName } = this.mapToolNameToCategory(headerToolName);

            toolCalls.push({
              id: `${toolId}-${headerToolKey}-running`,
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
        running: true,
        blockIndex: executionBlockIndex,
        indexInBlock: innerToolIndex, // next index position
        order: globalOrder++
              }
            });
          }
        }
      }

  // Increment block index after finishing this execution block
  executionBlockIndex++;
    }

    // Remove tool execution blocks from content but keep the rest
    cleanContent = this.stripAllToolText(content);

    // Additional cleanup for leaked code blocks that appear outside tool execution blocks
    cleanContent = this.cleanupLeakedCode(cleanContent);

    // Handle incomplete tool patterns that appear outside main execution blocks
    // This helps show running tools even when they haven't been wrapped in execution blocks yet
    if (isActiveStream && toolCalls.length === 0 && incompleteToolMatches.length > 0) {
      incompleteToolMatches.forEach((match, index) => {
        const toolName = match[1].trim();
        const argsText = match[2].trim();

        // Skip only if this header itself shows completion markers
        const hasCompletion = /✅\s*\*\*Success\*\*|❌\s*\*\*Error\*\*/.test(match[0]);
        if (!hasCompletion) {
          const input: any = argsText ? this.tryParseArgs(argsText) : {};
          const { category, mappedName } = this.mapToolNameToCategory(toolName);

          toolCalls.push({
            id: `incomplete-${message.id}-${index}`,
            toolName: mappedName,
            category,
            status: 'running',
            progress: undefined,
            input,
            output: undefined,
            error: undefined,
            startTime: message.timestamp ? new Date(message.timestamp) : new Date(),
            metadata: {
              originalToolName: toolName,
              incomplete: true,
              running: true
            }
          });

          shouldAddGenericProgress = false; // We have specific tool widgets
        }
      });
    }

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

    // Final cleanup pass
    cleanContent = this.stripAllToolText(cleanContent);

    return {
      content: cleanContent,
      toolCalls
    };
  }

  /**
   * Parse file edit data
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

    // Extract content based on tool type
    let originalContent = input.original_content || output.original_content || output.originalContent;
    let modifiedContent = input.content || output.content || output.modified_content || output.modifiedContent;
    
    if (originalToolName === 'read_file' && output && typeof output === 'object') {
      // Handle structured output from read_file
      if (output.content) {
        modifiedContent = output.content;
      }
      // For read operations, show additional metadata if available
      if (output.totalLines || output.totalSize) {
        // Content is already truncated in parsing, so we use it as-is
      }
    }
    
    // For replace_string_in_file operations, extract original and modified content
    if (originalToolName === 'replace_string_in_file' && output && typeof output === 'object') {
      originalContent = output.originalContent || originalContent;
      modifiedContent = output.modifiedContent || modifiedContent;
    }

    return {
      filePath,
      originalContent,
      modifiedContent,
      diff: output.diff,
      timestamp: toolCall.endTime ? new Date(toolCall.endTime).toLocaleString() : undefined,
      operation: operation as any,
      lineNumbers: output.line_numbers,
      startLine: input.startLine || input.start_line,
      endLine: input.endLine || input.end_line,
      totalLines: output?.totalLines,
      totalSize: output?.totalSize
    };
  }

  /**
   * Parse code execution data
   */
  parseCodeExecutionData(toolCall: ToolCallData): any {
    const input = toolCall.input || {};
    const output = toolCall.output || {};
    const originalToolName = toolCall.metadata?.originalToolName || toolCall.toolName;
    
    let code = '';
    let executionOutput = '';
    let error = '';
    let stackTrace = '';
    
    // Extract code/command from input - enhanced for run_in_terminal
    if (originalToolName === 'run_in_terminal') {
      // For terminal commands, prioritize command parameter
      code = input.command || input.cmd || input.script || input.code || '';
      
      // If still no code, try to extract from tool call metadata or raw input
      if (!code && typeof input === 'string') {
        code = input;
      }
      
      // If still no code, check if it's in a nested structure
      if (!code && input.raw) {
        code = input.raw;
      }
    } else {
      // For other code execution tools
      if (input.command) {
        code = input.command;
      } else if (input.code) {
        code = input.code;
      } else if (input.script) {
        code = input.script;
      } else if (input.cmd) {
        code = input.cmd;
      }
      
      // Fallback: if input is a simple string, treat it as code
      if (!code && typeof input === 'string') {
        code = input;
      }
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
      language: originalToolName === 'run_in_terminal' ? 'bash' : this.detectCodeLanguage(code) || 'bash',
      exitCode:
        typeof output?.exitCode === 'number' ? output.exitCode
        : typeof output?.status === 'number' ? output.status
        : (typeof output?.status === 'string' && /^\d+$/.test(output.status)
            ? parseInt(output.status, 10)
            : (toolCall.status === 'success' ? 0 : 1)),
      executionTime: toolCall.endTime && toolCall.startTime 
        ? toolCall.endTime.getTime() - toolCall.startTime.getTime() 
        : undefined,
      environment: input.environment || 'terminal',
      outputFormat: this.detectOutputFormat(executionOutput || error || '')
    };
  }

  /**
   * Parse semantic search data
   */
  parseSemanticSearchData(toolCall: ToolCallData): any {
    const input = toolCall.input || {};
    const output = toolCall.output || {};
    
    let results: any[] = [];
    let resultCount = 0;
    
    // Handle different output formats - enhanced for better parsing
    if (Array.isArray(output)) {
      // Direct array
      results = output
        .filter((item: any) => item && (item.file || item.path)) // Only include items with valid file paths
        .map((item: any) => ({
          file: item.file || item.path || 'Unknown file',
          line: item.line || item.lineNumber || undefined,
          snippet: item.snippet || item.text || item.content || 'No snippet available'
        }));
    } else if (output && typeof output === 'object') {
      // Check various nested structures
      if (output.data && Array.isArray(output.data)) {
        // Output has .data property with array (from ToolResult structure)
        results = output.data
          .filter((item: any) => item && (item.file || item.path)) // Only include items with valid file paths
          .map((item: any) => ({
            file: item.file || item.path || 'Unknown file', 
            line: item.line || item.lineNumber || undefined,
            snippet: item.snippet || item.text || item.content || 'No snippet available'
          }));
      } else if (output.results && Array.isArray(output.results)) {
        // Output has .results property
        results = output.results
          .filter((item: any) => item && (item.file || item.path)) // Only include items with valid file paths
          .map((item: any) => ({
            file: item.file || item.path || 'Unknown file',
            line: item.line || item.lineNumber || undefined,
            snippet: item.snippet || item.text || item.content || 'No snippet available'
          }));
      } else if (output.result) {
        try {
          // Try parsing result as JSON
          let parsed;
          if (typeof output.result === 'string') {
            parsed = JSON.parse(output.result);
          } else {
            parsed = output.result;
          }
          
          if (Array.isArray(parsed)) {
            results = parsed
              .filter((item: any) => item && (item.file || item.path)) // Only include items with valid file paths
              .map((item: any) => ({
                file: item.file || item.path || 'Unknown file',
                line: item.line || item.lineNumber || undefined,
                snippet: item.snippet || item.text || item.content || 'No snippet available'
              }));
          } else if (parsed.data && Array.isArray(parsed.data)) {
            // Nested data structure
            results = parsed.data
              .filter((item: any) => item && (item.file || item.path)) // Only include items with valid file paths
              .map((item: any) => ({
                file: item.file || item.path || 'Unknown file',
                line: item.line || item.lineNumber || undefined,
                snippet: item.snippet || item.text || item.content || 'No snippet available'
              }));
          }
        } catch {
          // If parsing fails, continue to string parsing
        }
      }
    } 
    
  // Handle string output - enhanced with better regex patterns
    if (results.length === 0 && typeof output === 'string') {
      try {
        // Handle string output - could be JSON array or success message with array
        let arrayText = output;
        
        // If it's a success message, extract the array part with better regex
        if (!output.startsWith('[')) {
          // Try multiple patterns to extract array data
          const patterns = [
            /\[[\s\S]*?\]/g,           // Basic array pattern
            /results?:\s*\[[\s\S]*?\]/gi, // "results: [...]" pattern
            /data:\s*\[[\s\S]*?\]/gi,     // "data: [...]" pattern
            /found:\s*\[[\s\S]*?\]/gi,    // "found: [...]" pattern
            /Success.*?\[[\s\S]*?\]/gi    // "**Success**: [...]" pattern
          ];
          
          for (const pattern of patterns) {
            const match = output.match(pattern);
            if (match && match[0]) {
              // Extract just the array part
              const extractMatch = match[0].match(/\[[\s\S]*\]/);
              if (extractMatch) {
                arrayText = extractMatch[0];
                break;
              }
            }
          }
        }
        
        // Parse the array, handling Python-style syntax and various formats
        const cleanedArrayText = arrayText
          .replace(/'/g, '"')           // Single to double quotes
          .replace(/None/g, 'null')     // Python None to JSON null
          .replace(/True/g, 'true')     // Python True to JSON true
          .replace(/False/g, 'false')   // Python False to JSON false
          .replace(/,\s*}/g, '}')       // Remove trailing commas
          .replace(/,\s*]/g, ']');      // Remove trailing commas
          
        const parsed = JSON.parse(cleanedArrayText);
        if (Array.isArray(parsed)) {
          results = parsed
            .filter((item: any) => item && (item.file || item.path || item.filename)) // Only include items with valid file paths
            .map((item: any) => ({
              file: item.file || item.path || item.filename || 'Unknown file',
              line: item.line || item.lineNumber || item.line_number || undefined,
              snippet: item.snippet || item.text || item.content || item.match || 'No snippet available'
            }));
        }
      } catch (parseError) {
        // If JSON parsing fails, try to extract results using simpler patterns
        try {
          const extractedResults: any[] = [];

          // 1) Look for file:line: snippet patterns
          const fileLinePattern = /([^:\n]+):(\d+):\s*(.+)/g;
          let match;
          while ((match = fileLinePattern.exec(output)) !== null) {
            extractedResults.push({
              file: match[1].trim(),
              line: parseInt(match[2], 10),
              snippet: match[3].trim()
            });
          }

          // 2) Extract Python-like object chunks even if the array is truncated
          //    Matches minimal object blocks and then we JSON-ify them
          const objectPattern = /\{[^{}]*\}/g;
          const rawObjects = output.match(objectPattern) || [];
          for (const raw of rawObjects) {
            try {
              const jsonish = raw
                .replace(/'/g, '"')
                .replace(/None/g, 'null')
                .replace(/True/g, 'true')
                .replace(/False/g, 'false')
                .replace(/,\s*}/g, '}');
              const obj = JSON.parse(jsonish);
              if (obj && (obj.file || obj.path || obj.filename)) {
                extractedResults.push({
                  file: obj.file || obj.path || obj.filename,
                  line: obj.line || obj.lineNumber || obj.line_number || undefined,
                  snippet: obj.snippet || obj.text || obj.content || obj.match || 'No snippet available'
                });
              }
            } catch {}
          }

          if (extractedResults.length > 0) {
            results = extractedResults;
          }
        } catch {
          // Final fallback - keep results empty
        }
      }
    }
    
    // Special case: Sometimes output might have success=true and data separately
    if (results.length === 0 && output && typeof output === 'object') {
      if (output.success === true && output.data && Array.isArray(output.data)) {
        results = output.data
          .filter((item: any) => item && (item.file || item.path))
          .map((item: any) => ({
            file: item.file || item.path || 'Unknown file',
            line: item.line || item.lineNumber || undefined,
            snippet: item.snippet || item.text || item.content || 'No snippet available'
          }));
      }
    }
    
    // Normalize results where some tools encode "file-line-snippet" inside the file field itself
    if (results.length > 0) {
      results = results.map((r: any) => {
        let file = r.file;
        let line = r.line;
        let snippet = r.snippet;

        // If file looks like: "/path/to/file.ext-14-# some snippet..."
        const hyphenEnc = typeof file === 'string' ? file.match(/^(.*?)-(\d+)-(.*)$/) : null;
        if (!line && hyphenEnc) {
          const [, f, ln, sn] = hyphenEnc;
          file = f;
          line = parseInt(ln, 10);
          if (!snippet || snippet === 'No snippet available') {
            snippet = (sn || '').trim();
          }
        }

        return {
          file: file || 'Unknown file',
          line: line || undefined,
          snippet: snippet || 'No snippet available'
        };
      });
    }

    resultCount = results.length;
    
    // Extract query from various possible locations
    let query = input.query || '';
    if (!query && toolCall.metadata?.query) {
      query = toolCall.metadata.query;
    }
    if (!query && input.search_query) {
      query = input.search_query;
    }
    if (!query && input.term) {
      query = input.term;
    }
    
    return {
      query: query || '(not provided)',
      scope: input.scope || input.root || '',
      fileTypes: input.fileTypes || input.file_types || [],
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

  private detectCodeLanguage(code: string): string {
    if (!code) return 'bash';
    
    const trimmed = code.trim();
    
    // Python patterns
    if (trimmed.includes('import ') || trimmed.includes('def ') || trimmed.includes('print(') || trimmed.startsWith('python ')) {
      return 'python';
    }
    
    // JavaScript/Node patterns  
    if (trimmed.includes('npm ') || trimmed.includes('node ') || trimmed.includes('const ') || trimmed.includes('function(')) {
      return 'javascript';
    }
    
    // Git commands
    if (trimmed.startsWith('git ')) {
      return 'bash';
    }
    
    // Docker commands
    if (trimmed.startsWith('docker ')) {
      return 'bash';
    }
    
    // Default to bash for shell commands
    return 'bash';
  }

  /**
   * Clean up leaked code blocks that appear outside tool execution blocks
   */
  private cleanupLeakedCode(text: string): string {
    return text
      // Remove large success blocks that contain structured data (like file content)
      .replace(/✅\s*\*\*Success\*\*:\s*\{[\s\S]*?\}\s*\n/g, '')
      // Remove large blocks of code that contain Python-specific patterns
      .replace(/\n[^\n]*(?:logger\.|import |def |class |try:|except |if __name__|yield |from )[^\n]*(?:\n[^\n]*(?:logger\.|import |def |class |try:|except |if __name__|yield |from |    |        )[^\n]*){5,}/g, '\n')
      // Remove blocks that look like stack traces or error output
      .replace(/\n[^\n]*(?:Traceback|File "[^"]*", line \d+|    at |Error:|Exception:)[^\n]*(?:\n[^\n]*(?:    |        |File |    at )[^\n]*){2,}/g, '\n')
      // Remove logger output patterns
      .replace(/\n[^\n]*logger\.[a-z]+\([^)]*\)[^\n]*(?:\n[^\n]*(?:    |        )[^\n]*){0,3}/g, '\n')
      // Remove lines that look like escaped Python strings with code
      .replace(/\n[^\n]*\\n[^\n]*(?:def |class |import |from |logger\.|try:|except )[^\n]*\n/g, '\n')
      // Remove very long lines (>300 chars) that likely contain raw data
      .replace(/\n[^\n]{300,}\n/g, '\n')
      // Remove blocks that contain multiple consecutive technical lines (imports, functions etc)
      .replace(/\n(?:[^\n]*(?:import|from|def|class|logger\.|yield|except)[^\n]*\n){3,}/g, '\n')
      // Clean up multiple newlines
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }
}

// Export the default instance
const genericModelHelper = new GenericModelHelper();
export default genericModelHelper; 