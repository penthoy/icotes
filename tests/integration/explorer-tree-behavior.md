# Explorer Tree Behavior - Manual Test Documentation

## Updated Features (Latest)

### Real-time File System Updates
The Explorer now automatically updates when files/folders are changed outside the application:

**Test Cases:**
1. **External File Creation**
   - Open terminal and create a new file: `touch workspace/test-external.txt`
   - ✅ Explorer should automatically show the new file (within 300ms)
   - File should appear at the bottom of the file list (after folders)

2. **External Directory Creation**
   - Create a new directory: `mkdir workspace/new-external-dir`
   - ✅ Explorer should automatically show the new directory
   - Directory should appear at the top of the list (before files)

3. **External File Deletion**
   - Delete a file from terminal: `rm workspace/test-external.txt`
   - ✅ Explorer should automatically remove the file from the list

4. **External File Move/Rename**
   - Rename a file: `mv workspace/file.txt workspace/renamed-file.txt`
   - ✅ Explorer should update to show the renamed file

5. **WebSocket Connection Test**
   - Check browser console for "Explorer received filesystem event:" messages
   - ✅ Should see events logged when external changes occur

**Notes:**
- Updates are debounced by 300ms to prevent excessive refreshes
- Only file structure changes trigger updates (not content modifications)
- Requires WebSocket connection to backend for real-time updates

## Overview
This document describes the VS Code-like explorer behavior implemented in ICUIExplorer component.

## Expected Behavior

### Folder Click Behavior
- **Before**: Clicking on a folder would navigate into that folder, changing the entire view
- **After**: Clicking on a folder expands/collapses it in place, showing children as nested items

### Visual Indicators
1. **Expand/Collapse Icons**: 
   - > (greater than) for collapsed folders
   - v (downward caret) for expanded folders

2. **Folder Icons**:
   - 📁 for closed folders
   - 📂 for open/expanded folders

3. **Indentation**: Each nesting level is indented by 16px

### Tree Structure
- Root directory items are shown at the top level
- **Folders are always displayed first, followed by files (both sorted alphabetically)**
- Folder children are loaded on-demand when first expanded
- Tree state is maintained (expanded folders stay expanded)
- File selection works at any level of nesting

## Manual Testing Steps

### Test 1: Basic Folder Expansion
1. Open the application with Explorer panel visible
2. Locate a folder in the root directory
3. Click on the folder
4. **Expected**: Folder expands in place, showing children with proper indentation
5. Click on the folder again
6. **Expected**: Folder collapses, hiding children

### Test 2: Nested Folder Navigation
1. Expand a root-level folder
2. Look for subfolders within the expanded folder
3. Click on a subfolder
4. **Expected**: Subfolder expands with additional indentation (32px from root)
5. Verify parent folder remains expanded

### Test 3: Mixed File and Folder Display
1. Expand a folder containing both files and subfolders
2. **Expected**: 
   - Files show with 📄 icon and no expand arrow
   - Folders show with 📁/📂 icon and >/v arrow
   - **Folders appear first, then files (both alphabetically sorted)**
   - Proper sorting and indentation

### Test 4: File Selection
1. Expand folders to show nested files
2. Click on a file at any nesting level
3. **Expected**: File gets selected (highlighted) but no expansion occurs

### Test 5: Performance Test
1. Navigate to a directory with many subfolders
2. Rapidly expand/collapse multiple folders
3. **Expected**: Smooth performance without navigation delays

### Test 6: Sorting Behavior
1. Open the application with Explorer panel visible
2. Observe the root directory structure
3. **Expected**: All folders appear at the top, sorted alphabetically
4. **Expected**: All files appear below folders, sorted alphabetically
5. Expand any folder with mixed content
6. **Expected**: Same sorting behavior applies to subfolders (folders first, then files)

## Technical Implementation

### Key Changes Made
1. Modified `handleItemClick` in `ICUIExplorer.tsx` to call `toggleFolderExpansion` instead of `loadDirectory`
2. Added `toggleFolderExpansion` function to manage expand/collapse state
3. Updated `renderFileTree` to support recursive rendering with indentation
4. Added on-demand children loading when folders are expanded
5. Enhanced visual indicators for tree navigation

### Component State
- `files`: Array of FileNode with tree structure
- Each FileNode has `isExpanded` and `children` properties
- Children are loaded lazily when folder is first expanded

## Integration Points

### Backend API Usage
- Uses existing `/files?path=` endpoint for loading directory contents
- Loads children on-demand rather than full tree at once
- Maintains compatibility with existing file operations

### Component Integration
- Works with existing ICUIExplorer props and callbacks
- Maintains file selection callback (`onFileSelect`)
- Preserves file operation callbacks (create, delete, rename)

## Future Enhancements
1. Add keyboard navigation (arrow keys, enter, space)
2. Implement drag-and-drop for file/folder operations
3. Add context menu for folder operations
4. Implement search/filter functionality within tree
5. Add folder refresh option for real-time updates
