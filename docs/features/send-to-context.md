# Send To Context Feature

## Overview
The "Send to >" context menu feature allows users to send (copy) files and folders from one context to another, supporting local ↔ remote transfers across hop sessions.

## User Experience

### Accessing the Feature
1. Right-click on one or more files/folders in the Explorer
2. Select "Send to >" from the context menu
3. Choose the target context (e.g., "Local workspace", "hop1", "hop2")

### Requirements
- Feature appears only when 2+ contexts are available (local + at least one hop session)
- Selected files/folders are copied to the target context's default workspace path
- Directory structure is preserved using common prefix logic

## Implementation Details

### Frontend Components

#### ExplorerContextMenu
- **File**: `src/icui/components/explorer/ExplorerContextMenu.tsx`
- **Responsibility**: Dynamically builds "Send to >" submenu based on available hop sessions
- **Logic**:
  - Fetches cached hop sessions from backend service
  - Filters out duplicate contexts
  - Shows credential names (e.g., "hop1") or falls back to username@host
  - Creates submenu items with `explorer.sendTo` command and `targetContextId` args

#### FileOperations
- **File**: `src/icui/components/explorer/FileOperations.tsx`
- **Command**: `explorer.sendTo`
- **Responsibility**: Handles file transfer initiation
- **Features**:
  - Computes common prefix to preserve relative directory structure
  - Calls backend service `sendFilesToContext` method
  - Shows confirmation dialogs for success/errors
  - Logs transfer operations

#### ContextMenu Component
- **File**: `src/icui/components/ui/ContextMenu.tsx`
- **Key Fixes**:
  - Submenu click detection: Fixed outside-click handler to recognize portal-rendered submenus
  - Submenu stability: Removed premature `onCloseSubMenu` calls on hover
  - Click propagation: Proper event handling for nested menu items

### Backend API

#### Endpoint: POST /api/hop/send-files
- **File**: `backend/icpy/api/endpoints/hop.py`
- **Request Model**: `SendFilesRequest`
  - `target_context_id`: Destination context
  - `paths`: List of source file/folder paths
  - `source_context_id`: Optional source (defaults to active context)
  - `common_prefix`: Optional prefix for relative path preservation

- **Features**:
  - Supports local → remote, remote → local, remote → remote
  - Uses SFTP for remote operations (when AsyncSSH available)
  - Recursive directory copying
  - Creates intermediate directories as needed
  - Binary-safe file transfer
  - Returns created paths and per-path errors

#### Backend Service
- **File**: `src/icui/services/backend-service-impl.tsx`
- **Method**: `sendFilesToContext(targetContextId, paths, opts)`
- **Caching**: Hop sessions cached in `hopSessionsCache` for menu performance

## Technical Decisions

### Path Resolution
- **Local context**: Uses `WORKSPACE_ROOT` or `VITE_WORKSPACE_ROOT` environment variable
- **Remote context**: Uses credential's `defaultPath` or session's `cwd`
- **Relative structure**: Computed common prefix preserves directory hierarchy

### Error Handling
- Non-aborting: Single file failures don't stop batch transfers
- User feedback: Confirmation dialogs show success/error counts
- Logging: Comprehensive backend logs for debugging production issues

### Security
- Path normalization prevents `..` traversal attacks
- SFTP availability guard prevents runtime errors when SSH not configured
- Context validation ensures source ≠ target

## Known Limitations

1. **SFTP Dependency**: Remote transfers require AsyncSSH to be installed
2. **No Progress UI**: Large transfers show no progress indicator (only completion dialog)
3. **No Conflict Resolution**: Existing files are overwritten without prompt
4. **No Auto-Refresh**: Target context Explorer doesn't automatically refresh (user must hop to see files)

## Future Enhancements

1. **Progress Indicators**: Non-blocking toast notifications for ongoing transfers
2. **Auto-Refresh**: Broadcast filesystem events to target context for automatic refresh
3. **Conflict Handling**: Prompt user when destination files exist
4. **Transfer Queue**: Background transfer queue for large operations
5. **Bandwidth Throttling**: Optional rate limiting for large remote transfers

## Files Modified/Created

### Frontend
- `src/icui/components/explorer/ExplorerContextMenu.tsx` - Added Send to submenu logic
- `src/icui/components/explorer/FileOperations.tsx` - Added `explorer.sendTo` command handler
- `src/icui/components/explorer/useExplorerContextMenu.ts` - Enhanced args propagation
- `src/icui/components/panels/ICUIExplorer.tsx` - Added hop sessions initial fetch
- `src/icui/components/ui/ContextMenu.tsx` - Fixed submenu click detection
- `src/icui/services/backend-service-impl.tsx` - Added `sendFilesToContext` method and sessions caching

### Backend
- `backend/icpy/api/endpoints/hop.py` - Added `/send-files` endpoint
- `backend/icpy/services/hop_service.py` - Enhanced `list_sessions` with credentialName

## Testing

### Manual Test Cases
1. **Basic Transfer**: Single file local → remote
2. **Batch Transfer**: Multiple files local → remote
3. **Directory Transfer**: Folder with nested structure
4. **Remote to Local**: File from remote → local workspace
5. **Remote to Remote**: File between two hop contexts
6. **Error Handling**: Transfer when target unreachable
7. **Same Context**: Verify noop when source = target

### Edge Cases Covered
- Empty selection (gracefully ignored)
- Source = target (early exit with message)
- SFTP unavailable (returns error message)
- Invalid paths (logged and included in errors array)
- Special characters in filenames (preserved)
