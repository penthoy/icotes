/**
 * VideoPlayer
 *
 * Phase 1 implementation: a lightweight wrapper around the native <video> element.
 *
 * Notes:
 * - We rely on the browser for decoding/controls in Phase 1.
 * - We keep this component isolated so it can later be reused as a chat widget.
 */

import React, { useCallback, useState } from 'react';

export interface VideoPlayerProps {
  srcUrl: string;
  title: string;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ srcUrl, title }) => {
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [videoError, setVideoError] = useState(false);

  const handleLoaded = useCallback(() => {
    setVideoLoaded(true);
    setVideoError(false);
  }, []);

  const handleError = useCallback(() => {
    setVideoLoaded(false);
    setVideoError(true);
  }, []);

  return (
    <div className="flex-1 relative overflow-hidden">
      {!videoLoaded && !videoError && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin text-4xl mb-2">⏳</div>
            <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
              Loading video...
            </p>
          </div>
        </div>
      )}

      {videoError && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div
            className="text-center p-6 rounded-lg max-w-md"
            style={{
              backgroundColor: 'var(--icui-bg-secondary)',
              border: '1px solid var(--icui-border-subtle)'
            }}
          >
            <div className="text-4xl mb-3">⚠️</div>
            <h3 className="text-lg font-semibold mb-2">Failed to Play Video</h3>
            <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
              Your browser may not support this video codec/container.
            </p>
          </div>
        </div>
      )}

      <video
        src={srcUrl}
        className="w-full h-full"
        style={{ display: videoError ? 'none' : 'block', backgroundColor: 'black' }}
        controls
        preload="metadata"
        onLoadedData={handleLoaded}
        onError={handleError}
        aria-label={title}
      />
    </div>
  );
};
