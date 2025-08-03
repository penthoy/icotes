# ICUI Framework

**Interactive Component UI Framework** - A modular panel system inspired by Blender's flexible UI design.

## Overview

ICUI is a React-based UI framework that provides a flexible, modular panel system. It allows users to create, remove, and transform panels dynamically while maintaining complete control over the layout.

**Architecture Note**: ICUI follows clean API design principles:
- **Primary components** use intuitive names (`ICUILayout`, `ICUIEditor`, `ICUITerminal`)
- **Enhanced variants** provide specialized features for advanced use cases
- **Service layer** uses Enhanced implementations with clean public APIs

## Core Components

### Layout System
- **`ICUILayout`** (Primary) - Modern layout component with IDE-like panel management  
- **`ICUIEnhancedLayout`** (Deprecated) - Use `ICUILayout` instead
- **`ICUIFrameContainer`** - Frame wrapper with responsive sizing
- **`ICUISplitPanel`** - Resizable split panel system

## Features

- **Responsive Frame Container**: Automatically detects viewport changes and adjusts layout
- **Border Detection**: Detects when panels are at viewport edges
- **Dynamic Resize Handles**: Interactive resize handles that appear on hover
- **TypeScript Support**: Comprehensive type definitions for all components
- **Accessibility**: Built with accessibility in mind
- **Development Tools**: Debug information in development mode

## Components

### ICUIFrameContainer

The foundational responsive frame component that handles layout and border detection.

```tsx
import { ICUIFrameContainer } from '@/icui';

<ICUIFrameContainer
  id="my-frame"
  config={{
    responsive: true,
    borderDetection: true,
    minPanelSize: { width: 200, height: 100 },
  }}
  onResize={(size) => console.log('Resized:', size)}
  onBorderDetected={(borders) => console.log('Borders:', borders)}
>
  <div>Your content here</div>
</ICUIFrameContainer>
```

## Configuration

### ICUIFrameConfig

```typescript
interface ICUIFrameConfig {
  id: string;
  responsive: boolean;
  borderDetection: boolean;
  minPanelSize: ICUISize;
  resizeHandleSize: number;
  snapThreshold: number;
}
```

## Hooks

### useICUIResponsive

Provides viewport detection and responsive utilities.

```tsx
import { useICUIResponsive } from '@/icui';

const { viewport, currentBreakpoint, isMinBreakpoint } = useICUIResponsive();
```

## Current Status

✅ **Step 1.1 Complete**: Frame Container Component
- Responsive frame with border detection
- Dynamic resize handles
- Viewport detection
- TypeScript support
- Development debug tools

## Testing

Visit `/icui-test` to see the framework in action.

## Next Steps

This framework is designed to be extended with additional components:
- Split Panel System (Step 1.2)
- Layout State Management (Step 1.3)
- Generic Panel Base Class (Step 2.1)
- Specialized Panel Implementations (Step 3.x)

## File Structure

```
src/icui/
├── components/
│   └── ICUIFrameContainer.tsx
├── hooks/
│   └── icui-use-responsive.ts
├── types/
│   └── icui-layout.ts
├── styles/
│   └── icui.css
└── index.ts
```

## Development

The framework is built with clean, documented code and follows React best practices. All components are prefixed with `ICUI` to avoid naming conflicts.

---

*ICUI Framework v1.0.0 - Built for modularity and reusability*
