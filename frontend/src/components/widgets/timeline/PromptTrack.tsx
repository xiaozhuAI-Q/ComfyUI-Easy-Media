import { useState } from 'react'
import { AlignJustify, Plus, Trash2 } from 'lucide-react'
import type { Track, PromptSegment, Segment, TimeDisplayFormat } from '@/types/timeline'
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { SegmentBlock } from './SegmentBlock'
import { TrackRow } from './TrackRow'
// import { PromptEditDialog } from './PromptEditDialog'
import { useT } from '@/lib/i18n'
import { uuid } from '@/lib/uuid'

interface PromptTrackProps {
  track: Track
  totalFrames: number
  frameRate: number
  displayFormat: TimeDisplayFormat
  areaWidth: number
  selectedId: string | null
  onSelectedIdChange: (id: string | null) => void
  onTrackChange: (patch: Partial<Track>) => void
  onSegmentsChange: (segments: Segment[]) => void
}

/** Evenly distribute all segments across total span. */
function distributeEvenly(segs: Segment[], totalFrames: number): Segment[] {
  if (segs.length === 0) return segs
  const base = Math.floor((totalFrames - 1) / segs.length)
  const remainder = (totalFrames - 1) % segs.length
  let cursor = 0
  return segs.map((s, i) => {
    const size = base + (i < remainder ? 1 : 0)
    const start_frame = cursor
    cursor += size
    const end_frame = i < segs.length - 1 ? cursor - 1 : totalFrames - 1
    return { ...s, start_frame, end_frame }
  })
}

