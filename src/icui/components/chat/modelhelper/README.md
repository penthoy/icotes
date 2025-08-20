# Model Helper Abstraction

This directory contains model-specific helper functions and widgets that handle parsing and processing of tool calls and message content in a way that's tailored to specific AI models.

## Overview

Different AI models format their tool calls and responses differently. Rather than having generic parsing logic that tries to handle all models, we create model-specific helpers that understand the exact format and behavior of each model.

## Current Implementation

### GPT-5 Helper (`gpt5.tsx`)

The GPT-5 model helper contains:

- **Text Processing**: Strips GPT-5 specific tool execution indicators (`🔧 **Executing tools...**`)
- **Tool Call Parsing**: Parses GPT-5 format tool execution blocks with success/error indicators
- **Argument Parsing**: Handles both JSON and Python-like dictionary formats
- **Tool Name Mapping**: Maps GPT-5 tool names to standardized widget categories
- **Widget Data Parsing**: Provides specialized parsing for file edits, code execution, and semantic search

### Model-Specific Widgets (`widgets/`)

Each model helper can have its own widget variants that use the model's specific parsing logic:

- `GPT5FileEditWidget`: Uses GPT-5 helper for parsing file edit data
- `GPT5CodeExecutionWidget`: Uses GPT-5 helper for parsing code execution data  
- `GPT5SemanticSearchWidget`: Uses GPT-5 helper for parsing search results

## Interface

All model helpers implement the `ModelHelper` interface:

```typescript
interface ModelHelper {
  stripAllToolText(text: string): string;
  parseToolCalls(content: string, message: ChatMessageType): { content: string; toolCalls: ToolCallData[] };
  tryParseArgs(text: string): any;
  mapToolNameToCategory(toolName: string): { category: string; mappedName: string };
  parseFileEditData(toolCall: ToolCallData): any;
  parseCodeExecutionData(toolCall: ToolCallData): any;
  parseSemanticSearchData(toolCall: ToolCallData): any;
}
```

## Usage

### In Components

```typescript
import { gpt5Helper } from './modelhelper';

// Use the helper for parsing
const { content, toolCalls } = gpt5Helper.parseToolCalls(message.content, message);
const fileData = gpt5Helper.parseFileEditData(toolCall);
```

### In Widgets

```typescript
import { gpt5Helper } from '../modelhelper';

const executionData = useMemo(() => {
  return gpt5Helper.parseCodeExecutionData(toolCall);
}, [toolCall]);
```

## Future Plans

1. **Model Selection**: Add a service to select the appropriate model helper based on the current model being used
2. **Additional Models**: Create helpers for Claude, Gemini, and other models
3. **Dynamic Registration**: Allow model helpers to be registered dynamically
4. **Fallback Logic**: Implement fallback parsing when model-specific logic fails

## Adding New Models

To add support for a new model:

1. Create a new helper class implementing `ModelHelper` (e.g., `claude.tsx`)
2. Implement model-specific parsing logic for that model's format
3. Create model-specific widget variants if needed
4. Export the helper from the index file
5. Update the model selection service to use the new helper

This abstraction makes it easy to support multiple models while keeping the parsing logic clean and maintainable. 