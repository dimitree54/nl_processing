"""Background task management for cache services."""

import asyncio
from collections.abc import Awaitable


class BackgroundTaskManager:
    """Manages background asyncio tasks with proper cleanup."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[object]] = set()

    def create_task(self, coro: Awaitable[object]) -> None:
        """Create a background task and track it for cleanup."""
        task = asyncio.create_task(coro)
        if task is not None:
            try:
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
            except AttributeError:
                # Task object doesn't support done callbacks (e.g., in tests)
                pass

    async def close(self) -> None:
        """Cancel and wait for all background tasks to complete."""
        if not self._tasks:
            return

        # Cancel all remaining tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for all tasks to finish (either complete or be cancelled)
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()
