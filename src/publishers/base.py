"""Publishing module base — future YouTube/publishing integration point.

This module defines the Publisher protocol. The default implementation is
NoOpPublisher (does nothing). A future publishing module implements this
protocol and is injected into the pipeline's publish hook.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Publisher(Protocol):
    """Protocol for publishing modules."""

    async def publish(self, video_path: Path, metadata: dict) -> None: ...


class NoOpPublisher:
    """Default no-op publisher. Future publishing module replaces this."""

    async def publish(self, video_path: Path, metadata: dict) -> None:
        pass
