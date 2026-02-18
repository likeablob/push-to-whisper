from abc import ABC, abstractmethod
from typing import Callable


class BaseInputAdapter(ABC):
    """
    Abstract base class for capturing global shortcut events.
    Different operating systems and desktop environments will have their own implementations.
    """

    @abstractmethod
    def start(
        self,
        on_pressed: Callable[[str], None],
        on_released: Callable[[str], None],
        pipelines: list,
    ) -> None:
        """
        Start listening for shortcut events.

        Args:
            on_pressed: Callback function to be called when a shortcut is pressed.
                        Takes pipeline_id as argument.
            on_released: Callback function to be called when a shortcut is released.
                        Takes pipeline_id as argument.
            pipelines: List of PipelineConfig to be registered.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and release resources."""
        pass
