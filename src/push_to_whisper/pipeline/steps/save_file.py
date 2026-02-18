import logging
from typing import TYPE_CHECKING, Any, Dict

from jinja2 import DebugUndefined, Environment

from push_to_whisper.pipeline.base import BaseStep

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class SaveMarkdownStep(BaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        state.text_path = state.audio_path.with_suffix(".md")
        state.text_path.parent.mkdir(parents=True, exist_ok=True)

        template_vars = state.to_template_vars()

        # Jinja2 Environment with DebugUndefined
        # This keeps undefined variables as {{ var_name }} in the output
        env = Environment(undefined=DebugUndefined)
        template_str = ctx.settings.storage.markdown_template

        try:
            template = env.from_string(template_str)
            md_content = template.render(**template_vars)
            # Save the rendering result to state (making it available for subsequent steps)
            state.rendered_content = md_content
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            # Fallback to a simple message or raw template if rendering fails completely
            md_content = template_str

        state.text_path.write_text(md_content, encoding="utf-8")
        logger.info(f"Saved Markdown to: {state.text_path}")
