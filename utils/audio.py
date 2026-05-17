import os
import urllib.request
from pathlib import Path

import torch

import folder_paths


def frames_to_seconds(frames: int, frame_rate: int) -> float:
    return (frames - 1) / frame_rate


def load_audio_waveform(source_type, file_path, local_path, url, target_sr: int):
    """Load audio → [1,C,T] waveform resampled to target_sr, or None."""
    try:
        import torchaudio  # type: ignore[import]
    except ImportError:
        return None

    audio_path = None
    if source_type == "url" and url:
        try:
            import tempfile
            with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
                suffix = Path(url).suffix or ".wav"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(resp.read())
                    audio_path = tmp.name
        except Exception:
            return None
    elif source_type == "input" and file_path:
        audio_path = folder_paths.get_annotated_filepath(file_path)
    elif source_type == "local" and local_path:
        audio_path = local_path

    if not audio_path or not os.path.isfile(audio_path):
        return None
    try:
        waveform, sr = torchaudio.load(audio_path)
        if sr != target_sr:
            waveform = torchaudio.functional.resample(waveform, sr, target_sr)
        return waveform.unsqueeze(0)  # [1,C,T]
    except Exception:
        return None


def silence(sr: int, duration_sec: float, channels: int = 2) -> torch.Tensor:
    return torch.zeros(1, channels, max(1, int(sr * duration_sec)))


def trim_audio(audio, start_index, duration):
    waveform = audio["waveform"]
    sample_rate = audio["sample_rate"]
    audio_length = waveform.shape[-1]

    if start_index < 0:
        start_frame = audio_length + int(round(start_index * sample_rate))
    else:
        start_frame = int(round(start_index * sample_rate))
    start_frame = max(0, min(start_frame, audio_length - 1))

    end_frame = start_frame + int(round(duration * sample_rate))
    end_frame = max(0, min(end_frame, audio_length))

    if start_frame >= end_frame:
        raise ValueError("AudioTrim: Start time must be less than end time and be within the audio length.")

    return {"waveform": waveform[..., start_frame:end_frame], "sample_rate": sample_rate}