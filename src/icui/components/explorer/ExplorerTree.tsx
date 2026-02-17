import React from 'react';
import { ChevronDown, ChevronRight, FolderOpen, Folder } from 'lucide-react';
import type { ICUIFileNode } from '../../services';
import { getFileIcon as getFileIconUtil } from './icons';

export interface ExplorerTreeProps {
  nodes: ICUIFileNode[];
  level?: number;
  isPathLocked: boolean;
  currentPath: string;
  dragHoverId: string | null;
  renamingFileId: string | null;
  renameValue: string;
  renameInputRef: React.RefObject<HTMLInputElement>;
  parentPath?: string | null;
  // selection + dnd
  isSelected: (id: string) => boolean;
  getDragProps: (node: ICUIFileNode) => Record<string, any>;
  handleItemDragOver: (e: React.DragEvent, node: ICUIFileNode) => void;
  handleItemDragLeave: (e: React.DragEvent, node: ICUIFileNode) => void;
  handleItemDrop: (e: React.DragEvent, node: ICUIFileNode) => void | Promise<void>;
  // clicks
  handleItemClick: (node: ICUIFileNode, e: React.MouseEvent) => void;
  handleItemDoubleClick: (node: ICUIFileNode, e: React.MouseEvent) => void;
  handleContextMenu: (e: React.MouseEvent | { clientX: number; clientY: number; preventDefault?: () => void; stopPropagation?: () => void }, node?: ICUIFileNode) => void;
  // rename
  handleRenameKeyDown: (e: React.KeyboardEvent) => void;
  confirmRename: () => void;
  setRenameValue: (v: string) => void;
  // navigation
  loadDirectory: (path: string) => void | Promise<void>;
}

