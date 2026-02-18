import logging

from push_to_whisper.config import Settings
from push_to_whisper.whisper.base import BaseWhisperClient
from push_to_whisper.whisper.openai import WhisperOpenAIClient
from push_to_whisper.whisper.whisper_cpp import WhisperCppClient

logger = logging.getLogger(__name__)


def get_whisper_client(settings: Settings) -> BaseWhisperClient:
    """
    Factory function to initialize the appropriate Whisper client based on settings.
    """
    w_cfg = settings.whisper

    if w_cfg.openai.enabled:
        logger.info(f"Initializing WhisperOpenAIClient at {w_cfg.openai.base_url}")
        return WhisperOpenAIClient(
            api_key=w_cfg.openai.api_key or "empty",
            base_url=w_cfg.openai.base_url,
            model=w_cfg.openai.model,
        )

    if w_cfg.whisper_cpp.enabled:
        logger.info(f"Initializing WhisperCppClient at {w_cfg.whisper_cpp.base_url}")
        return WhisperCppClient(base_url=w_cfg.whisper_cpp.base_url)

    # Fallback or future providers
    if w_cfg.openai.enabled:
        # return OpenAiWhisperClient(...)
        raise NotImplementedError("OpenAI Whisper client is not yet implemented.")

    raise ValueError(
        "No Whisper provider is enabled in the configuration. "
        "Please enable at least one (e.g., whisper_cpp or openai)."
    )
