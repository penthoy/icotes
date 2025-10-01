import { MediaAttachment as ChatMediaAttachment } from '../../../types/chatTypes';
import { inferMimeFromName } from './mime';

// Minimal shape of an upload entry from useMediaUpload
export interface UploadEntry {
  id: string;
  context?: string;
  status: 'pending' | 'uploading' | 'completed' | 'error' | string;
  file: File;
  result?: any; // backend reply shape can vary; we handle common fields
}

/** Polls uploads until none are pending/uploading for the given context. */
export async function waitForUploadsToSettle(
  getUploads: () => UploadEntry[],
  context: string = 'chat',
  timeoutMs: number = 15000,
  sleepMs: number = 150
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const uploads = getUploads();
    const busy = uploads.some(u => u.context === context && (u.status === 'pending' || u.status === 'uploading'));
    if (!busy) return;
    await new Promise(res => setTimeout(res, sleepMs));
  }
}

/** Builds chat attachments from completed uploads for the given context. */
export function buildAttachmentsFromUploads(
  uploads: UploadEntry[],
  context: string = 'chat'
): ChatMediaAttachment[] {
  return uploads
    .filter(u => u.context === context && u.status === 'completed' && u.result)
    .map((u) => {
      const r: any = u.result!;
      const resKind = (r.kind || r.type || '').toString();
      const resMime = (r.mime_type || r.mime || '').toString();
      const resPath = (r.relative_path || r.rel_path || r.path || '').toString();
      const resSize = (typeof r.size_bytes === 'number' ? r.size_bytes : r.size) as number | undefined;
      const originalFileName = u.file?.name;
      const baseName = originalFileName || (resPath ? resPath.split('/').pop() : (r.filename || undefined));
      const localKind: ChatMediaAttachment['kind'] = (
        resKind === 'images' || resKind === 'image' || (resMime && resMime.startsWith('image/'))
      ) ? 'image' : (
        resKind === 'audio' || (resMime && resMime.startsWith('audio/')) ? 'audio' : 'file'
      );
      return {
        id: r.id,
        kind: localKind,
        path: resPath,
        mime: resMime || 'application/octet-stream',
        size: typeof resSize === 'number' ? resSize : 0,
        meta: {
          source: 'upload',
          tempUploadId: u.id,
          filename: baseName,
          originalPath: originalFileName,
        }
      } as ChatMediaAttachment;
    });
}

/** Builds chat attachments from explorer-referenced files. */
export function buildReferencedAttachments(
  referenced: { id: string; path: string; name: string; kind: 'file' }[]
): ChatMediaAttachment[] {
  return referenced.map(ref => {
    const mime = inferMimeFromName(ref.name);
    const isImage = mime.startsWith('image/');
    return {
      id: ref.id,
      kind: isImage ? 'image' : 'file',
      path: ref.path,
      mime,
      size: 0,
      meta: { source: 'explorer', filename: ref.name }
    } as ChatMediaAttachment;
  });
}
