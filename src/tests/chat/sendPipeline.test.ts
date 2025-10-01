import { describe, it, expect } from 'vitest';
import { buildReferencedAttachments, buildAttachmentsFromUploads, waitForUploadsToSettle } from '../../icui/components/chat/utils/sendPipeline';

function makeFile(name: string, type: string, content = 'x') {
  return new File([content], name, { type });
}

describe('sendPipeline helpers', () => {
  it('buildReferencedAttachments maps refs to attachments', () => {
    const refs = [
      { id: '1', path: '/abs/a.png', name: 'a.png', kind: 'file' as const },
      { id: '2', path: '/abs/b.txt', name: 'b.txt', kind: 'file' as const },
    ];
    const atts = buildReferencedAttachments(refs);
    expect(atts).toHaveLength(2);
    expect(atts[0].kind).toBe('image');
    expect(atts[1].kind).toBe('file');
    expect(atts[0].mime).toContain('image/');
    expect(atts[1].mime).toBe('text/plain');
  });

  it('buildAttachmentsFromUploads maps completed uploads', () => {
    const uploads: any[] = [
      { id: 'u1', context: 'chat', status: 'completed', file: makeFile('a.png', 'image/png'), result: { id: 'rid1', kind: 'image', mime_type: 'image/png', relative_path: 'media/a.png', size: 100 } },
      { id: 'u2', context: 'chat', status: 'uploading', file: makeFile('b.txt', 'text/plain') },
    ];
    const atts = buildAttachmentsFromUploads(uploads, 'chat');
    expect(atts).toHaveLength(1);
    expect(atts[0].id).toBe('rid1');
    expect(atts[0].kind).toBe('image');
  });

  it('waitForUploadsToSettle resolves once no pending/uploading remain', async () => {
    const state: any[] = [
      { id: 'u1', context: 'chat', status: 'uploading', file: makeFile('a.png', 'image/png') },
    ];
    setTimeout(() => { state[0].status = 'completed'; }, 50);
    const started = Date.now();
    await waitForUploadsToSettle(() => state as any, 'chat', 2000, 10);
    expect(Date.now() - started).toBeGreaterThanOrEqual(40);
  });
});
