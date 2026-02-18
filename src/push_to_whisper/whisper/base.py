from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseWhisperClient(ABC):
    """Abstract base class for Whisper transcription clients."""

    @abstractmethod
    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """
        Transcribe the given audio file.

        Args:
            audio_path: Path to the WAV audio file.
            language: Optional language code (e.g., 'ja', 'en').

        Returns:
            The transcribed text.
        """
        pass
