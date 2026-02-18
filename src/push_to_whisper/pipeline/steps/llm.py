import logging
from typing import TYPE_CHECKING, Any, Dict

from jinja2 import DebugUndefined, Environment

from push_to_whisper.pipeline.base import BaseStep

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class LLMBaseStep(BaseStep):
    """Base class for LLM steps. Supports input generation via Jinja2 templates."""

    def _render(self, template_str: str, state: "PipelineState") -> str:
        env = Environment(undefined=DebugUndefined)
        template = env.from_string(template_str)
        return template.render(**state.to_template_vars())


class LLMRefineStep(LLMBaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        if not ctx.settings.llm.model:
            logger.warning("LLM model not configured, skipping refine.")
            return

        # Template both the input text and system prompt
        input_text = self._render(
            options.get("input_template", "{{ full_text }}"), state
        )
        system_prompt = self._render(
            options.get(
                "system_prompt_template", "You are a professional writing assistant."
            ),
            state,
        )

        refined = ctx.llm.refine_text(
            input_text,
            mode="refine",
            prompt_override=system_prompt,
        )
        state.refined_text = refined
        state.display_sections["refined_text"] = refined


class LLMInstructionStep(LLMBaseStep):
    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        if not ctx.settings.llm.model:
            logger.warning("LLM model not configured, skipping instruction.")
            return

        input_text = self._render(
            options.get("input_template", "{{ full_text }}"), state
        )
        system_prompt = self._render(
            options.get(
                "system_prompt_template", "You are a versatile document assistant."
            ),
            state,
        )

        result = ctx.llm.refine_text(
            input_text,
            mode="instruction",
            prompt_override=system_prompt,
        )
        state.instruction_result = result
        state.display_sections["instruction_result"] = result
