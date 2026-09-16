"""
Voice pipeline: speech-to-text and text-to-speech.

Wraps an ASR call (e.g. Whisper) for incoming voice complaints, and a TTS
call for spoken replies. Both fall back to mock implementations when no
API key is configured, so the CLI demo works without any audio backend.

Course tie-in: Module 5 · Lesson 2 (Voice AI Fundamentals and Speech Processing)
"""

from __future__ import annotations

from pathlib import Path

from src.llm.client import LLMClient, get_default_client


def transcribe(audio_path: str | Path, llm: LLMClient | None = None) -> str:
    """Transcribe a voice complaint to text.

    Live mode (sketch): send the audio bytes to a Whisper-style ASR endpoint.
    Mock mode: return a canned transcript derived from the filename, so a demo
    can still flow through classification/reply drafting without real audio.
    """
    llm = llm or get_default_client()
    path = Path(audio_path)

    if llm.mock_mode:
        if not path.exists():
            raise FileNotFoundError(f"No such audio file: {path}")
        return (
            "Hi, I'm calling about an order that showed as delivered yesterday "
            "but I never received the package. Can someone look into this?"
        )

    raise NotImplementedError(
        "Plug in a real ASR call here (e.g. Whisper API) using the audio bytes at `path`."
    )


def synthesize_speech(text: str, output_path: str | Path, llm: LLMClient | None = None) -> Path:
    """Convert text to a spoken audio reply.

    Live mode (sketch): call a TTS endpoint and write the returned audio bytes
    to `output_path`. Mock mode: write a small text stub instead of audio, so
    the pipeline can be verified end-to-end without an audio backend.
    """
    llm = llm or get_default_client()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if llm.mock_mode:
        out = out.with_suffix(".mock.txt")
        out.write_text(f"[MOCK TTS AUDIO for]: {text}")
        return out

    raise NotImplementedError(
        "Plug in a real TTS call here and write the resulting audio bytes to `output_path`."
    )
