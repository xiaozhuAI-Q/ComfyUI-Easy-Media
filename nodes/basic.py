import json

import torch

from comfy_api.latest import io
from ..utils import (
    frames_to_seconds,
    load_audio_waveform,
    load_image_tensor,
    resize_image,
    silence,
    trim_audio,
) 


# ---------------------------------------------------------------------------
# Resolution combo setup
# ---------------------------------------------------------------------------

BASE_RESOLUTIONS = [
    ["width", "height", "auto"],
    ["width", "height", "shortest"],
    ["width", "height", "longest"],
    ["width", "height", "custom"],
    [480, 832, "9:16"],
    [544, 960, "9:16"],
    [576, 1024, "9:16"],
    [720, 1280, "9:16"],
    [768, 1024, "3:4"],
    [816, 1456, "9:16"],
    [817, 1920, "1:2.35"],
    [864, 1536, "9:16"],
    [1080, 1920, "9:16"],
    [1920, 1080, "16:9"],
    [1920, 817, "2.35:1"],
    [1536, 864, "16:9"],
    [1456, 816, "16:9"],
    [1280, 720, "16:9"],
    [1024, 768, "4:3"],
    [1024, 576, "16:9"],
    [960, 544, "16:9"],
    [832, 480, "16:9"],
]
VIDEO_FORMATS = {
    'None': {},
    'AnimateDiff': {'target_rate': 8, 'dim': (8,0,512,512)},
    'Mochi': {'target_rate': 24, 'dim': (16,0,848,480), 'frames':(6,1)},
    'LTXV': {'target_rate': 24, 'dim': (32,0,768,512), 'frames':(8,1)},
    'Hunyuan': {'target_rate': 24, 'dim': (16,0,848,480), 'frames':(4,1)},
    'Cosmos': {'target_rate': 24, 'dim': (16,0,1280,704), 'frames':(8,1)},
    'Wan': {'target_rate': 16, 'dim': (8,0,832,480), 'frames':(4,1)},
}

resolution_strings = [f"{w} x {h} ({r})" for w, h, r in BASE_RESOLUTIONS]
resize_method_input = io.Combo.Input(
    "resize_method",
    default="stretch",
    options=["stretch", "resize", "pad", "crop"],
)
resolution_combo_options = [
    io.DynamicCombo.Option(
        s,
        [
            io.Int.Input("width", default=544, min=64, max=8096, step=8),
            io.Int.Input("height", default=960, min=64, max=8096, step=8),
            resize_method_input,
        ]
        if "custom" in s
        else (
            [
                io.Int.Input("resize_to_pixel", default=960, min=64, max=8096, step=8),
                resize_method_input
            ]
            if "shortest" in s or "longest" in s
            else [resize_method_input]
        ),
    )
    for s in resolution_strings
]

# ---------------------------------------------------------------------------
# Custom types
# ---------------------------------------------------------------------------

TYPE_TIMELINE = io.Custom(io_type="TIMELINE")
TYPE_TIMELINE_INFO = io.Custom(io_type="TIMELINE_INFO")
CATEGORY = "EasyUse/Media"
PROMPT_FORMAT_OPTIONS = ["default", "promptRelay"]

# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class TimelineEditor(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy timelineEditor",
            display_name="Timeline Editor",
            category=CATEGORY,
            description="Load a timeline of media items (prompt, image, audio tracks) and outputs structured data.",
            inputs=[
                io.DynamicCombo.Input(
                    "resolution",
                    options=resolution_combo_options,
                    tooltip="Select a resolution or choose 'Custom' to specify your own width and height.",
                ),
                io.Combo.Input("format", options=list(VIDEO_FORMATS.keys()), default="LTXV",  tooltip="Choose a video format to automatically set resolution and frame rate."),
                TYPE_TIMELINE.Input(
                    "timeline_data",
                ),
            ],
            outputs=[
                TYPE_TIMELINE_INFO.Output("TIMELINE_INFO"),
                io.Image.Output("IMAGES"),
                io.Audio.Output("AUDIO"),
            ],
        )

    @classmethod
    def execute(cls, resolution, format, timeline_data, **kwargs):
        # ---- Parse timeline_data ----
        if isinstance(timeline_data, str):
            try:
                data = json.loads(timeline_data)
            except (json.JSONDecodeError, ValueError):
                data = {}
        else:
            data = dict(timeline_data) if timeline_data else {}

        tracks = data.get("tracks", [])
        total_length: int = int(data.get("total_length", 121))
        frame_rate: int = int(data.get("frame_rate", 24))

        # =========================================================
        # Collect maintain (main) track segments
        # =========================================================
        maintain_segs: list[dict] = []
        for track in tracks:
            if track.get("type") != "maintain":
                continue
            for seg in sorted(track.get("segments", []), key=lambda s: s.get("start_frame", 0)):
                content = seg.get("content", {})
                maintain_segs.append({
                    "start_frame": int(seg.get("start_frame", 0)),
                    "end_frame": int(seg.get("end_frame", 0)),
                    "text": content.get("text", ""),
                    "images": content.get("images", []),  # list of ImageItem dicts
                    "type": content.get("type", "flf"),
                })

        # Flat list of all image items from maintain segments, in order
        all_image_items: list[dict] = []
        for seg in maintain_segs:
            all_image_items.extend(seg["images"])

        # =========================================================
        # Resolve target dimensions
        # =========================================================
        _resolution: str = resolution.get("resolution", "")
        resize_method: str = resolution.get("resize_method", "stretch")
        resize_to_pixel: int | None = resolution.get("resize_to_pixel", None)
        width_custom: int | None = resolution.get("width", None)
        height_custom: int | None = resolution.get("height", None)

        # Detect mode from resolution string
        if "auto" in _resolution:
            mode = "auto"
        elif "longest" in _resolution:
            mode = "longest"
        elif "shortest" in _resolution:
            mode = "shortest"
        elif "custom" in _resolution:
            mode = "custom"
        else:
            mode = "preset"

        # Load first image once for dimension inference (auto / longest / shortest)
        first_image_tensor: torch.Tensor | None = None
        if mode in ("auto", "longest", "shortest") and all_image_items:
            first = all_image_items[0]
            first_image_tensor = load_image_tensor(
                first.get("source_type", "input"),
                first.get("file_path"),
                first.get("local_path"),
                first.get("url"),
            )

        target_w: int
        target_h: int

        if mode == "preset":
            target_w, target_h = 544, 960
            for entry in BASE_RESOLUTIONS:
                w, h = entry[0], entry[1]
                if isinstance(w, int) and f"{w} x {h}" in _resolution:
                    target_w, target_h = int(w), int(h)
                    break
        elif mode == "auto":
            if first_image_tensor is not None:
                target_h = first_image_tensor.shape[1]
                target_w = first_image_tensor.shape[2]
            else:
                target_w, target_h = 544, 960
        elif mode in ("longest", "shortest"):
            if first_image_tensor is not None:
                img_h = first_image_tensor.shape[1]
                img_w = first_image_tensor.shape[2]
                pix = int(resize_to_pixel) if resize_to_pixel else 960
                aspect = img_w / img_h  # width / height
                if mode == "longest":
                    if img_w >= img_h:
                        target_w = pix
                        target_h = round(pix / aspect)
                    else:
                        target_h = pix
                        target_w = round(pix * aspect)
                else:  # shortest
                    if img_w <= img_h:
                        target_w = pix
                        target_h = round(pix / aspect)
                    else:
                        target_h = pix
                        target_w = round(pix * aspect)
            else:
                target_w, target_h = 544, 960
        else:  # custom
            target_w = int(width_custom) if width_custom else 544
            target_h = int(height_custom) if height_custom else 960

        # Apply format divisibility to finalise target dimensions
        fmt_info = VIDEO_FORMATS.get(format, {})
        div: int = int(fmt_info.get("dim", [1])[0]) if fmt_info else 1
        if div > 1:
            target_w = max(div, ((target_w + div - 1) // div) * div)
            target_h = max(div, ((target_h + div - 1) // div) * div)

        # =========================================================
        # Load and resize images from maintain segments
        # =========================================================
        image_tensors: list[torch.Tensor] = []
        for idx, item in enumerate(all_image_items):
            # Reuse already-loaded tensor for the first item (avoid double load)
            if idx == 0 and first_image_tensor is not None:
                t = first_image_tensor
            else:
                t = load_image_tensor(
                    item.get("source_type", "input"),
                    item.get("file_path"),
                    item.get("local_path"),
                    item.get("url"),
                )
            if t is None:
                continue
            t = resize_image(t, target_w, target_h, resize_method)
            image_tensors.append(t)

        if image_tensors:
            images_out = torch.cat(image_tensors, dim=0)
        else:
            images_out = torch.zeros(1, target_h, target_w, 3)

        # =========================================================
        # Audio track processing
        # =========================================================
        default_sr = 44100
        merged_waveform: torch.Tensor | None = None

        for track in tracks:
            if track.get("type") != "audio":
                continue
            track_parts: list[torch.Tensor] = []
            prev_end_sec = 0.0
            channels = 2

            for seg in sorted(track.get("segments", []), key=lambda s: s.get("start_frame", 0)):
                start = int(seg.get("start_frame", 0))
                end = min(int(seg.get("end_frame", 0)), total_length - 1)
                start_sec = max(0.0, frames_to_seconds(start, frame_rate))
                end_sec = frames_to_seconds(end, frame_rate)
                duration_sec = max(0.0, end_sec - start_sec)

                # Trim offset: how far into the source audio this segment starts
                origin_start = int(seg.get("origin_start_frame", start))
                # Use plain frame-count division (not frames_to_seconds which applies a -1 offset for indices)
                trim_offset_sec = max(0.0, (start - origin_start) / frame_rate) if start > origin_start else 0.0

                content = seg.get("content", {})
                waveform = load_audio_waveform(
                    content.get("source_type", "input"),
                    content.get("file_path"),
                    content.get("local_path"),
                    content.get("url"),
                    default_sr,
                )

                # Determine channel count from loaded audio before adding gap silence,
                # so the silence tensor has matching channels and torch.cat won't fail.
                if waveform is not None:
                    channels = waveform.shape[1]

                # Silence gap before this segment (inserted after channel count is known)
                if start_sec > prev_end_sec + 1e-6:
                    track_parts.append(silence(default_sr, start_sec - prev_end_sec, channels))

                if waveform is not None:
                    wav = waveform[0]  # [C,T]
                    # Apply trim offset — skip samples from the start of the source
                    if trim_offset_sec > 0.0:
                        offset_samples = int(default_sr * trim_offset_sec)
                        wav = wav[:, offset_samples:]
                    target_samples = max(1, int(default_sr * duration_sec))
                    if wav.shape[-1] > target_samples:
                        wav = wav[:, :target_samples]
                    elif wav.shape[-1] < target_samples:
                        wav = torch.cat([wav, torch.zeros(channels, target_samples - wav.shape[-1])], dim=-1)
                    track_parts.append(wav.unsqueeze(0))
                else:
                    track_parts.append(silence(default_sr, duration_sec, channels))

                prev_end_sec = end_sec

            if track_parts:
                merged_waveform = torch.cat(track_parts, dim=-1)

        total_sec = (total_length - 1) / frame_rate
        channels = 2
        if merged_waveform is not None:
            channels = merged_waveform.shape[1]
            total_samples = max(1, int(default_sr * total_sec))
            wav = merged_waveform[0]
            if wav.shape[-1] > total_samples:
                wav = wav[:, :total_samples]
            elif wav.shape[-1] < total_samples:
                wav = torch.cat([wav, torch.zeros(channels, total_samples - wav.shape[-1])], dim=-1)
            merged_waveform = wav.unsqueeze(0)
        else:
            merged_waveform = silence(default_sr, total_sec, channels)

        audio_out = {"waveform": merged_waveform, "sample_rate": default_sr}

        # =========================================================
        # Build audio segment info from maintain segment boundaries
        # Segment n+1 start == segment n end; last segment end == total time
        # =========================================================
        audio_seg_info: list[dict] = []
        for i, seg in enumerate(maintain_segs):
            start_sec = seg["start_frame"] / frame_rate
            if i < len(maintain_segs) - 1:
                end_sec = maintain_segs[i + 1]["start_frame"] / frame_rate
            else:
                end_sec = seg["end_frame"] / frame_rate
            audio_seg_info.append({
                "start_sec": round(start_sec, 4),
                "end_sec": round(end_sec, 4),
                "duration": round(end_sec - start_sec, 4),
            })

        # =========================================================
        # Build per-segment info for timeline_info
        # =========================================================
        seg_infos: list[dict] = []
        for seg in maintain_segs:
            images_info: list[dict] = []
            for img in seg["images"]:
                entry: dict = {
                    "source_type": img.get("source_type", "input"),
                    "file_name": img.get("file_name", ""),
                }
                if img.get("start_frame") is not None:
                    entry["start_frame"] = img["start_frame"]
                if img.get("end_frame") is not None:
                    entry["end_frame"] = img["end_frame"]
                images_info.append(entry)

            seg_info: dict = {
                "start_frame": seg["start_frame"],
                "end_frame": seg["end_frame"],
                "prompt": seg["text"],
                "images": images_info,
            }
            if images_info:
                seg_info["type"] = seg["type"]
            seg_infos.append(seg_info)

        # =========================================================
        # timeline_info output
        # =========================================================
        timeline_info = {
            "total_length": total_length,
            "frame_rate": frame_rate,
            "width": target_w,
            "height": target_h,
            "segments": seg_infos,
            "audio": {
                "segments": audio_seg_info,
            },
        }

        return io.NodeOutput(timeline_info, images_out, audio_out)


class TimelineInfoOutput(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy timelineInfoOutput",
            display_name="Timeline Info Output",
            category=CATEGORY,
            description="Output timeline info including formatted prompt, dimensions, and image indexes.",
            inputs=[
                TYPE_TIMELINE_INFO.Input("timeline_info"),
                io.Combo.Input(
                    "prompt_format",
                    options=PROMPT_FORMAT_OPTIONS,
                    default="default",
                    tooltip="Choose prompt format. promptRelay formats prompts with frame ranges.",
                ),
            ],
            outputs=[
                io.String.Output("PROMPT"),
                io.Int.Output("WIDTH"),
                io.Int.Output("HEIGHT"),
                io.Int.Output("TOTAL_FRAMES"),
                io.Float.Output("FPS"),
                io.String.Output("IMAGE_INDEXES"),
            ],
        )

    @classmethod
    def execute(cls, timeline_info, prompt_format, **kwargs):
        if isinstance(timeline_info, str):
            try:
                info = json.loads(timeline_info)
            except (json.JSONDecodeError, ValueError):
                info = {}
        else:
            info = dict(timeline_info) if timeline_info else {}

        total_length: int = info.get("total_length", 121)
        frame_rate: int = info.get("frame_rate", 24)
        width: int = info.get("width", 544)
        height: int = info.get("height", 960)
        segments: list[dict] = info.get("segments", [])

        # Build image_indexes: comma-separated string of starting frames
        image_indexes: str = ",".join(str(int(seg.get("start_frame", 0))) for seg in segments if seg.get("images", []))

        def normalize_prompt(value: str | list | None) -> str:
            if value is None:
                return ""
            if isinstance(value, list):
                return "\n".join(v for v in value if isinstance(v, str))
            return str(value).strip()

        # Build prompt string
        if prompt_format == "promptRelay":
            prompt_parts: list[str] = []
            for seg in segments:
                seg_text = normalize_prompt(seg.get("prompt"))
                if seg_text:
                    start = int(seg.get("start_frame", 0))
                    end = int(seg.get("end_frame", 0))
                    prompt_parts.append(f"{seg_text} [{start}-{end}]")
            prompt_str = " | ".join(prompt_parts)
        else:
            prompt_str = [seg.get("prompt").strip() for seg in segments]

        return io.NodeOutput(
            prompt_str,
            width,
            height,
            total_length,
            float(frame_rate),
            image_indexes,
        )


TYPE_MAP = {"flf": 0, "fmlf": 1, "ref": 2}

class TimelineSegmentOutput(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy timelineSegmentOutput",
            display_name="Timeline Segment Output",
            category=CATEGORY,
            description="Output data for a specific segment from the timeline.",
            inputs=[
                TYPE_TIMELINE_INFO.Input("timeline_info"),
                io.Combo.Input(
                    "prompt_format",
                    options=PROMPT_FORMAT_OPTIONS,
                    default="default",
                    tooltip="Choose prompt format. promptRelay formats prompts with frame ranges.",
                ),
                io.Image.Input("images", optional=True),
                io.Audio.Input("audio", optional=True),
                io.Int.Input("segment_index", default=0, min=0),
            ],
            outputs=[
                io.String.Output("PROMPT"),
                io.Int.Output("TYPE"),
                io.Boolean.Output("NO_IMAGES"),
                io.String.Output("IMAGE_INDEXES"),
                io.Int.Output("LENGTH"),
                io.Image.Output("IMAGES"),
                io.Audio.Output("AUDIO"),
            ],
        )

    @classmethod
    def execute(cls, timeline_info, prompt_format, segment_index, images=None, audio=None, **kwargs):
        if isinstance(timeline_info, str):
            try:
                info = json.loads(timeline_info)
            except (json.JSONDecodeError, ValueError):
                info = {}
        else:
            info = dict(timeline_info) if timeline_info else {}

        segments: list[dict] = info.get("segments", [])
        height = info.get("height", 960)
        width = info.get("width", 544)

        # Clamp index to valid range
        segment_index = max(0, min(segment_index, len(segments) - 1))
        seg = segments[segment_index] if segments else {}
        seg_images = seg.get("images", [])
        start_frame = seg.get("start_frame", 0)
        end_frame = seg.get("end_frame", 0)
        no_images = len(seg_images) == 0

        raw_prompt = seg.get("prompt", "") or ""
        if prompt_format == "promptRelay" and raw_prompt.strip():
            parts = [p.strip() for p in raw_prompt.split("|") if p.strip()]
            prompt_parts: list[str] = []
            for i, p in enumerate(parts):
                if i < len(seg_images):
                    img = seg_images[i]
                    img_start = img.get("start_frame")
                    img_end = img.get("end_frame")
                    if img_start is not None and img_end is not None:
                        prompt_parts.append(f"{p} [{int(img_start)}-{int(img_end)}]")
            prompt = " | ".join(prompt_parts)
        else:
            prompt = raw_prompt
        seg_type_str = seg.get("type", "flf")
        seg_type = TYPE_MAP.get(seg_type_str, 0)

        audio_segments = info.get("audio", {}).get("segments", [])
        frame_rate = info.get("frame_rate", 30)

        # Calculate segment length (frame count)
        if seg_images:
            segment_length = end_frame - start_frame + 1
        elif segment_index < len(audio_segments):
            segment_length = int(audio_segments[segment_index].get("duration", 0.0) * frame_rate)
        else:
            segment_length = 0

        # Output images from segment (based on images array in segment)
        num_seg_images = len(seg_images)
        if images is not None and isinstance(images, torch.Tensor) and num_seg_images > 0:
            # Calculate offset: sum of images in all previous segments
            offset = sum(len(segments[i].get("images", [])) for i in range(segment_index))
            if offset + num_seg_images <= images.shape[0]:
                images_out = images[offset:offset + num_seg_images]
            else:
                images_out = images[offset:]
            images_indexes_str = ",".join(str(int(img.get("start_frame", 0))) for img in seg_images)
        else:
            images_out = torch.zeros(1, height, width, 3)
            images_indexes_str = ""

        # Output audio from segment (trimmed by segment index)
        if audio is not None and isinstance(audio, dict):
            waveform = audio.get("waveform")
            sample_rate = audio.get("sample_rate", 44100)
            if waveform is not None and isinstance(waveform, torch.Tensor):
                if segment_index < len(audio_segments):
                    seg_audio = audio_segments[segment_index]
                    audio_out = trim_audio(
                        {"waveform": waveform, "sample_rate": sample_rate},
                        seg_audio["start_sec"],
                        seg_audio["duration"],
                    )
                else:
                    audio_out = {"waveform": waveform, "sample_rate": sample_rate}
            else:
                audio_out = {"waveform": None, "sample_rate": sample_rate}
        else:
            audio_out = {"waveform": None, "sample_rate": 44100}

        return io.NodeOutput(
            prompt,
            seg_type,
            no_images,
            images_indexes_str,
            segment_length,
            images_out,
            audio_out,
        )


class TimelineSegmentCount(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy timelineSegmentCount",
            display_name="Timeline Segment Count",
            category=CATEGORY,
            description="Output the total number of segments in the timeline.",
            inputs=[
                TYPE_TIMELINE_INFO.Input("timeline_info"),
            ],
            outputs=[
                io.Int.Output("COUNT"),
            ],
        )

    @classmethod
    def execute(cls, timeline_info, **kwargs):
        if isinstance(timeline_info, str):
            try:
                info = json.loads(timeline_info)
            except (json.JSONDecodeError, ValueError):
                info = {}
        else:
            info = dict(timeline_info) if timeline_info else {}

        count: int = len(info.get("segments", []))
        return io.NodeOutput(count)

class ImageIndexesToIntList(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy imageIndexesToIntList",
            display_name="Image Indexes To Int List",
            category=CATEGORY,
            description="Convert comma-separated image index string to integer list.",
            inputs=[
                io.String.Input("image_indexes"),
            ],
            outputs=[
                io.Int.Output("INDEXES", is_output_list=True),
            ],
        )

    @classmethod
    def execute(cls, image_indexes, **kwargs):
        if not image_indexes:
            indexes: list[int] = []
        else:
            try:
                indexes = [int(x.strip()) for x in str(image_indexes).split(",") if x.strip()]
            except ValueError:
                raise ValueError(f"Invalid image_indexes input: {image_indexes}. Must be a comma-separated string of integers.")

        return io.NodeOutput(indexes)

