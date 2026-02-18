import logging
import os
import sys

from push_to_whisper.input.base import BaseInputAdapter
from push_to_whisper.input.stub import StubInputAdapter

logger = logging.getLogger(__name__)


def get_default_input_adapter(app_id: str) -> BaseInputAdapter:
    """
    Detect the current environment and return the appropriate input adapter.
    """
    if sys.platform == "linux":
        # Check if running under Wayland
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            try:
                from push_to_whisper.input.wayland_portal import (
                    WaylandPortalInputAdapter,
                )

                return WaylandPortalInputAdapter(app_id)
            except Exception as e:
                logger.error(f"Failed to load WaylandPortalInputAdapter: {e}")
                return StubInputAdapter()
        else:
            logger.warning(
                f"Linux session type '{os.environ.get('XDG_SESSION_TYPE')}' is not explicitly supported yet. "
                "Falling back to Stub adapter."
            )
            return StubInputAdapter()

    elif sys.platform == "darwin":
        logger.info(
            "macOS detected. Native shortcut support is coming soon. Using Stub adapter."
        )
        return StubInputAdapter()

    elif sys.platform == "win32":
        logger.info(
            "Windows detected. Native shortcut support is coming soon. Using Stub adapter."
        )
        return StubInputAdapter()

    else:
        logger.warning(
            f"Platform '{sys.platform}' is not supported. Using Stub adapter."
        )
        return StubInputAdapter()
