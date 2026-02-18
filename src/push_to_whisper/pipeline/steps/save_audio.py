import logging
import shutil
from typing import TYPE_CHECKING, Any, Dict

from push_to_whisper.pipeline.base import BaseStep

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class SaveAudioStep(BaseStep):
    """Step to persist temporary audio files by moving them to the configured official storage location."""

    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        if not state.audio_path.exists():
            logger.warning("save_audio skipped: Audio file does not exist.")
            return

        # Generate the official storage path (ignore the md side of wav/md, maintain audio extension)
        final_audio_path, _ = ctx.get_output_paths()
        final_audio_path = final_audio_path.with_suffix(state.audio_path.suffix)

        # Create directory
        final_audio_path.parent.mkdir(parents=True, exist_ok=True)

        # Move (Persist)
        try:
            shutil.move(str(state.audio_path), str(final_audio_path))
            state.audio_path = final_audio_path
            logger.info(f"Persisted audio file to: {final_audio_path}")
        except Exception as e:
            logger.error(f"Failed to persist audio file: {e}")
            raise