export function PromptTrack({
  track,
  totalFrames,
  frameRate,
  displayFormat,
  areaWidth,
  selectedId,
  onSelectedIdChange,
  onTrackChange,
  onSegmentsChange,
}: Readonly<PromptTrackProps>) {
  const t = useT()
  // const [editDialogOpen, setEditDialogOpen] = useState(false)
  // const [focusedSegmentId, setFocusedSegmentId] = useState<string | null>(null)
  const [rightClickedId, setRightClickedId] = useState<string | null>(null)

  function formatDuration(seg: PromptSegment): string {
    const frames = seg.end_frame - seg.start_frame + 1
    if (displayFormat === 'seconds') {
      return `${(frames / frameRate).toFixed(1)}s`
    }
    return `${frames}f`
  }

  const segments = track.segments as PromptSegment[]

  function handleDragEnd(segmentId: string, deltaFrames: number, origStart: number) {
    const seg = segments.find((s) => s.id === segmentId)
    if (!seg) return
    const span = seg.end_frame - seg.start_frame
    const newStart = Math.max(0, origStart + deltaFrames)
    const newEnd = Math.min(totalFrames - 1, newStart + span)
    const clampedStart = newEnd - span

    // Place the dragged segment at its new (potentially overlapping) position
    const withDragged = segments.map((s) =>
      s.id === segmentId ? { ...s, start_frame: clampedStart, end_frame: newEnd } : s,
    )

    // Sort by center to determine new display order (triggers slot swap when crossing)
    const sortedByCenter = [...withDragged].sort(
      (a, b) => (a.start_frame + a.end_frame) - (b.start_frame + b.end_frame),
    )

    // Original frame slots in positional order
    const originalSlots = [...segments]
      .sort((a, b) => a.start_frame - b.start_frame)
      .map((s) => ({ start_frame: s.start_frame, end_frame: s.end_frame }))

    // Re-assign slots: whichever segment is now at position i gets slot i
    const result = sortedByCenter.map((s, i) => ({
      ...s,
      start_frame: originalSlots[i].start_frame,
      end_frame: originalSlots[i].end_frame,
    }))

    onSegmentsChange(result)
  }

  function handleResizeEnd(segmentId: string, edge: 'start' | 'end', deltaFrames: number) {
    if (track.locked) return
    const idx = segments.findIndex((s) => s.id === segmentId)
    if (idx === -1) return
    const seg = segments[idx]
    const updated = [...segments]

    if (edge === 'end') {
      const next = updated[idx + 1]
      const minEnd = seg.start_frame + 1
      const maxEnd = next ? next.end_frame - 1 : totalFrames - 1
      const newEnd = Math.max(minEnd, Math.min(maxEnd, seg.end_frame + deltaFrames))
      updated[idx] = { ...seg, end_frame: newEnd }
      // Shift next segment start to fill
      if (next) updated[idx + 1] = { ...next, start_frame: newEnd + 1 }
    } else {
      const prev = updated[idx - 1]
      const maxStart = seg.end_frame - 1
      const minStart = prev ? prev.start_frame + 1 : 0
      const newStart = Math.max(minStart, Math.min(maxStart, seg.start_frame + deltaFrames))
      updated[idx] = { ...seg, start_frame: newStart }
      if (prev) updated[idx - 1] = { ...prev, end_frame: newStart - 1 }
    }

    onSegmentsChange(updated)
  }

  function addSegment(text = '') {
    if (segments.length === 0) {
      onSegmentsChange([
        {
          id: uuid(),
          start_frame: 0,
          end_frame: totalFrames - 1,
          content: { text },
          color: track.color,
        },
      ])
      return
    }
    // Split last segment in half
    const last = segments.at(-1)!
    const mid = Math.floor((last.start_frame + last.end_frame) / 2)
    const updated = [
      ...segments.slice(0, -1),
      { ...last, end_frame: mid },
      {
        id: uuid(),
        start_frame: mid + 1,
        end_frame: last.end_frame,
        content: { text },
        color: track.color,
      },
    ]
    onSegmentsChange(updated)
  }

  function deleteSegment(id: string) {
    if (segments.length <= 1) return
    const idx = segments.findIndex((s) => s.id === id)
    if (idx === -1) return
    const updated = [...segments]
    const [removed] = updated.splice(idx, 1)
    // Fill the gap: expand the left neighbor's end, or right neighbor's start if first
    if (idx > 0) {
      updated[idx - 1] = { ...updated[idx - 1], end_frame: removed.end_frame }
    } else if (updated.length > 0) {
      updated[0] = { ...updated[0], start_frame: removed.start_frame }
    }
    onSegmentsChange(updated)
    onSelectedIdChange(null)
  }

  const toolSlots: [React.ReactNode, React.ReactNode, React.ReactNode] = [
    <button
      key="distribute"
      type="button"
      title={t('promptTrack.distributeEvenly')}
      className="w-full h-full flex items-center justify-center hover:bg-accent cursor-pointer "
      onClick={() => onSegmentsChange(distributeEvenly(segments, totalFrames))}
    >
      <AlignJustify className="w-2.5 h-2.5 text-muted-foreground" />
    </button>,
    <button
      key="add"
      type="button"
      title={t('promptTrack.addSegment')}
      className="w-full h-full flex items-center justify-center hover:bg-accent cursor-pointer"
      onClick={() => addSegment()}
    >
      <Plus className="w-2.5 h-2.5 text-muted-foreground" />
    </button>,
    <button
      key="delete"
      type="button"
      title={t('promptTrack.deleteSegment')}
      disabled={!selectedId || segments.length <= 1}
      className="w-full h-full flex items-center justify-center hover:bg-accent disabled:opacity-25 cursor-pointer"
      onClick={() => { if (selectedId) deleteSegment(selectedId) }}
    >
      <Trash2 className="w-2.5 h-2.5 text-muted-foreground" />
    </button>,
  ]

  return (
    <TrackRow track={track} onTrackChange={onTrackChange} toolSlots={toolSlots}>
      <ContextMenu>
        <ContextMenuTrigger className="relative block w-full h-full">
          {segments.map((seg, index) => (
            <SegmentBlock
              key={seg.id}
              segment={seg}
              totalFrames={totalFrames}
              areaWidth={areaWidth}
              interactive={!track.locked}
              hideLeftHandle={index === 0}
              selected={selectedId === seg.id}
              onSelect={(s) => onSelectedIdChange(selectedId === s.id ? null : s.id)}
              onDragEnd={handleDragEnd}
              onResizeEnd={handleResizeEnd}
              onDoubleClick={() => { /* openEditDialog(seg.id) */ }}
              onContextMenu={(_, s) => {
                setRightClickedId(s.id)
                onSelectedIdChange(s.id)
              }}
            >
              <div className="flex flex-col h-full justify-between py-0.5 min-w-0 px-0.5">
                <div className="flex items-start justify-between gap-1 min-w-0">
                  <span className="text-[10px] font-semibold leading-tight truncate">
                    {t('promptTrack.segmentLabel', { n: index + 1 })}
                  </span>
                  <span className="text-[9px] leading-tight shrink-0 opacity-70">
                    {formatDuration(seg)}
                  </span>
                </div>
                <div className="text-[10px] leading-tight truncate opacity-80">
                  {seg.content.text || <span className="italic opacity-60">{t('promptTrack.empty')}</span>}
                </div>
              </div>
            </SegmentBlock>
          ))}
        </ContextMenuTrigger>
        <ContextMenuContent onCloseAutoFocus={() => setRightClickedId(null)}>
          {rightClickedId && (
            <>
              <ContextMenuItem onClick={() => { /* openEditDialog(rightClickedId) */ }}>
                {t('promptTrack.contextEdit')}
              </ContextMenuItem>
              <ContextMenuItem
                onClick={() => { deleteSegment(rightClickedId); setRightClickedId(null) }}
                disabled={segments.length <= 1}
              >
                {t('common.delete')}
              </ContextMenuItem>
            </>
          )}
          <ContextMenuItem onClick={() => addSegment()}>{t('promptTrack.contextAdd')}</ContextMenuItem>
          <ContextMenuItem onClick={() => onSegmentsChange(distributeEvenly(segments, totalFrames))}>
            {t('promptTrack.contextDistribute')}
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      {/* PromptEditDialog — commented out for future reference
      <PromptEditDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        segments={segments}
        totalFrames={totalFrames}
        frameRate={frameRate}
        displayFormat={displayFormat}
        focusedSegmentId={focusedSegmentId}
        trackColor={track.color}
        onSegmentsChange={onSegmentsChange}
      />
      */}
    </TrackRow>
  )
}
