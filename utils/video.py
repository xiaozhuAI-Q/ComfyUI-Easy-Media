from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import torch

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MergeSpec:
    width: int
    height: int
    fps: Fraction
    has_audio: bool
    sample_rate: int | None
    channels: int | None


def normalize_video_images(
    images: torch.Tensor, divisible_by: int = 2
) -> tuple[torch.Tensor, bool]:
    """Crop H/W dimensions to be divisible by `divisible_by` for video encoding.

    Returns (tensor, changed) where changed is True if the tensor was cropped.
    """
    _batch, height, width, _channels = images.shape
    target_width = width - (width % divisible_by)
    target_height = height - (height % divisible_by)

    if target_width == width and target_height == height:
        return images, False

    cropped = images[:, :target_height, :target_width, :]
    return cropped.contiguous(), True


def extract_merge_spec(video: Any) -> MergeSpec:
    """Extract a MergeSpec from a VideoInput object for compatibility checks."""
    components = video.get_components()
    fps: Fraction = components.frame_rate
    width, height = video.get_dimensions()

    audio = components.audio
    if audio is None:
        has_audio = False
        sample_rate = None
        channels = None
    else:
        has_audio = True
        if isinstance(audio, dict):
            sample_rate = int(audio.get("sample_rate") or 0)
            waveform = audio.get("waveform")
            channels = int(waveform.shape[1]) if waveform is not None else None
        else:
            # Treat unknown audio types as present with unknown params
            sample_rate = None
            channels = None

    return MergeSpec(
        width=width,
        height=height,
        fps=fps,
        has_audio=has_audio,
        sample_rate=sample_rate,
        channels=channels,
    )


def validate_merge_compatibility(specs: list[MergeSpec]) -> None:
    """Raise ValueError if the given specs are not all merge-compatible."""
    if not specs:
        raise ValueError("At least one video is required")

    baseline = specs[0]
    labels = ("width", "height", "fps", "has_audio", "sample_rate", "channels")
    for index, spec in enumerate(specs[1:], start=2):
        for label in labels:
            baseline_val = getattr(baseline, label)
            spec_val = getattr(spec, label)
            if baseline_val != spec_val:
                raise ValueError(
                    f"Video {index} is incompatible: '{label}' mismatch "
                    f"(expected {baseline_val!r}, got {spec_val!r})"
                )


def ffmpeg_concat(
    input_paths: list[str],
    output_path: str,
    progress_callback: "callable[[str], None] | None" = None,
) -> bool:
    """Concatenate video files using FFmpeg concat demuxer.

    Tries stream copy first (no re-encoding — extremely fast).
    Falls back to libx264/aac re-encoding if stream copy fails.

    Returns True on success, False if FFmpeg is not installed (caller should
    fall back to the tensor-based merge path).

    Raises RuntimeError if FFmpeg is available but the concat fails.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    # Build the concat list file
    list_fd, list_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(list_fd, "w", encoding="utf-8") as f:
            for p in input_paths:
                # FFmpeg concat-list escaping: backslash-escape single quotes
                escaped = p.replace("\\", "\\\\").replace("'", "\\'")
                f.write(f"file '{escaped}'\n")

        base_cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path]

        # --- attempt 1: stream copy (fastest) ---
        if progress_callback:
            progress_callback("FFmpeg concat (stream copy)…")
        result = subprocess.run(
            base_cmd + ["-c", "copy", output_path],
            capture_output=True,
        )

        if result.returncode == 0:
            return True

        logger.warning(
            "[ffmpeg_concat] stream copy failed (rc=%d), retrying with re-encode. "
            "stderr: %s",
            result.returncode,
            result.stderr.decode(errors="replace")[-400:],
        )

        # --- attempt 2: re-encode (compatible with mixed codecs) ---
        if progress_callback:
            progress_callback("FFmpeg concat (re-encoding)…")
        result2 = subprocess.run(
            base_cmd + [
                "-c:v", "libx264", "-preset", "fast",
                "-c:a", "aac",
                output_path,
            ],
            capture_output=True,
        )
        if result2.returncode != 0:
            raise RuntimeError(
                f"FFmpeg concat failed:\n{result2.stderr.decode(errors='replace')[-600:]}"
            )
        return True
    finally:
        try:
            os.unlink(list_path)
        except OSError:
            pass


def ffmpeg_replace_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> bool:
    """Replace (or add) the audio track of a video file using FFmpeg stream copy.

    The video stream is always stream-copied (no re-encode). The audio is
    encoded to AAC. The output is trimmed to the shortest stream.

    Returns True on success, False if FFmpeg is not installed.
    Raises RuntimeError if FFmpeg is available but the operation fails.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg replace-audio failed:\n{result.stderr.decode(errors='replace')[-600:]}"
        )
    return True
