"""Local, offline speech-to-text using OpenAI Whisper.

Run it directly to transcribe a file::

    python -m services.transcription data/user_files/audio/avouris.wav
    python -m services.transcription            # newest recording
"""

import sys
import time
from pathlib import Path
from typing import Optional

import torch

sys.path.append(str(Path(__file__).parent.parent))  # noqa: E402
from config import USER_FILES_DIR

DEFAULT_AUDIO = USER_FILES_DIR / "audio" / "avouris-mathesis.wav"
DEFAULT_MODEL_SIZE = "small"
DEFAULT_LANGUAGE = "el"

_models = {}  # cache per model size, so tiny/base/small/medium are kept separately


def load_model(model_size: str = DEFAULT_MODEL_SIZE):
    """Load (and cache) a Whisper model of the given size."""
    if model_size not in _models:
        import whisper

        print(f"Loading local Whisper model '{model_size}'...")
        _models[model_size] = whisper.load_model(model_size)
    return _models[model_size]


def transcribe(
    audio_path: Path,
    language: str = DEFAULT_LANGUAGE,
    model_size: str = DEFAULT_MODEL_SIZE,
) -> dict:
    """Transcribe ``audio_path``.

    Returns a dict with the transcript, the wall-clock time of the
    transcription call only (model loading excluded), and the peak GPU
    memory allocated by PyTorch during that call.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = load_model(model_size)  # loaded before the timer starts

    use_cuda = torch.cuda.is_available()
    if use_cuda:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()

    t0 = time.perf_counter()
    result = model.transcribe(str(audio_path), language=language, fp16=use_cuda)
    if use_cuda:
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - t0

    peak_gb = torch.cuda.max_memory_allocated() / 1e9 if use_cuda else None

    return {
        "model": model_size,
        "device": "cuda" if use_cuda else "cpu",
        "precision": "fp16" if use_cuda else "fp32",
        "text": result["text"].strip(),
        "seconds": round(elapsed, 2),
        "peak_gpu_gb": round(peak_gb, 3) if peak_gb is not None else None,
    }



def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    audio_path = DEFAULT_AUDIO
    if audio_path is None:
        print(f"No recording found in {USER_FILES_DIR}. Record one first.")
        return 1

    print(f"Transcribing {audio_path} ...")
    info = transcribe(audio_path)
    print("\n--- Transcription Complete ---")
    print(f"model={info['model']} device={info['device']} "
          f"precision={info['precision']} time={info['seconds']}s "
          f"peak_gpu={info['peak_gpu_gb']} GB")
    print(info["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())