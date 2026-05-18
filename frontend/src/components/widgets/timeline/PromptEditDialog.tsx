import { useRef, useEffect, useCallback, useState } from 'react'
import type { PromptSegment, Segment, TimeDisplayFormat } from '@/types/timeline'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  type CarouselApi,
} from '@/components/ui/carousel'
import { useT } from '@/lib/i18n'
import { uuid } from '@/lib/uuid'
import { cn } from '@/lib/utils'

// Height shared by both tab content areas
const CONTENT_H = 'h-[300px]'

export interface PromptEditDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  segments: PromptSegment[]
  totalFrames: number
  frameRate: number
  displayFormat: TimeDisplayFormat
  /** If set, the dialog opens to the Individual tab with this segment highlighted. */
  focusedSegmentId: string | null
  trackColor: string
  onSegmentsChange: (segments: Segment[]) => void
}

// ─── helpers ────────────────────────────────────────────────────────────────

function escHtml(str: string): string {
  return str
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('\n', '<br>')
}

function buildCombinedHtml(rawParts: string[]): string {
  const sep =
    '<span style="color:var(--highlight);padding:0 4px;font-weight:700" data-pipe="1">|</span>'
  return rawParts.map(escHtml).join(sep)
}

function getCursorOffset(el: HTMLElement): number {
  const sel = globalThis.getSelection()
  if (!sel || sel.rangeCount === 0) return 0
  const range = sel.getRangeAt(0)
  const pre = range.cloneRange()
  pre.selectNodeContents(el)
  pre.setEnd(range.endContainer, range.endOffset)
  return pre.toString().length
}

function setCursorOffset(el: HTMLElement, offset: number) {
  const sel = globalThis.getSelection()
  if (!sel) return
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT)
  let remaining = offset
  let node: Text | null
  while ((node = walker.nextNode() as Text | null)) {
    if (remaining <= node.length) {
      const r = document.createRange()
      r.setStart(node, remaining)
      r.collapse(true)
      sel.removeAllRanges()
      sel.addRange(r)
      return
    }
    remaining -= node.length
  }
  const r = document.createRange()
  r.selectNodeContents(el)
  r.collapse(false)
  sel.removeAllRanges()
  sel.addRange(r)
}

function applyTextsToSegments(
  parts: string[],
  segments: PromptSegment[],
  totalFrames: number,
  color: string,
): Segment[] {
  if (parts.length === segments.length) {
    return segments.map((s, i) => ({ ...s, content: { ...s.content, text: parts[i] } }))
  }
  const count = Math.max(1, parts.length)
  const perSeg = Math.floor((totalFrames - 1) / count)
  return parts.map((text, i) => ({
    id: segments[i]?.id ?? uuid(),
    start_frame: i * perSeg,
    end_frame: i < count - 1 ? (i + 1) * perSeg - 1 : totalFrames - 1,
    content: { text },
    color: segments[i]?.color ?? color,
  }))
}

// ─── Combined editor ─────────────────────────────────────────────────────────

interface CombinedEditorProps {
  segments: PromptSegment[]
  totalFrames: number
  trackColor: string
  onSegmentsChange: (segs: Segment[]) => void
}

