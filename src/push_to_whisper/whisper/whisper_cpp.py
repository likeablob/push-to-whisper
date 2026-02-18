import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from push_to_whisper.whisper.base import BaseWhisperClient

logger = logging.getLogger(__name__)


class WhisperCppClient(BaseWhisperClient):
    """
    Client for whisper.cpp HTTP server.
    Ref: https://github.com/ggerganov/whisper.cpp/blob/master/examples/server/README.md
    """

    def __init__(self, base_url: str = "http://localhost:50060"):
        self.base_url = base_url

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Transcribe and return only the text (for simple interface)."""
        result = self.transcribe_detailed(audio_path, language=language)
        return result.get("text", "").strip()

    def transcribe_detailed(
        self, audio_path: Path, language: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Send audio file to whisper.cpp server and get detailed JSON response.
        Note: whisper.cpp server's /inference endpoint accepts some parameters
        like temperature, but language/model are usually server-side options.
        """
        url = f"{self.base_url}/inference"
        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {
                "response_format": "json",
                # Note: language is supported in some versions of whisper.cpp server
                # but often it is a server-side flag (-l).
                **kwargs,
            }
            if language:
                data["language"] = language

            response = requests.post(url, files=files, data=data, timeout=120)
            response.raise_for_status()

            return response.json()
