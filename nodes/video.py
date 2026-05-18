from __future__ import annotations

import io as _io
import logging
import os
import tempfile
import urllib.request
from fractions import Fraction
from typing import Optional

import folder_paths
import torch
from comfy_api.latest import Input, InputImpl, Types, io, ui
from comfy.utils import ProgressBar
from server import PromptServer

from ..utils.video import extract_merge_spec, ffmpeg_concat, normalize_video_images, validate_merge_compatibility

logger = logging.getLogger(__name__)

CATEGORY = "EasyUse/Media"

_OUTPUT_MODE_OPTIONS = [
    io.DynamicCombo.Option(
        "save",
        [
            io.String.Input("filename_prefix", default="ComfyUI"),
            io.Boolean.Input(
                "save_metadata",
                default=False,
                tooltip="Write ComfyUI prompt/workflow metadata into the saved file.",
            ),
        ],
    ),
    io.DynamicCombo.Option("preview_only", []),
]

_INPUT_MODE_OPTIONS = [
    io.DynamicCombo.Option(
        "images+audio",
        [
            io.Image.Input("images" ,optional=True),
            io.Float.Input("fps", default=24.0, min=1.0, max=120.0, step=1.0),
            io.Audio.Input("audio", optional=True),
        ],
    ),
    io.DynamicCombo.Option(
        "video",
        [
            io.Video.Input("video"),
        ],
    ),
]


class EasySaveVideo(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy saveVideo",
            display_name="Save Video",
            category=CATEGORY,
            description=(
                "Save images and optional audio to a video file. "
                "Returns the VIDEO for downstream use and the full written file path."
            ),
            inputs=[
                io.DynamicCombo.Input("input_mode", options=_INPUT_MODE_OPTIONS),
                io.DynamicCombo.Input("output_mode", options=_OUTPUT_MODE_OPTIONS),
            ],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo],
            is_output_node=True,
            outputs=[
                io.Video.Output(display_name="VIDEO"),
                io.String.Output(display_name="file_path"),
            ],
        )

    @classmethod
    def execute(
        cls,
        input_mode: dict,
        output_mode: dict,
    ) -> io.NodeOutput:
        input_mode_key: str = input_mode.get("input_mode", "images+audio")
        output_mode_key: str = output_mode.get("output_mode", "save")
        only_preview = output_mode_key == "preview_only"
        filename_prefix: str = output_mode.get("filename_prefix", "ComfyUI")
        save_metadata: bool = output_mode.get("save_metadata", False)

        if input_mode_key == "video":
            source_video = input_mode.get("video")
            if source_video is None:
                raise ValueError("A VIDEO input is required when input_mode is 'video'.")
        else:
            images = input_mode.get("images", None)
            if images is None:
                raise ValueError("An IMAGES input is required when input_mode is 'images+audio'.")
            fps: float = input_mode.get("fps", 24.0)
            audio = input_mode.get("audio", None)
            normalized, changed = normalize_video_images(images)
            if changed:
                logger.info(
                    "[EasySaveVideo] Image dimensions were cropped to even size for video encoding."
                )
            source_video = InputImpl.VideoFromComponents(
                Types.VideoComponents(
                    images=normalized,
                    audio=audio,
                    frame_rate=Fraction(fps),
                )
            )

        width, height = source_video.get_dimensions()

        if only_preview:
            output_dir = folder_paths.get_temp_directory()
            folder_type = io.FolderType.temp
        else:
            output_dir = folder_paths.get_output_directory()
            folder_type = io.FolderType.output

        full_output_folder, filename, counter, subfolder, filename_prefix = (
            folder_paths.get_save_image_path(filename_prefix, output_dir, width, height)
        )

        ext = Types.VideoContainer.get_extension(Types.VideoContainer.AUTO)
        file = f"{filename}_{counter:05}_.{ext}"
        full_path = os.path.join(full_output_folder, file)
        prefix = "temp" if only_preview else "output"
        relative_path = f"{prefix}/{os.path.relpath(full_path, output_dir)}"

        metadata: dict | None = None
        if save_metadata:
            metadata = {}
            if cls.hidden.extra_pnginfo is not None:
                metadata.update(cls.hidden.extra_pnginfo)
            if cls.hidden.prompt is not None:
                metadata["prompt"] = cls.hidden.prompt
            if not metadata:
                metadata = None

        source_video.save_to(
            full_path,
            format=Types.VideoContainer.AUTO,
            codec=Types.VideoCodec.AUTO,
            metadata=metadata,
        )

        return io.NodeOutput(
            source_video,
            relative_path,
            ui=ui.PreviewVideo([ui.SavedResult(file, subfolder, folder_type)]),
        )


