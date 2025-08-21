# Model Helper Abstraction

This directory contains model-specific helper functions that handle parsing and processing of tool calls and message content in a way that's tailored to specific AI models.

## Overview

Different AI models format their tool calls and responses differently. Instead of embedding model-specific parsing in UI components, helpers encapsulate it and components call into the active helper.

## Current Implementation

### GPT-5 Helper (`gpt5.tsx`)

The GPT-5 model helper contains:

- **Text Processing**: Strips GPT-5 specific tool execution indicators (`🔧 **Executing tools...**`)
- **Tool Call Parsing**: Parses GPT-5 format tool execution blocks with success/error indicators
- **Argument Parsing**: Handles both JSON and Python-like dictionary formats
- **Tool Name Mapping**: Maps GPT-5 tool names to standardized widget categories
- **Widget Data Parsing**: Provides specialized parsing for file edits, code execution, and semantic search

### Generic Helper (`genericmodel.tsx`)

- A baseline helper that currently reuses GPT-5 defaults; override behavior here for non-GPT-5 models as needed.

### Helper Router (`router.ts`)

- Simple switch to return the active model helper based on a model id.
- Defaults to `gpt5`, falls back to `generic` for unknown ids.

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

### In Components/Widgets

```typescript
import { getActiveModelHelper } from './modelhelper';

const helper = getActiveModelHelper();
const { content, toolCalls } = helper.parseToolCalls(message.content, message);
const fileData = helper.parseFileEditData(toolCall);
const execData = helper.parseCodeExecutionData(toolCall);
```

## Switching Models

Expose a model id from the agent/backend (e.g., `AGENT_MODEL_ID`) and call `setActiveModelId(id)` in the frontend during initialization to pick the correct helper.

## Adding New Models

1. Create a new helper class implementing `ModelHelper` (e.g., `claude.tsx`).
2. Implement model-specific parsing logic for that model's format.
3. Export the helper and update the router to recognize the new model id.

This abstraction keeps UI components clean and makes it easy to support multiple models. 