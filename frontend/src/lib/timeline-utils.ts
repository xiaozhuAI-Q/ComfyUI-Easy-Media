import type { TimelineData, Track, TrackType } from '@/types/timeline'
import { uuid } from './uuid'
/**
 * Converts seconds to frame count using the formula from the spec:
 *   frames = ceil(seconds * frameRate / 4) * 4 + 1
 */
export function secondsToFrames(seconds: number, frameRate: number): number {
  return Math.ceil((seconds * frameRate) / 4) * 4 + 1
}

/**
 * Converts seconds to frame count for audio playback (no +1 offset).
 * Use this when computing audio segment duration or seeking.
 *   frames = ceil(seconds * frameRate)
 */
export function secondsToAudioFrames(seconds: number, frameRate: number): number {
  return Math.ceil(seconds * frameRate)
}

/**
 * Converts frame count back to seconds.
 *   seconds = (frames - 1) / frameRate
 */
export function framesToSeconds(frames: number, frameRate: number): number {
  return (frames - 1) / frameRate
}

/**
 * Format a frame index as a display string.
 * mode='frames' → "121f"
 * mode='seconds' → "5.00s"
 */
export function formatTime(
  frames: number,
  frameRate: number,
  mode: 'frames' | 'seconds',
): string {
  if (mode === 'frames') return `${frames}f`
  const secs = framesToSeconds(frames, frameRate)
  return `${secs.toFixed(2)}s`
}

/**
 * Parse a user-entered time string to frames.
 * Accepts "121" (treated as frames), "121f", "5s", "5.0s".
 * Returns NaN if unparseable.
 */
export function parseTimeInput(input: string, frameRate: number): number {
  const trimmed = input.trim()
  if (trimmed.endsWith('s')) {
    const secs = Number.parseFloat(trimmed.slice(0, -1))
    if (Number.isNaN(secs)) return Number.NaN
    return secondsToFrames(secs, frameRate)
  }
  const framesStr = trimmed.endsWith('f') ? trimmed.slice(0, -1) : trimmed
  const frames = Number.parseInt(framesStr, 10)
  return Number.isNaN(frames) ? Number.NaN : frames
}

/** Default colors per track type */
export const TRACK_DEFAULT_COLORS: Record<TrackType, string> = {
  audio: '#34d399',
  prompt: '#a78bfa',
  image: '#fb923c',
  video: '#60a5fa',
  maintain: 'var(--muted)',
}

/** Build a default empty TimelineData with one maintain track and one audio track */
export function createDefaultTimelineData(): TimelineData {
  const total_length = 121
  const frame_rate = 24

  const tracks: Track[] = [
    {
      id: uuid(),
      name: '主轨 1',
      type: 'maintain',
      color: TRACK_DEFAULT_COLORS.maintain,
      muted: false,
      locked: false,
      segments: [
        {
          id: uuid(),
          start_frame: 0,
          end_frame: total_length,
          content: { text: '', images: [], type: 'flf' },
          color: TRACK_DEFAULT_COLORS.maintain,
        },
      ],
    },
    {
      id: uuid(),
      name: '音频轨 1',
      type: 'audio',
      color: TRACK_DEFAULT_COLORS.audio,
      muted: false,
      locked: false,
      segments: [],
    },
  ]

  return { tracks, total_length, frame_rate }
}

/**
 * Returns the pixel left offset and width for a segment on the track content area.
 * @param startFrame  segment start frame (inclusive)
 * @param endFrame    segment end frame (inclusive)
 * @param totalFrames total timeline length in frames
 * @param areaWidth   pixel width of the track content area
 */
export function segmentPixelRect(
  startFrame: number,
  endFrame: number,
  totalFrames: number,
  areaWidth: number,
): { left: number; width: number } {
  const left = (startFrame / (totalFrames - 1)) * areaWidth
  const right = ((endFrame + 1) / (totalFrames - 1)) * areaWidth
  return { left, width: Math.max(right - left, 2) }
}