class EasyMergeVideos(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy mergeVideos",
            display_name="Merge Videos",
            category=CATEGORY,
            description=(
                "Concatenate multiple compatible VIDEO clips in order. "
                "All clips must share the same fps, dimensions, and audio configuration."
            ),
            inputs=[
                io.Video.Input("video_1"),
                io.Video.Input("video_2"),
            ],
            outputs=[
                io.Video.Output(display_name="VIDEO"),
            ],
        )

    @classmethod
    def execute(
        cls,
        video_1: Input.Video,
        video_2: Input.Video,
    ) -> io.NodeOutput:
        videos = [video_1, video_2]

        specs = [extract_merge_spec(v) for v in videos]
        validate_merge_compatibility(specs)

        all_images: list[torch.Tensor] = []
        all_waveforms: list[torch.Tensor] = []
        sample_rate: int | None = None
        has_audio = specs[0].has_audio

        for video in videos:
            components = video.get_components()
            all_images.append(components.images)

            if has_audio and components.audio is not None:
                audio = components.audio
                if isinstance(audio, dict):
                    waveform = audio.get("waveform")
                    if waveform is not None:
                        all_waveforms.append(waveform)
                    if sample_rate is None:
                        sample_rate = audio.get("sample_rate")

        merged_images = torch.cat(all_images, dim=0)

        merged_audio: dict | None = None
        if has_audio and all_waveforms:
            merged_waveform = torch.cat(all_waveforms, dim=2)
            merged_audio = {"waveform": merged_waveform, "sample_rate": sample_rate}

        merged_video = InputImpl.VideoFromComponents(
            Types.VideoComponents(
                images=merged_images,
                audio=merged_audio,
                frame_rate=specs[0].fps,
            )
        )

        return io.NodeOutput(merged_video)


