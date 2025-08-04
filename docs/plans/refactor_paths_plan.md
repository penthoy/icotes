# Path Refactoring and Rebranding Plan

## Overview
This plan addresses hardcoded paths and inconsistent workspace configuration across the codebase, as well as completing the rebrand from "icotes" to "icotes".

## Issues Identified

### 1. Hardcoded Workspace Paths
**Problem**: Multiple files contain hardcoded fallback paths to `/home/penthoy/icotes/workspace`

**Affected Files**:
- `src/icui/lib/workspaceUtils.ts` - Line 12
- `src/icui/components/panels/ICUIExplorerPanel.tsx` - Line 107  
- `src/icui/services/fileService.tsx` - Line 43
- `tests/integration/components/BackendConnectedExplorer.tsx` - Lines 177, 190
- `tests/integration/components/BackendConnectedEditor.tsx` - Line 356
- `tests/integration/simpleeditor.tsx` - Lines 97, 196
- `tests/integration/icui/ICUIServicesTest.tsx` - Line 59

### 2. Inconsistent Environment Variable Usage
**Problem**: Mix of patterns for accessing workspace root:
- `config.workspacePath || '/home/penthoy/icotes/workspace'`
- `(import.meta as any).env?.VITE_WORKSPACE_ROOT || '/home/penthoy/icotes/workspace'`

### 3. Incomplete Rebranding
**Problem**: References to "icotes" still exist in:
- Environment variables in `.env` files
- Documentation in roadmap.md (historical references in completed tasks)
- Backend agent files
- Test files

### 4. Environment Configuration Issues
**Current State**:
- `.env`: `WORKSPACE_ROOT=/home/penthoy/icotes/workspace`
- `.env.production`: `WORKSPACE_ROOT=/workspace`
- Backend correctly uses `WORKSPACE_ROOT` environment variable
- Frontend inconsistently uses `VITE_WORKSPACE_ROOT`

## Refactoring Strategy

### Phase 1: Environment Configuration Standardization
1. **Update Environment Files**:
   - `.env`: Change `WORKSPACE_ROOT` and `VITE_WORKSPACE_ROOT` to `/home/penthoy/icotes/workspace`
   - Ensure consistency between `WORKSPACE_ROOT` (backend) and `VITE_WORKSPACE_ROOT` (frontend)

2. **Create Workspace Directory**:
   - Create `/home/penthoy/icotes/workspace` if it doesn't exist
   - Migrate content from old workspace if needed

### Phase 2: Remove Hardcoded Fallbacks
1. **Centralize Workspace Configuration**:
   - Update `src/icui/lib/workspaceUtils.ts` to remove hardcoded fallback
   - Enforce that `VITE_WORKSPACE_ROOT` must be set (throw error if missing)

2. **Update All Frontend Files**:
   - Replace hardcoded paths with calls to `getWorkspaceRoot()` from workspaceUtils
   - Remove all `/home/penthoy/icotes/workspace` references

3. **Update Test Files**:
   - Replace hardcoded paths with environment variable usage
   - Ensure tests work with any workspace path

### Phase 3: Complete Rebranding
1. **Backend Agent Files**:
   - `backend/icpy/agent/mailsent_agent.py`: Update dotenv path
   - `backend/icpy/agent/personal_agent.py`: Update hardcoded PDF path

2. **Documentation Files**:
   - Update roadmap.md to use correct paths in historical references
   - Keep historical context but fix path references

### Phase 4: Validation and Testing
1. **Runtime Validation**:
   - Add startup checks to ensure workspace directory exists
   - Provide clear error messages if environment variables are missing

2. **Test Validation**:
   - Ensure all tests pass with new configuration
   - Verify frontend and backend can start successfully

## Implementation Details

### Critical Files to Modify

**Frontend Core**:
- `src/icui/lib/workspaceUtils.ts` - Remove hardcoded fallback, add validation
- `src/icui/components/panels/ICUIExplorerPanel.tsx` - Use workspaceUtils
- `src/icui/services/fileService.tsx` - Use workspaceUtils

**Test Files**:
- All test files in `tests/integration/` - Replace hardcoded paths

**Backend**:
- `backend/icpy/agent/mailsent_agent.py` - Fix dotenv path
- `backend/icpy/agent/personal_agent.py` - Fix PDF path

**Configuration**:
- `.env` - Update workspace paths
- Ensure workspace directory exists

### New Workspace Path Structure
```
/home/penthoy/icotes/workspace/
├── (user workspace files)
└── README.md (optional: workspace usage guide)
```

### Error Handling Strategy
- Frontend: Throw clear error if `VITE_WORKSPACE_ROOT` is undefined
- Backend: Already handles missing `WORKSPACE_ROOT` with relative fallback (good)
- Startup validation: Check if workspace directory exists and is accessible

## Risk Mitigation
1. **Backup**: Document current workspace location before migration
2. **Gradual Migration**: Test each phase independently
3. **Fallback Plan**: Keep old workspace available during testing
4. **Validation**: Add runtime checks to prevent silent failures

## Success Criteria
- ✅ No hardcoded paths in any source files
- ✅ Consistent environment variable usage across frontend/backend
- ✅ All references to "icotes" replaced with "icotes" 
- ✅ Workspace directory exists and is functional
- ✅ All tests pass with new configuration
- ✅ Clear error messages for configuration issues
