# GPT-5 Compatibility Update

## Overview

Updated the OpenAI API helper functions to support both GPT-4 and GPT-5 models by automatically selecting the correct token parameter based on the model family.

## Changes Made

### Core Function Added
- `get_openai_token_param(model_name: str, max_tokens: int) -> dict` in `icpy/agent/helpers.py`
  - Automatically detects model family and returns appropriate parameter
  - GPT-5 and o1 models: `max_completion_tokens` 
  - GPT-4 and all other models: `max_tokens`
  - Proper architectural placement: helpers reference core, not vice versa

### Files Updated

1. **`backend/icpy/agent/helpers.py`**
   - Added `get_openai_token_param()` helper function
   - Updated `OpenAIStreamingHandler.stream_chat_with_tools()` method
   - Updated `create_agent_chat_function()` simple streaming section
   - Both now use the new parameter selection logic
   - Function properly exported in `__all__`

2. **`backend/icpy/core/framework_compatibility.py`**
   - Updated `OpenAIFrameworkAgent.execute()` method  
   - Updated `OpenAIFrameworkAgent.stream()` method
   - Both now use model-aware parameter selection
   - Imports helper function with fallback to avoid circular dependencies

## Model Support

| Model Family | Parameter Used |
|--------------|----------------|
| GPT-4, GPT-4o, GPT-4-turbo | `max_tokens` |
| GPT-5, GPT-5-turbo | `max_completion_tokens` |
| o1-mini, o1-preview | `max_completion_tokens` |  
| All other models | `max_tokens` (fallback) |

## Backward Compatibility

- ✅ Existing GPT-4 code continues to work unchanged
- ✅ New GPT-5 models now work without errors
- ✅ o1 models now work correctly
- ✅ Non-OpenAI models remain unaffected

## Testing

A comprehensive test suite (`test_gpt5_compatibility.py`) was created to verify:
- Parameter selection logic for different model families
- Case-insensitive model name handling
- API parameter preparation for actual calls
- Fallback behavior for unknown models

## Usage Example

```python
from icpy.agent.helpers import get_openai_token_param

# GPT-4 usage
params = get_openai_token_param("gpt-4o-mini", 2000)
# Returns: {"max_tokens": 2000}

# GPT-5 usage  
params = get_openai_token_param("gpt-5-turbo", 2000)
# Returns: {"max_completion_tokens": 2000}

# Use in API call
api_params = {
    "model": model_name,
    "messages": messages,
    **get_openai_token_param(model_name, token_limit)
}
response = client.chat.completions.create(**api_params)
```

## Architecture

The function is properly placed in `icpy/agent/helpers.py` following the principle that:
- ✅ **Helper modules** provide utilities to core modules
- ❌ **Core modules** should not depend on helper modules

The framework compatibility layer imports the helper with a fallback implementation to avoid circular dependencies.

## Impact

This change ensures all agent code in the framework can seamlessly use both GPT-4 and GPT-5 models without modification, resolving the "max_tokens parameter not supported" error that occurs when using GPT-5 models.