def _resolve_video_path(raw: str) -> str | _io.BytesIO:
    """Resolve a raw path string to a local file path or BytesIO buffer.

    Supported formats:
    - HTTP/HTTPS URL
    - ``temp/<filename>`` — file in ComfyUI temp directory
    - ``output/<filename>`` — file in ComfyUI output directory
    - Absolute file path
    - ComfyUI annotated path (filename[subfolder][type]) via folder_paths
    - Bare filename resolved against output then temp directories
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("Empty path string")

    # URL
    if raw.startswith(("http://", "https://")):
        with urllib.request.urlopen(raw, timeout=30) as resp:  # noqa: S310
            return _io.BytesIO(resp.read())

    # ComfyUI-style prefixed paths: temp/<file> or output/<file>
    _PREFIXED = {
        "temp": folder_paths.get_temp_directory,
        "output": folder_paths.get_output_directory,
    }
    for prefix, get_dir in _PREFIXED.items():
        if raw.startswith(prefix + "/") or raw.startswith(prefix + os.sep):
            rel = raw[len(prefix) + 1:]
            candidate = os.path.join(get_dir(), rel)
            if os.path.isfile(candidate):
                return candidate
            raise FileNotFoundError(f"File not found in {prefix!r} directory: {rel!r}")

    # Absolute path
    if os.path.isabs(raw) and os.path.isfile(raw):
        return raw

    # ComfyUI annotated path
    try:
        annotated = folder_paths.get_annotated_filepath(raw)
        if os.path.isfile(annotated):
            return annotated
    except Exception:
        pass

    # Bare filename: check output then temp directories
    for base_dir in (folder_paths.get_output_directory(), folder_paths.get_temp_directory()):
        candidate = os.path.join(base_dir, raw)
        if os.path.isfile(candidate):
            return candidate

    raise FileNotFoundError(f"Cannot resolve video path: {raw!r}")


class EasyMergeVideosFromPaths(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="easy mergeVideosFromPaths",
            display_name="Merge Videos From Paths",
            category=CATEGORY,
            description=(
                "Load and concatenate videos from a list of file paths or URLs. "
                "Supports ComfyUI temp/output paths, absolute local paths, and HTTP(S) URLs. "
                "All clips must share the same fps, dimensions, and audio configuration."
            ),
            inputs=[
                io.String.Input(
                    "paths",
                    force_input=True,
                    default="",
                    tooltip=(
                        "One path per line (or comma-separated). "
                        "Accepts ComfyUI output/temp filenames, absolute paths, or URLs."
                    ),
                ),
            ],
            hidden=[io.Hidden.unique_id],
            outputs=[
                io.Video.Output(display_name="VIDEO"),
            ],
        )

    @classmethod
    def execute(cls, paths: str) -> io.NodeOutput:
        # Parse path list: split by newlines and commas, strip blanks
        raw_paths: list[str] = []
        lines = paths if isinstance(paths, list) else paths.replace(",", "\n").splitlines()
        for line in lines:
            line = line.strip()
            if line:
                raw_paths.append(line)

        if len(raw_paths) < 2:
            raise ValueError("At least 2 video paths are required for merging.")

        node_id: str = str(cls.hidden.unique_id or "")
        total = len(raw_paths)
        pbar = ProgressBar(total + 2)

        def _progress(step: int, msg: str) -> None:
            pbar.update_absolute(step, total + 2)
            if node_id:
                PromptServer.instance.send_progress_text(msg, node_id)

        _progress(0, f"Resolving {total} paths…")
        resolved: list[str] = []
        for i, raw in enumerate(raw_paths, start=1):
            _progress(i - 1, f"Resolving {i}/{total}: {raw}")
            try:
                source = _resolve_video_path(raw)
            except (FileNotFoundError, ValueError) as exc:
                raise ValueError(f"Clip {i}: {exc}") from exc
            resolved.append(source)

        # --- Fast path: FFmpeg concat (stream copy preferred) ---
        ext = os.path.splitext(resolved[0])[1] or ".mp4"
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=folder_paths.get_temp_directory())
        os.close(tmp_fd)
        try:
            _progress(total, f"Merging {total} clips via FFmpeg…")
            success = ffmpeg_concat(
                resolved,
                tmp_path,
                progress_callback=lambda msg: _progress(total, msg),
            )
            if success:
                merged_video = InputImpl.VideoFromFile(tmp_path)
                _progress(total + 2, f"Done — merged {total} clips")
                return io.NodeOutput(merged_video)
        except RuntimeError as exc:
            logger.warning("[EasyMergeVideosFromPaths] FFmpeg failed: %s — falling back to tensor merge.", exc)

        # --- Slow fallback: tensor-based merge ---
        _progress(total, "Loading clips for tensor merge…")
        videos = []
        for i, source in enumerate(resolved, start=1):
            _progress(total, f"Loading clip {i}/{total}")
            videos.append(InputImpl.VideoFromFile(source))

        specs = [extract_merge_spec(v) for v in videos]
        validate_merge_compatibility(specs)

        _progress(total + 1, "Merging frames…")
        all_images: list[torch.Tensor] = []
        all_waveforms: list[torch.Tensor] = []
        sample_rate: int | None = None
        has_audio = specs[0].has_audio

        for video in videos:
            components = video.get_components()
            all_images.append(components.images)
            if has_audio and components.audio is not None:
                audio = components.audio
                if isinstance(audio, dict):
                    waveform = audio.get("waveform")
                    if waveform is not None:
                        all_waveforms.append(waveform)
                    if sample_rate is None:
                        sample_rate = audio.get("sample_rate")

        merged_images = torch.cat(all_images, dim=0)
        merged_audio: dict | None = None
        if has_audio and all_waveforms:
            merged_audio = {
                "waveform": torch.cat(all_waveforms, dim=2),
                "sample_rate": sample_rate,
            }

        merged_video = InputImpl.VideoFromComponents(
            Types.VideoComponents(
                images=merged_images,
                audio=merged_audio,
                frame_rate=specs[0].fps,
            )
        )
        _progress(total + 2, f"Done — merged {total} clips")
        return io.NodeOutput(merged_video)

