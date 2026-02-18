import logging
from typing import TYPE_CHECKING, Any, Dict

from jinja2 import DebugUndefined, Environment

from push_to_whisper.clipboard import copy_to_clipboard as clipboard_copy
from push_to_whisper.pipeline.base import BaseStep

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class CopyClipboardStep(BaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        text_to_copy = (
            state.refined_text or state.instruction_result or state.whisper_text
        )
        clipboard_copy(text_to_copy)
        logger.info("Copied text to clipboard.")


class AppriseStep(BaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        template_vars = state.to_template_vars()

        # Identify final text based on priority (available as {{ final_text }} within the template)
        template_vars["final_text"] = (
            state.rendered_content
            or state.refined_text
            or state.instruction_result
            or state.whisper_text
        )

        # Jinja2 Environment for notifications
        env = Environment(undefined=DebugUndefined)

        try:
            title_tmpl = env.from_string(
                options.get("title_template", "Transcription Complete")
            )
            title = title_tmpl.render(**template_vars)

            body_tmpl = env.from_string(
                options.get("body_template", "{{ final_text | truncate(100) }}")
            )
            body = body_tmpl.render(**template_vars)
        except Exception as e:
            logger.error(f"Notification template rendering failed: {e}")
            title = "Transcription Complete"
            body = template_vars["final_text"][:100]

        ctx.notifier.notify(title=title, body=body, urls=options.get("urls"))
        logger.info("Sent Apprise notification.")
