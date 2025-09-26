import { getParentDirectoryPath, isDescendantPath, joinPathSegments, normalizeDirPath } from './pathUtils';

export interface ExplorerMoveDescriptor {
  path: string;
  name?: string;
  type?: 'file' | 'folder';
}

export interface MovePlanningResult {
  operations: { source: string; destination: string }[];
  skipped: string[];
}

type PlannedDescriptor = {
  sourcePath: string;
  name: string;
  type: 'file' | 'folder';
  depth: number;
};

export function planExplorerMoveOperations({
  descriptors,
  destinationDir,
}: {
  descriptors: ExplorerMoveDescriptor[];
  destinationDir: string;
}): MovePlanningResult {
  const normalizedDestination = normalizeDirPath(destinationDir);
  const uniqueDescriptors: PlannedDescriptor[] = [];
  const seenPaths = new Set<string>();
  const skipped: string[] = [];

  descriptors.forEach((descriptor, index) => {
    const normalizedPath = normalizeDirPath(descriptor.path);
    if (seenPaths.has(normalizedPath)) {
      return;
    }

    const safeNameCandidate = descriptor.name ?? descriptor.path.split('/').pop() ?? `item-${index}`;
    const safeName = safeNameCandidate.replace(/[\\/]+/g, '').trim();
    if (!safeName || normalizedPath === '/') {
      return;
    }

    seenPaths.add(normalizedPath);
    const depth = normalizedPath === '/' ? 0 : normalizedPath.split('/').filter(Boolean).length;
    uniqueDescriptors.push({
      sourcePath: normalizedPath,
      name: safeName,
      type: descriptor.type ?? 'file',
      depth,
    });
  });

  uniqueDescriptors.sort((a, b) => a.depth - b.depth);

  const minimalDescriptors = uniqueDescriptors.filter((descriptor, index, array) => {
    const hasAncestor = array.some((other, otherIndex) => {
      if (index === otherIndex) return false;
      return isDescendantPath(other.sourcePath, descriptor.sourcePath);
    });
    if (hasAncestor) {
      skipped.push(descriptor.sourcePath);
      return false;
    }
    return true;
  });

  const operations: { source: string; destination: string }[] = [];
  const plannedDestinations = new Set<string>();

  minimalDescriptors.forEach(descriptor => {
    const { sourcePath, name } = descriptor;

    if (sourcePath === normalizedDestination) {
      skipped.push(sourcePath);
      return;
    }

    const parentDir = getParentDirectoryPath(sourcePath);
    if (parentDir === normalizedDestination) {
      skipped.push(sourcePath);
      return;
    }

    if (isDescendantPath(sourcePath, normalizedDestination)) {
      skipped.push(sourcePath);
      return;
    }

    const destinationPath = joinPathSegments(normalizedDestination, name);
    if (plannedDestinations.has(destinationPath)) {
      throw new Error(
        `Cannot move selection: multiple items named “${name}” would conflict in the destination.`
      );
    }

    operations.push({ source: sourcePath, destination: destinationPath });
    plannedDestinations.add(destinationPath);
  });

  return { operations, skipped };
}
