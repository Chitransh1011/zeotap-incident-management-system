import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry(operation: Callable[[], Awaitable[T]], attempts: int = 3, base_delay: float = 0.05) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as error:
            last_error = error
            if attempt < attempts - 1:
                await asyncio.sleep(base_delay * (2**attempt))
    raise last_error or RuntimeError("Retry failed")
