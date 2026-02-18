import logging
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from push_to_whisper.main_daemon import DaemonContext
    from push_to_whisper.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


class BaseStep:
    """Base class for all pipeline steps."""

    def execute(
        self, ctx: "DaemonContext", state: "PipelineState", options: Dict[str, Any]
    ) -> None:
        """
        Execution logic for the step. Updates the state object directly.

        Args:
            ctx: Daemon context (Settings, Clients, etc.)
            state: Shared pipeline state
            options: Step-specific options from config
        """
        raise NotImplementedError
