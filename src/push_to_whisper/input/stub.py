import logging
from typing import Callable

from push_to_whisper.input.base import BaseInputAdapter

logger = logging.getLogger(__name__)


class StubInputAdapter(BaseInputAdapter):
    """
    Fallback adapter that does nothing but logs actions.
    Used for unsupported OS or headless environments.
    """

    def start(
        self,
        on_pressed: Callable[[str], None],
        on_released: Callable[[str], None],
        pipelines: list,
    ) -> None:
        logger.info("Stub Input Adapter started (No-op).")
        import time

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def stop(self) -> None:
        logger.info("Stub Input Adapter stopped.")
