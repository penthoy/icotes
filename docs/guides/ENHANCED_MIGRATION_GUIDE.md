# Enhanced Component Migration Guide

This guide helps developers migrate from Enhanced component names to the new clean component names.

## Overview

As part of the Enhanced cleanup initiative, several components have been renamed to use cleaner, more intuitive names. The Enhanced versions remain available for backward compatibility but are marked as deprecated.

## Component Migrations

### Layout Components

#### ICUIEnhancedLayout → ICUILayout
**Old (Deprecated):**
```typescript
import { ICUIEnhancedLayout, ICUIEnhancedLayoutProps } from 'icui';

// Component usage
<ICUIEnhancedLayout 
  panels={panels}
  layout={layout}
  onLayoutChange={handleLayoutChange}
/>
```

**New (Recommended):**
```typescript
import { ICUILayout, ICUILayoutProps } from 'icui';

// Component usage
<ICUILayout 
  panels={panels}
  layout={layout}
  onLayoutChange={handleLayoutChange}
/>
```

### Panel Components

The Enhanced panel components serve specific purposes and remain as-is:
- **ICUIEnhancedEditorPanel** - Advanced editor panel with enhanced features
- **ICUIEnhancedTerminalPanel** - Advanced terminal panel with enhanced features
- **ICUIEnhancedPanelArea** - Layout-specific panel area (different from ICUIPanelArea)

## Service Architecture

The service layer already uses optimal architecture:
- **Public APIs**: Clean names (e.g., `WebSocketService`, `ChatBackendClient`)
- **Implementations**: Enhanced files provide the actual functionality
- **Compatibility**: Automatic re-exports handle the bridging

Example:
```typescript
// These both import the same enhanced implementation
import { WebSocketService } from 'icui/services'; // ✅ Recommended
import { EnhancedWebSocketService } from 'icui/services'; // ✅ Also works
```

## Migration Steps

1. **Update Imports**: Replace Enhanced component imports with clean versions
2. **Update Types**: Use types from the new clean components
3. **Update Component Usage**: Replace component names in JSX
4. **Test**: Ensure functionality remains the same

## Backward Compatibility

All Enhanced components remain available and fully functional. The cleanup provides:
- **Clean primary exports** for new development
- **Deprecated Enhanced exports** for existing code
- **Zero breaking changes** during migration period

## Benefits

- **Cleaner API**: More intuitive component names
- **Better Developer Experience**: Easier component discovery
- **Reduced Cognitive Load**: No need to decide between "Enhanced" and regular versions
- **Future-Proof**: Architecture ready for continued development

## Support

For questions about the migration, see:
- [Enhanced Cleanup Plan](./plans/enhanced_cleanup_plan.md)
- [CHANGELOG.md](../CHANGELOG.md) - August 2025 Enhanced Cleanup section
