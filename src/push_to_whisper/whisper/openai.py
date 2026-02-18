import logging
from pathlib import Path
from typing import Optional

import requests

from push_to_whisper.whisper.base import BaseWhisperClient

logger = logging.getLogger(__name__)


class WhisperOpenAIClient(BaseWhisperClient):
    """
    Client for OpenAI-compatible Whisper API (e.g., OpenAI, Speaches, LocalAI).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "whisper-1",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Transcribe audio via OpenAI-compatible /audio/transcriptions endpoint."""
        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/wav")}
            data = {
                "model": self.model,
                "response_format": "text",
            }
            if language:
                data["language"] = language

            logger.info(f"Sending transcription request to {url}")
            response = requests.post(
                url, headers=headers, files=files, data=data, timeout=120
            )
            response.raise_for_status()

            return response.text.strip()
