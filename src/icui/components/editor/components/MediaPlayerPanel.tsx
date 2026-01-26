/**
 * MediaPlayerPanel
 *
 * Editor-facing wrapper that renders either the audio or video player.
 * Mirrors the structure of ImageViewerPanel/PDFViewerPanel for a consistent UX.
 */

import React from 'react';
import { AudioWaveformPlayer } from '../../media/AudioWaveformPlayer';
import { VideoPlayer } from '../../media/VideoPlayer';

export type MediaType = 'audio' | 'video';

export interface MediaPlayerPanelProps {
  filePath: string;
  fileName: string;
  mediaType: MediaType;
}

export const MediaPlayerPanel: React.FC<MediaPlayerPanelProps> = ({
  filePath,
  fileName,
  mediaType
}) => {
  const mediaUrl = `/api/files/raw?path=${encodeURIComponent(filePath)}`;

  return (
    <div
      className="flex flex-col h-full w-full"
      style={{
        backgroundColor: 'var(--icui-bg-primary)',
        color: 'var(--icui-text-primary)'
      }}
    >
      {mediaType === 'audio' ? (
        <AudioWaveformPlayer srcUrl={mediaUrl} title={fileName} />
      ) : (
        <VideoPlayer srcUrl={mediaUrl} title={fileName} />
      )}
    </div>
  );
};
