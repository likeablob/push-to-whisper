import logging
import shutil
from typing import TYPE_CHECKING, Any, Dict

from jinja2 import DebugUndefined, Environment

from push_to_whisper.audio_utils import transcode_audio
from push_to_whisper.pipeline.base import BaseStep

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class TranscodeStep(BaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        logger.info(f"Transcoding start. Options: {options}, Input: {state.audio_path}")
        new_path = transcode_audio(state.audio_path, options)
        if new_path:
            state.audio_path = new_path
            logger.info(f"Transcoded audio successfully: {new_path}")
        else:
            logger.error("Transcoding failed to produce a new path.")


class LLMPatchStep(BaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        if not state.text_path or not state.text_path.exists():
            logger.warning("llm_patch skipped: No target file.")
            return

        env = Environment(undefined=DebugUndefined)
        template_vars = state.to_template_vars()

        instruction_tmpl = options.get("instruction_template")
        if options.get("use_whisper_text_as_instruction"):
            instruction = state.whisper_text
        elif instruction_tmpl:
            instruction = env.from_string(instruction_tmpl).render(**template_vars)
        else:
            instruction = options.get("default_instruction")

        if not instruction:
            logger.warning("llm_patch skipped: No instruction provided.")
            return

        current_content = state.text_path.read_text(encoding="utf-8")
        patch_text = ctx.llm.generate_patch(instruction, current_content)

        if patch_text:
            # Create a backup to protect against destructive changes by LLM
            backup_path = state.text_path.with_suffix(state.text_path.suffix + ".bak")
            shutil.copy2(state.text_path, backup_path)
            try:
                if ctx.llm.apply_patch(state.text_path, patch_text):
                    state.patch_result = patch_text
                    backup_path.unlink()
                    logger.info(f"Applied patch to {state.text_path}")
                else:
                    logger.warning("Patch application failed, rolling back.")
                    shutil.move(str(backup_path), str(state.text_path))
            except Exception as e:
                logger.error(f"Error applying patch: {e}. Rolling back.")
                if backup_path.exists():
                    shutil.move(str(backup_path), str(state.text_path))
