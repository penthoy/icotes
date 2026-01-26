/**
 * MediaPlayerPanel tests
 *
 * We mock wavesurfer because JSDOM does not provide a real WebAudio implementation.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

import { MediaPlayerPanel } from '../../icui/components/editor';

const mockWaveSurferInstance = {
  load: vi.fn(),
  on: vi.fn(),
  destroy: vi.fn(),
  playPause: vi.fn(),
  isPlaying: vi.fn(() => false),
  getDuration: vi.fn(() => 0),
  setVolume: vi.fn(),
  zoom: vi.fn()
};

vi.mock('wavesurfer.js', () => {
  return {
    default: {
      create: vi.fn(() => mockWaveSurferInstance)
    }
  };
});

describe('MediaPlayerPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders video player with <video> element', () => {
    render(
      <MediaPlayerPanel
        filePath="/workspace/video.mp4"
        fileName="video.mp4"
        mediaType="video"
      />
    );

    const video = document.querySelector('video');
    expect(video).toBeInTheDocument();
  });

  it('renders audio player and initializes wavesurfer', async () => {
    const WaveSurfer = (await import('wavesurfer.js')).default as any;

    render(
      <MediaPlayerPanel
        filePath="/workspace/song.mp3"
        fileName="song.mp3"
        mediaType="audio"
      />
    );
    expect(WaveSurfer.create).toHaveBeenCalledTimes(1);
  });
});