function CombinedEditor({
  segments,
  totalFrames,
  trackColor,
  onSegmentsChange,
}: Readonly<CombinedEditorProps>) {
  const t = useT()
  const ref = useRef<HTMLDivElement>(null)
  const composing = useRef(false)
  const isFocused = useRef(false)
  const segmentsRef = useRef(segments)
  segmentsRef.current = segments

  useEffect(() => {
    if (ref.current) {
      ref.current.innerHTML = buildCombinedHtml(segments.map((s) => s.content.text))
      const r = document.createRange()
      r.selectNodeContents(ref.current)
      r.collapse(false)
      const sel = globalThis.getSelection()
      if (sel) {
        sel.removeAllRanges()
        sel.addRange(r)
      }
      ref.current.focus()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ComfyUI's keybindHandler is registered on `window` in bubble phase.
  // `document` bubble fires BEFORE `window` bubble — so our listener here
  // is guaranteed to run first and can stop ComfyUI from receiving the event.
  useEffect(() => {
    function interceptShortcut(e: KeyboardEvent) {
      if (!isFocused.current) return
      if (!(e.ctrlKey || e.metaKey)) return
      const k = e.key.toLowerCase()
      if (k === 'c' || k === 'x' || k === 'v' || k === 'a') {
        e.stopImmediatePropagation()
      }
    }
    document.addEventListener('keydown', interceptShortcut)
    return () => document.removeEventListener('keydown', interceptShortcut)
  }, [])

  const handleInput = useCallback(() => {
    if (!ref.current || composing.current) return
    const el = ref.current
    const offset = getCursorOffset(el)
    const raw = el.textContent ?? ''
    const rawParts = raw.split('|')
    el.innerHTML = buildCombinedHtml(rawParts)
    setCursorOffset(el, offset)
    const validParts = rawParts
      .map((p) => p.replaceAll('<br>', '\n').trim())
      .filter(Boolean)
    if (validParts.length > 0) {
      onSegmentsChange(
        applyTextsToSegments(validParts, segmentsRef.current, totalFrames, trackColor),
      )
    }
  }, [totalFrames, trackColor, onSegmentsChange])

  return (
    <div className={cn('flex flex-col gap-2', CONTENT_H)}>
      <p className="shrink-0 text-xs text-muted-foreground">
        {t('promptTrack.combinedHint')}
      </p>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        spellCheck={false}
        className="flex-1 min-h-0 overflow-y-auto p-3 rounded-md border border-input bg-background text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring whitespace-pre-wrap wrap-break-word"
        onInput={handleInput}
        onFocus={() => {
          isFocused.current = true
          // Deselect ComfyUI nodes so that even if the keybinding fires,
          // canvas.selectedItems.size === 0 and nothing gets copied.
          try {
            ;(globalThis as any).comfyAPI?.app?.app?.canvas?.deselectAll?.()
          } catch { /* ignore */ }
        }}
        onBlur={() => { isFocused.current = false }}
        onCompositionStart={() => {
          composing.current = true
        }}
        onCompositionEnd={() => {
          composing.current = false
          handleInput()
        }}
      />
    </div>
  )
}

// ─── Individual editor (index pills + carousel) ──────────────────────────────

interface IndividualEditorProps {
  segments: PromptSegment[]
  frameRate: number
  displayFormat: TimeDisplayFormat
  initialIndex: number
  onSegmentsChange: (segs: Segment[]) => void
}

function IndividualEditor({
  segments,
  frameRate,
  displayFormat,
  initialIndex,
  onSegmentsChange,
}: Readonly<IndividualEditorProps>) {
  const t = useT()
  const [carouselApi, setCarouselApi] = useState<CarouselApi>()
  const [activeIndex, setActiveIndex] = useState(Math.max(0, initialIndex))

  // Jump to initial index once api is ready.
  useEffect(() => {
    if (carouselApi) {
      carouselApi.scrollTo(activeIndex, true)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carouselApi])

  // Sync activeIndex when carousel changes (keyboard arrows etc.)
  useEffect(() => {
    if (!carouselApi) return
    const onSelect = () => setActiveIndex(carouselApi.selectedScrollSnap())
    carouselApi.on('select', onSelect)
    return () => {
      carouselApi.off('select', onSelect)
    }
  }, [carouselApi])

  function handlePillClick(index: number) {
    setActiveIndex(index)
    carouselApi?.scrollTo(index)
  }

  function handleTextChange(id: string, text: string) {
    onSegmentsChange(
      segments.map((s) => (s.id === id ? { ...s, content: { ...s.content, text } } : s)),
    )
  }

  return (
    <div className={cn('flex flex-col gap-2', CONTENT_H)}>
      {/* Index pill strip */}
      <div className="shrink-0 flex gap-1.5 overflow-x-auto pb-0.5 no-scrollbar">
        {segments.map((seg, i) => (
          <button
            key={seg.id}
            type="button"
            onClick={() => handlePillClick(i)}
            className={cn(
              'shrink-0 h-6 min-w-6 px-1.5 rounded text-xs font-semibold transition-colors',
              i === activeIndex
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            )}
          >
            {i + 1}
          </button>
        ))}
      </div>

      {/* Carousel — fills remaining height, no drag */}
      <Carousel
        setApi={setCarouselApi}
        opts={{ loop: false, watchDrag: false }}
        className="flex-1 min-h-0 [&>div]:h-full"
      >
        <CarouselContent className="h-full">
          {segments.map((seg, i) => {
            const frames = seg.end_frame - seg.start_frame + 1
            const duration =
              displayFormat === 'seconds'
                ? `${(frames / frameRate).toFixed(1)}s`
                : `${frames}f`

            return (
              <CarouselItem key={seg.id} className="h-full">
                <div className="flex flex-col h-full gap-1.5 pl-1">
                  <div className="shrink-0 flex items-center justify-between">
                    <p
                      className={cn(
                        'text-xs font-semibold',
                        i === activeIndex ? 'text-primary' : 'text-foreground',
                      )}
                    >
                      {t('promptTrack.segmentLabel', { n: i + 1 })}
                    </p>
                    <span className="text-[10px] text-muted-foreground">{duration}</span>
                  </div>
                  <Textarea
                    autoFocus={i === initialIndex}
                    className="flex-1 min-h-0 h-full resize-none text-sm"
                    rows={10}
                    placeholder={t('promptTrack.promptPlaceholder')}
                    value={seg.content.text}
                    onChange={(e) => handleTextChange(seg.id, e.target.value)}
                  />
                </div>
              </CarouselItem>
            )
          })}
        </CarouselContent>
      </Carousel>
    </div>
  )
}

// ─── Dialog ──────────────────────────────────────────────────────────────────

export function PromptEditDialog({
  open,
  onOpenChange,
  segments,
  totalFrames,
  frameRate,
  displayFormat,
  focusedSegmentId,
  trackColor,
  onSegmentsChange,
}: Readonly<PromptEditDialogProps>) {
  const t = useT()
  const [activeTab, setActiveTab] = useState<'combined' | 'individual'>(
    focusedSegmentId ? 'individual' : 'combined',
  )

  useEffect(() => {
    if (open) {
      setActiveTab(focusedSegmentId ? 'individual' : 'combined')
    }
  }, [open, focusedSegmentId])

  const focusedIndex = focusedSegmentId
    ? Math.max(0, segments.findIndex((s) => s.id === focusedSegmentId))
    : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold">
            {t('promptTrack.editDialogTitle')}
          </DialogTitle>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as 'combined' | 'individual')}
          className="space-y-3"
        >
          <TabsList className="w-full">
            <TabsTrigger value="combined" className="flex-1 text-xs">
              {t('promptTrack.tabCombined')}
            </TabsTrigger>
            <TabsTrigger value="individual" className="flex-1 text-xs">
              {t('promptTrack.tabIndividual')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="combined" className="mt-0">
            <CombinedEditor
              key={`combined-${open}-${activeTab === 'combined'}`}
              segments={segments}
              totalFrames={totalFrames}
              trackColor={trackColor}
              onSegmentsChange={onSegmentsChange}
            />
          </TabsContent>

          <TabsContent value="individual" className="mt-0">
            <IndividualEditor
              key={`individual-${open}-${activeTab === 'individual'}-${segments.length}`}
              segments={segments}
              frameRate={frameRate}
              displayFormat={displayFormat}
              initialIndex={focusedIndex}
              onSegmentsChange={onSegmentsChange}
            />
          </TabsContent>
        </Tabs>
        <p className="shrink-0 text-xs text-muted-foreground">
         {t('promptTrack.segmentCount', { n: segments.length })}
        </p>
      </DialogContent>
    </Dialog>
  )
}
