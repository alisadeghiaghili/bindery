"""Progress events shared by CLI, GUI, and pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "ProgressCallback",
    "ProgressEvent",
    "ProgressStage",
]

ProgressStage = Literal["discover", "transform", "assemble", "done", "skipped"]


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """One progress notification emitted by the pipeline.

    Attributes:
        stage: Pipeline stage that produced this event.
        completed: Units finished so far (pages, etc.).
        total: Total units in this stage.
        current: Optional label for the unit being processed.
        message: Optional human-readable detail.

    Examples:
        >>> ProgressEvent(stage="transform", completed=1, total=3, current="a.png").fraction
        0.3333333333333333
    """

    stage: ProgressStage
    completed: int
    total: int
    current: str | None = None
    message: str | None = None

    @property
    def fraction(self) -> float:
        """Return completion ratio in ``[0.0, 1.0]``.

        Returns:
            float: ``completed / total``, or ``1.0`` when ``total`` is 0.

        Examples:
            >>> ProgressEvent(stage="done", completed=2, total=2).fraction
            1.0
        """
        if self.total <= 0:
            return 1.0
        return min(1.0, max(0.0, self.completed / self.total))


ProgressCallback = Callable[[ProgressEvent], None]
