/**
 * Explorer utility helpers extracted from ICUIExplorer for reuse and testing.
 * These functions are intentionally pure and UI-agnostic.
 */

import type { ICUIFileNode } from '../../services/backend-service-impl';

/** Flatten the visible tree respecting folder expansion flags. */
export function flattenVisibleTree(files: ICUIFileNode[]): ICUIFileNode[] {
  const result: ICUIFileNode[] = [];
  const stack: ICUIFileNode[] = files.slice().reverse();
  while (stack.length > 0) {
    const node = stack.pop()!;
    result.push(node);
    if (node.type === 'folder' && node.isExpanded && node.children) {
      for (let i = node.children.length - 1; i >= 0; i--) {
        stack.push(node.children[i] as ICUIFileNode);
      }
    }
  }
  return result;
}

/** Build a Map keyed by path for quick node lookup. */
export function buildNodeMapByPath(nodes: ICUIFileNode[], map: Map<string, ICUIFileNode> = new Map()): Map<string, ICUIFileNode> {
  for (const n of nodes) {
    map.set(n.path, n);
    if (n.children && n.children.length > 0) buildNodeMapByPath(n.children as ICUIFileNode[], map);
  }
  return map;
}

/**
 * Create an annotateWithExpansion function bound to a Set of expanded paths.
 * It optionally reuses previous children to preserve already-expanded subtrees.
 */
export function createAnnotateWithExpansion(expandedPaths: Set<string>) {
  const annotate = (
    nodes: ICUIFileNode[],
    prevMap?: Map<string, ICUIFileNode>,
    preferNewChildren: boolean = false,
  ): ICUIFileNode[] => {
    const prev = prevMap || new Map<string, ICUIFileNode>();
    const walk = (list: ICUIFileNode[]): ICUIFileNode[] =>
      list.map(node => {
        if (node.type === 'folder') {
          const shouldExpand = expandedPaths.has(node.path);
          const prevNode = prev.get(node.path);
          const rawChildren = preferNewChildren
            ? (node.children as ICUIFileNode[] | undefined)
            : ((node.children as ICUIFileNode[] | undefined) ?? (shouldExpand ? (prevNode?.children as ICUIFileNode[] | undefined) : undefined));
          const children = rawChildren ? walk(rawChildren as ICUIFileNode[]) : rawChildren;
          return { ...node, isExpanded: shouldExpand, children } as ICUIFileNode;
        }
        return node;
      });
    return walk(nodes);
  };
  return annotate;
}

/**
 * Apply folder children fetch results to the current tree, preserving expansion flags.
 */
export function applyChildrenResults(
  current: ICUIFileNode[],
  results: { path: string; children: ICUIFileNode[] }[],
  prevMap: Map<string, ICUIFileNode>,
  annotateWithExpansion: (
    nodes: ICUIFileNode[],
    prevMap?: Map<string, ICUIFileNode>,
    preferNewChildren?: boolean,
  ) => ICUIFileNode[],
): ICUIFileNode[] {
  const byPath = new Map(results.map(r => [r.path, r.children] as const));
  const apply = (nodes: ICUIFileNode[]): ICUIFileNode[] =>
    nodes.map(node => {
      if (node.type === 'folder') {
        const replacedChildren = byPath.has(node.path) ? (byPath.get(node.path) as ICUIFileNode[]) : (node.children as ICUIFileNode[] | undefined);
        const annotated = replacedChildren ? annotateWithExpansion(replacedChildren, prevMap, true) : replacedChildren;
        const deepApplied = annotated ? apply(annotated) : annotated;
        return { ...node, children: deepApplied } as ICUIFileNode;
      }
      return node;
    });
  return apply(current);
}

/** Depth-first search by node id. */
export function findNodeInTree(nodes: ICUIFileNode[], nodeId: string): ICUIFileNode | null {
  for (const node of nodes) {
    if (node.id === nodeId) return node;
    if (node.children) {
      const found = findNodeInTree(node.children, nodeId);
      if (found) return found;
    }
  }
  return null;
}
