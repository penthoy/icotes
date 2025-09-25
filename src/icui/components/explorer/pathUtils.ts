export const normalizeDirPath = (value: string): string => {
  if (!value) return '/';
  const replaced = value.replace(/\\/g, '/').replace(/\/+/g, '/');
  if (replaced === '' || replaced === '/') {
    return '/';
  }
  return replaced.endsWith('/') ? replaced.slice(0, -1) : replaced;
};

export const joinPathSegments = (dir: string, name: string): string => {
  const safeDir = normalizeDirPath(dir);
  const safeName = name.replace(/[\\/]+/g, '');
  if (safeDir === '/') {
    return `/${safeName}`.replace(/\/+/g, '/');
  }
  return `${safeDir}/${safeName}`.replace(/\/+/g, '/');
};

export const getParentDirectoryPath = (path: string): string => {
  const normalized = normalizeDirPath(path);
  if (normalized === '/') return '/';
  const parts = normalized.split('/');
  parts.pop();
  const parent = parts.join('/') || '/';
  return parent === '' ? '/' : parent;
};

export const isDescendantPath = (potentialAncestor: string, potentialChild: string): boolean => {
  const ancestor = normalizeDirPath(potentialAncestor);
  const child = normalizeDirPath(potentialChild);
  if (ancestor === child) {
    return false;
  }
  if (ancestor === '/') {
    return child !== '/';
  }
  return child.startsWith(`${ancestor}/`);
};
