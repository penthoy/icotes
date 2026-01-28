/**
 * File type detection tests for multimedia extensions.
 *
 * Phase 1 coverage: ensure editor can route audio/video files to the correct viewer.
 */

import { describe, it, expect } from 'vitest';
import {
  detectFileTypeFromExtension,
  supportedFileTypes
} from '../../icui/components/editor/utils/fileTypeDetection';

describe('fileTypeDetection (media)', () => {
  it('detects audio extensions', () => {
    expect(detectFileTypeFromExtension('/workspace/song.mp3')).toBe('audio');
    expect(detectFileTypeFromExtension('/workspace/recording.wav')).toBe('audio');
    expect(detectFileTypeFromExtension('/workspace/voice.m4a')).toBe('audio');
  });

  it('detects video extensions', () => {
    expect(detectFileTypeFromExtension('/workspace/video.mp4')).toBe('video');
    expect(detectFileTypeFromExtension('/workspace/clip.mov')).toBe('video');
    expect(detectFileTypeFromExtension('/workspace/demo.webm')).toBe('video');
  });

  it('includes audio/video in supportedFileTypes', () => {
    const ids = new Set(supportedFileTypes.map(t => t.id));
    expect(ids.has('audio')).toBe(true);
    expect(ids.has('video')).toBe(true);
  });
});
