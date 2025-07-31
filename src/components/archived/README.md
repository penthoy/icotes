# Archived Components and Services

This folder contains deprecated components and services that are no longer actively used in the application but are preserved for reference and potential future use.

## Recently Moved (July 31, 2025)

### From Enhanced WebSocket Integration
The following deprecated files were moved here during the enhanced WebSocket integration cleanup:

#### ICUI Components
- `icui/ICUITerminal_deprecated.tsx` - Original terminal component before enhanced WebSocket integration

#### Services
- `services/backendService_deprecated.tsx` - Original backend service before enhanced integration
- `services/chatBackendClient_deprecated.tsx` - Original chat backend client before enhanced WebSocket
- `services/websocket-service_deprecated.ts` - Original WebSocket service before connection management improvements

## Build Configuration

These archived files are excluded from TypeScript compilation via `tsconfig.json`:
```json
"exclude": ["src/components/archived/**/*"]
```

## Usage Notes

- ❌ **Do not import** these files in active code
- ✅ **Reference only** for understanding previous implementations
- ✅ **Safe to delete** if storage space is needed
- ✅ **Preserved** for migration rollback scenarios

## Previous Archived Components

### UI Components (Pre-existing)
- `CodeEditor.tsx` - Legacy code editor component
- `FileExplorer.tsx` - Legacy file explorer
- `FileTabs.tsx` - Legacy file tab management
- `Terminal.tsx` - Legacy terminal implementations
- `ThemeToggle.tsx` - Legacy theme switching
- Various test and panel components

These components were archived during previous development phases and represent earlier iterations of the UI framework.
