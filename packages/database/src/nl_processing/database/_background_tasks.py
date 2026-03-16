"""Background task management for DatabaseService."""

import asyncio


class BackgroundTaskManager:
    """Manages background translation tasks for a DatabaseService instance."""

    def __init__(self) -> None:
        """Initialize empty task tracker."""
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._stored_exceptions: list[Exception] = []

    def create_translation_task(self, coro_func: callable, *args, **kwargs) -> None:
        """Create and track a background translation task.

        Args:
            coro_func: The coroutine function to run as a background task
            *args, **kwargs: Arguments to pass to the coroutine function
        """

        async def task_wrapper() -> None:
            try:
                # Call the original function normally to preserve fire-and-forget behavior
                await coro_func(*args, **kwargs)
            except Exception as e:
                # Store the original exception for explicit cleanup path
                self._stored_exceptions.append(e)
                # Do NOT re-raise here to avoid unhandled task exceptions during normal operation
                # The original function has already handled logging and other side effects

        task = asyncio.create_task(task_wrapper())
        self._background_tasks.add(task)

        def cleanup_task(finished_task: asyncio.Task[None]) -> None:
            self._background_tasks.discard(finished_task)

        task.add_done_callback(cleanup_task)

    async def wait_for_background_translations(self) -> None:
        """Wait for all background translation tasks to complete.

        This method must be called before service teardown to ensure
        background translation tasks don't outlive schema teardown.
        Surfaces real task errors to the caller instead of silently swallowing them.
        """
        # Wait for any remaining active tasks
        if self._background_tasks:
            # Create a copy since the set may be modified by done callbacks during await
            tasks_to_wait = list(self._background_tasks)
            # Wait for all tasks to complete
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)

        # Surface any stored exceptions from already-finished or just-finished tasks
        if self._stored_exceptions:
            # Re-raise the first exception that was stored
            exception_to_raise = self._stored_exceptions[0]
            # Clear all stored exceptions after raising
            self._stored_exceptions.clear()
            raise exception_to_raise