export const ExplorerTree: React.FC<ExplorerTreeProps> = ({
  nodes,
  level = 0,
  isPathLocked,
  currentPath,
  dragHoverId,
  renamingFileId,
  renameValue,
  renameInputRef,
  isSelected,
  getDragProps,
  handleItemDragOver,
  handleItemDragLeave,
  handleItemDrop,
  handleItemClick,
  handleItemDoubleClick,
  handleContextMenu,
  handleRenameKeyDown,
  confirmRename,
  setRenameValue,
  loadDirectory,
  parentPath,
}) => {
  const items: React.ReactNode[] = [];

  const longPressStateRef = React.useRef<{
    timeoutId: number | null;
    pointerId: number | null;
    startX: number;
    startY: number;
  }>({ timeoutId: null, pointerId: null, startX: 0, startY: 0 });

  const suppressNextClickRef = React.useRef(false);

  const clearLongPress = React.useCallback(() => {
    if (longPressStateRef.current.timeoutId != null) {
      window.clearTimeout(longPressStateRef.current.timeoutId);
    }
    longPressStateRef.current.timeoutId = null;
    longPressStateRef.current.pointerId = null;
  }, []);

  const startLongPress = React.useCallback((e: React.PointerEvent, node: ICUIFileNode) => {
    if (e.pointerType !== 'touch') return;
    if (renamingFileId === node.path) return;

    clearLongPress();

    longPressStateRef.current.pointerId = e.pointerId;
    longPressStateRef.current.startX = e.clientX;
    longPressStateRef.current.startY = e.clientY;

    // Typical mobile long-press threshold
    const timeoutId = window.setTimeout(() => {
      suppressNextClickRef.current = true;

      handleContextMenu(
        {
          clientX: longPressStateRef.current.startX,
          clientY: longPressStateRef.current.startY,
          preventDefault: () => {},
          stopPropagation: () => {},
        },
        node
      );

      clearLongPress();
    }, 550);

    longPressStateRef.current.timeoutId = timeoutId;
  }, [clearLongPress, handleContextMenu, renamingFileId]);

  const maybeCancelLongPressOnMove = React.useCallback((e: React.PointerEvent) => {
    if (e.pointerType !== 'touch') return;
    if (longPressStateRef.current.pointerId !== e.pointerId) return;

    const dx = e.clientX - longPressStateRef.current.startX;
    const dy = e.clientY - longPressStateRef.current.startY;
    const distance = Math.hypot(dx, dy);
    if (distance > 10) {
      clearLongPress();
    }
  }, [clearLongPress]);

  // Top-level ".." parent navigation when unlocked OR when directory is empty (at any level)
  const shouldShowParent = level === 0 && parentPath && (nodes.length === 0 || !isPathLocked);
  if (shouldShowParent) {
    const navigateToParent = () => {
      if (parentPath) loadDirectory(parentPath);
    };
    items.push(
      <div key="parent-nav" className="select-none">
        <div
          className="flex items-center cursor-pointer py-1 px-2 rounded-sm group transition-colors hover:bg-opacity-50"
          style={{ paddingLeft: `${level * 16 + 8}px`, backgroundColor: 'transparent', color: 'var(--icui-text-secondary)' }}
          onClick={navigateToParent}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--icui-bg-secondary)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
        >
          <span className="text-sm font-mono mr-2" style={{ color: 'var(--icui-text-secondary)' }}>📁</span>
          <span className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>...</span>
        </div>
      </div>
    );
  }

  // Regular file/folder rows
  for (const node of nodes) {
    const dragProps = getDragProps(node);
    const isDragTarget = dragHoverId === node.id;
    const paddingLeft = `${level * 16 + 8}px`;
    const rowBg = isSelected(node.id) ? 'var(--icui-bg-tertiary)' : 'transparent';

    items.push(
      <div key={node.id} className="select-none" data-path={node.path} data-type={node.type}>
        <div
          className={`flex items-center cursor-pointer py-1 px-2 rounded-sm group transition-colors ${isDragTarget ? 'ring-2 ring-blue-400 ring-offset-1 ring-offset-transparent' : ''}`}
          style={{ paddingLeft, backgroundColor: rowBg, color: 'var(--icui-text-primary)' }}
          {...dragProps}
          onDragOver={(e) => handleItemDragOver(e, node)}
          onDragEnter={(e) => handleItemDragOver(e, node)}
          onDragLeave={(e) => handleItemDragLeave(e, node)}
          onDrop={(e) => handleItemDrop(e, node)}
          onClick={(e) => {
            if (suppressNextClickRef.current) {
              suppressNextClickRef.current = false;
              e.preventDefault();
              e.stopPropagation();
              return;
            }
            handleItemClick(node, e);
          }}
          onDoubleClick={(e) => handleItemDoubleClick(node, e)}
          onContextMenu={(e) => handleContextMenu(e, node)}
          onPointerDown={(e) => startLongPress(e, node)}
          onPointerMove={maybeCancelLongPressOnMove}
          onPointerUp={clearLongPress}
          onPointerCancel={clearLongPress}
          onPointerLeave={clearLongPress}
          onMouseEnter={(e) => { if (!isSelected(node.id)) e.currentTarget.style.backgroundColor = 'var(--icui-bg-secondary)'; }}
          onMouseLeave={(e) => { if (!isSelected(node.id)) e.currentTarget.style.backgroundColor = 'transparent'; }}
        >
          {node.type === 'folder' ? (
            <div className="flex items-center flex-1 min-w-0">
              {isPathLocked && (
                <>
                  {node.isExpanded ? (
                    <ChevronDown className="h-4 w-4 mr-1" style={{ color: 'var(--icui-text-secondary)' }} />
                  ) : (
                    <ChevronRight className="h-4 w-4 mr-1" style={{ color: 'var(--icui-text-secondary)' }} />
                  )}
                </>
              )}
              {isPathLocked && node.isExpanded ? (
                <FolderOpen className="h-4 w-4 mr-2" style={{ color: 'var(--icui-accent)' }} />
              ) : (
                <Folder className="h-4 w-4 mr-2" style={{ color: 'var(--icui-accent)' }} />
              )}
              {renamingFileId === node.path ? (
                <input
                  ref={renameInputRef}
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={handleRenameKeyDown}
                  onBlur={confirmRename}
                  className="text-sm bg-transparent border border-blue-500 rounded px-1 py-0 flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  style={{ color: 'var(--icui-text-primary)' }}
                />
              ) : (
                <span className="text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>{node.name}</span>
              )}
            </div>
          ) : (
            <div className="flex items-center flex-1 min-w-0">
              <span className="mr-3 text-sm">{getFileIconUtil(node.name)}</span>
              {renamingFileId === node.path ? (
                <input
                  ref={renameInputRef}
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={handleRenameKeyDown}
                  onBlur={confirmRename}
                  className="text-sm bg-transparent border border-blue-500 rounded px-1 py-0 flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  style={{ color: 'var(--icui-text-primary)' }}
                />
              ) : (
                <span className="text-sm truncate" style={{ color: 'var(--icui-text-primary)' }}>{node.name}</span>
              )}
            </div>
          )}
        </div>
        {isPathLocked && node.type === 'folder' && node.isExpanded && Array.isArray(node.children) && (
          <div>
            <ExplorerTree
              nodes={node.children}
              level={level + 1}
              isPathLocked={isPathLocked}
              currentPath={currentPath}
              dragHoverId={dragHoverId}
              renamingFileId={renamingFileId}
              renameValue={renameValue}
              renameInputRef={renameInputRef}
              isSelected={isSelected}
              getDragProps={getDragProps}
              handleItemDragOver={handleItemDragOver}
              handleItemDragLeave={handleItemDragLeave}
              handleItemDrop={handleItemDrop}
              handleItemClick={handleItemClick}
              handleItemDoubleClick={handleItemDoubleClick}
              handleContextMenu={handleContextMenu}
              handleRenameKeyDown={handleRenameKeyDown}
              confirmRename={confirmRename}
              setRenameValue={setRenameValue}
              loadDirectory={loadDirectory}
              parentPath={null}
            />
          </div>
        )}
      </div>
    );
  }

  return <>{items}</>;
};

export default ExplorerTree;
