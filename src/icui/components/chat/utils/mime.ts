/**
 * Mime utilities for chat components
 *
 * Keep logic small and frontend-only; backend may perform its own checks.
 */

/** Infer a reasonable MIME type from a filename extension. */
export function inferMimeFromName(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (!ext) return 'application/octet-stream';
  if (['png','jpg','jpeg','gif','webp','bmp','svg'].includes(ext)) return `image/${ext === 'jpg' ? 'jpeg' : ext}`;
  if (['mp3','wav','ogg','m4a','flac'].includes(ext)) return `audio/${ext}`;
  if (ext === 'json') return 'application/json';
  if (ext === 'md') return 'text/markdown';
  if (ext === 'txt' || ext === 'log') return 'text/plain';
  if (ext === 'html' || ext === 'htm') return 'text/html';
  if (ext === 'css') return 'text/css';
  if (ext === 'js' || ext === 'mjs' || ext === 'cjs' || ext === 'ts' || ext === 'tsx') return 'text/plain';
  if (ext === 'py') return 'text/x-python';
  return 'application/octet-stream';
}

export default { inferMimeFromName };
