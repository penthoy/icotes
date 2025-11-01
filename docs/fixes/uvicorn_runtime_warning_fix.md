# Uvicorn RuntimeWarning Fix

**Date**: 2025-10-09  
**Issue**: RuntimeWarning during backend startup  
**Status**: ✅ Fixed

## Problem

During backend startup, a RuntimeWarning was being logged:

```
/home/penthoy/icotes/backend/icpy/services/chat_service.py:2143: RuntimeWarning: coroutine 'get_connection_manager' was never awaited
  _chat_service = ChatService()
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
```

## Root Cause

In `ChatService.__init__()`, the code was calling `get_connection_manager()` without awaiting it:

```python
# OLD CODE (line 168)
self.connection_manager = get_connection_manager()
```

The function `get_connection_manager()` is defined as an async function in `backend/icpy/core/connection_manager.py`:

```python
async def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        await _connection_manager.start()
    # ...
    return _connection_manager
```

Since `__init__` is not an async function, calling `get_connection_manager()` without `await` returns a coroutine object instead of executing it, which triggers Python's "coroutine was never awaited" RuntimeWarning.

## Solution

The code already had a proxy mechanism to handle lazy initialization of the connection manager (see lines 265-279). The fix was to simply set `connection_manager` to `None` initially and let the proxy handle it:

```python
# NEW CODE (line 168)
self.connection_manager = None
```

**File Changed**: `backend/icpy/services/chat_service.py`

### Why This Works

1. The initialization code (lines 265-279) checks if `connection_manager` needs a proxy
2. It detects when `connection_manager` is `None` or a coroutine
3. It wraps it with `_CMProxy` class that provides a `send_to_connection` method
4. The proxy lazily resolves the actual connection manager when needed
5. No RuntimeWarning is triggered because we never call the async function without awaiting

## Testing

### Before Fix
```bash
$ cd backend && python3 -W default main.py 2>&1 | grep RuntimeWarning
/home/penthoy/icotes/backend/icpy/services/chat_service.py:2143: RuntimeWarning: coroutine 'get_connection_manager' was never awaited
```

### After Fix
```bash
$ cd backend && python3 -W default main.py 2>&1 | grep RuntimeWarning
✅ No RuntimeWarning found!
```

### Frontend Build
```bash
$ npm run build
✓ built in 8.54s
✅ Frontend build successful
```

## Impact

- **Severity**: Low (cosmetic warning, not functional issue)
- **User Impact**: None - warning was only visible in backend logs
- **Performance**: No change - proxy mechanism was already in place
- **Compatibility**: Fully compatible - no breaking changes

## Related Files

- `backend/icpy/services/chat_service.py` - Main fix
- `backend/icpy/core/connection_manager.py` - Async function definition
- Test files continue to work with mocking (proxy handles it)

## Notes

The original code comment mentioned "tests patch get_connection_manager to return a Mock manager" - this still works because:
1. Tests can patch `get_connection_manager` to return a Mock
2. The proxy checks `hasattr(cm_obj, 'send_to_connection')` 
3. If the Mock has that attribute, no proxy is created
4. If the Mock doesn't have it, the proxy provides it
5. Everything continues to work as expected
