import logging
import time
from typing import TYPE_CHECKING, Any, Dict

from push_to_whisper.pipeline.base import BaseStep

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class TranscribeStep(BaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        if not state.whisper_text:
            logger.info(f"Transcribing {state.audio_path.name}")
            # Determine language - priority: step options > config
            language = options.get("language")
            if not language:
                # Get from the first enabled whisper config
                if ctx.settings.whisper.whisper_cpp.enabled:
                    language = ctx.settings.whisper.whisper_cpp.language
                elif ctx.settings.whisper.openai.enabled:
                    language = ctx.settings.whisper.openai.language

            # BaseWhisperClient.transcribe returns a plain string
            state.whisper_text = ctx.whisper.transcribe(
                state.audio_path,
                language=language,
            )

        # Update processing time (elapsed since start)
        state.processing_time_sec = time.time() - state.start_time.timestamp()
