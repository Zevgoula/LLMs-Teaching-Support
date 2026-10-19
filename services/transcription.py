"""Local, offline speech-to-text using OpenAI Whisper.

The model used to be loaded and the transcription started at *import* time,
which made this module impossible to reuse. It is now a plain function plus a
small ``python -m`` CLI.

Run it directly to transcribe the newest recording::

    python -m services.transcription
    python -m services.transcription data/user_files/recording_20260930_133500.wav
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))  # noqa: E402
from config import USER_FILES_DIR

#: Whisper model size. "base" is fast/lightweight, "small"/"medium" are more
#: accurate for Greek but slower.
DEFAULT_MODEL_SIZE = "base"
DEFAULT_LANGUAGE = "el"

_model = None


def load_model(model_size: str = DEFAULT_MODEL_SIZE):
    """Load (and cache) a Whisper model."""
    global _model
    if _model is None:
        import whisper

        print(f"Loading local Whisper model '{model_size}' (CPU/GPU)...")
        _model = whisper.load_model(model_size)
    return _model


def transcribe(
    audio_path: Path,
    language: str = DEFAULT_LANGUAGE,
    model_size: str = DEFAULT_MODEL_SIZE,
) -> str:
    """Transcribe ``audio_path`` and return the plain-text transcript."""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = load_model(model_size)
    result = model.transcribe(str(audio_path), language=language)
    return result["text"].strip()


def latest_recording(directory: Path = USER_FILES_DIR) -> Optional[Path]:
    """Return the most recent ``*.wav`` in ``directory`` (or ``None``)."""
    recordings = sorted(
        Path(directory).glob("*.wav"), key=lambda p: p.stat().st_mtime
    )
    return recordings[-1] if recordings else None


def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    audio_path = Path(argv[0]) if argv else latest_recording()
    if audio_path is None:
        print(f"No recording found in {USER_FILES_DIR}. Record one first.")
        return 1

    print(f"Transcribing {audio_path} ...")
    print("\n--- Transcription Complete ---")
    print(transcribe(audio_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())