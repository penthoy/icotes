/**
 * AudioWaveformPlayer
 *
 * Phase 1 implementation: waveform visualization + basic playback controls using wavesurfer.js.
 *
 * We keep this component isolated so it can later be reused as a chat widget.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import { Pause, Play, Volume2 } from 'lucide-react';

export interface AudioWaveformPlayerProps {
  srcUrl: string;
  title: string;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export const AudioWaveformPlayer: React.FC<AudioWaveformPlayerProps> = ({ srcUrl, title }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const waveSurferRef = useRef<WaveSurfer | null>(null);

  const [isReady, setIsReady] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);

  const waveformColors = useMemo(
    () => ({
      waveColor: 'rgba(180, 180, 190, 0.45)',
      progressColor: 'rgba(120, 180, 255, 0.95)',
      cursorColor: 'rgba(255, 255, 255, 0.6)'
    }),
    []
  );

  useEffect(() => {
    if (!containerRef.current) return;

    setIsReady(false);
    setHasError(false);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height: 120,
      normalize: true,
      backend: 'WebAudio',
      ...waveformColors
    });

    waveSurferRef.current = ws;

    const handleReady = () => {
      setIsReady(true);
      setHasError(false);
      setDuration(ws.getDuration() || 0);
      ws.setVolume(volume);
    };

    const handleError = () => {
      setHasError(true);
      setIsReady(false);
    };

    const handleTimeUpdate = (time: number) => {
      setCurrentTime(time);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    ws.on('ready', handleReady);
    ws.on('error', handleError);
    ws.on('timeupdate', handleTimeUpdate);
    ws.on('play', handlePlay);
    ws.on('pause', handlePause);

    ws.load(srcUrl);

    return () => {
      ws.destroy();
      waveSurferRef.current = null;
    };
  }, [srcUrl, waveformColors]);

  // Separate effect for volume changes (doesn't reload audio)
  useEffect(() => {
    if (waveSurferRef.current && isReady) {
      waveSurferRef.current.setVolume(volume);
    }
  }, [volume, isReady]);

  const togglePlay = useCallback(() => {
    waveSurferRef.current?.playPause();
  }, []);

  const onVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const nextVolume = Number(e.target.value);
    setVolume(nextVolume);
    waveSurferRef.current?.setVolume(nextVolume);
  }, []);

  const iconButtonStyle = useMemo<React.CSSProperties>(() => {
    return {
      backgroundColor: 'var(--icui-bg-tertiary)',
      color: 'var(--icui-text-primary)'
    };
  }, []);

  return (
    <div className="flex flex-col flex-1">
      <div className="flex-1 relative overflow-hidden">
        {!isReady && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin text-4xl mb-2">⏳</div>
              <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
                Loading audio...
              </p>
            </div>
          </div>
        )}

        {hasError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div
              className="text-center p-6 rounded-lg max-w-md"
              style={{
                backgroundColor: 'var(--icui-bg-secondary)',
                border: '1px solid var(--icui-border-subtle)'
              }}
            >
              <div className="text-4xl mb-3">⚠️</div>
              <h3 className="text-lg font-semibold mb-2">Failed to Play Audio</h3>
              <p className="text-sm" style={{ color: 'var(--icui-text-secondary)' }}>
                Your browser may not support this audio codec/container.
              </p>
            </div>
          </div>
        )}

        <div
          ref={containerRef}
          className="w-full h-full"
          aria-label={title}
          style={{
            display: hasError ? 'none' : 'block',
            backgroundColor: 'var(--icui-bg-primary)'
          }}
        />
      </div>

      {/* Bottom Controls (similar placement to native video controls) */}
      <div
        className="flex items-center justify-between px-4 py-2 border-t"
        style={{
          borderColor: 'var(--icui-border-subtle)',
          backgroundColor: 'var(--icui-bg-secondary)'
        }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={togglePlay}
            className="h-8 w-8 inline-flex items-center justify-center rounded transition-colors"
            style={iconButtonStyle}
            title={isPlaying ? 'Pause' : 'Play'}
            disabled={!isReady || hasError}
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>

          <span className="text-xs whitespace-nowrap" style={{ color: 'var(--icui-text-secondary)' }}>
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div
            className="h-8 w-8 inline-flex items-center justify-center rounded"
            style={iconButtonStyle}
            title="Volume"
            aria-label="Volume"
          >
            <Volume2 size={16} />
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={onVolumeChange}
            aria-label="Volume"
            disabled={!isReady || hasError}
            style={{ width: 160 }}
          />
        </div>
      </div>
    </div>
  );
};
