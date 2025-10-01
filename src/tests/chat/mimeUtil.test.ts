import { describe, it, expect } from 'vitest';
import { inferMimeFromName } from '../../icui/components/chat/utils/mime';

describe('mime util', () => {
  it('infers common types', () => {
    expect(inferMimeFromName('photo.jpg')).toBe('image/jpeg');
    expect(inferMimeFromName('sound.mp3')).toBe('audio/mp3');
    expect(inferMimeFromName('doc.txt')).toBe('text/plain');
    expect(inferMimeFromName('data.json')).toBe('application/json');
    expect(inferMimeFromName('code.py')).toBe('text/x-python');
  });

  it('falls back for unknown', () => {
    expect(inferMimeFromName('file.unknownext')).toBe('application/octet-stream');
    expect(inferMimeFromName('noext')).toBe('application/octet-stream');
  });
});
