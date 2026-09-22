import asyncio
import random
from collections.abc import Awaitable, Callable


async def run_with_retries[T](
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    factor: float = 2.0,
    jitter: float = 0.25,
    is_retryable: Callable[[Exception], bool] | None = None,
    on_retry: Callable[[int, Exception], None] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Ejecuta `operation` con backoff exponencial ante errores reintentables.

    Reintenta hasta `attempts` veces (default 3). Solo reintenta cuando
    `is_retryable(exc)` es True; por defecto usa el atributo `retryable`
    de la excepción. Re-lanza la última excepción si se agotan los intentos.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    retryable = is_retryable or (lambda exc: bool(getattr(exc, "retryable", False)))

    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt >= attempts or not retryable(exc):
                raise
            delay = base_delay * (factor ** (attempt - 1))
            delay *= 1 + random.uniform(-jitter, jitter)
            if on_retry is not None:
                on_retry(attempt, exc)
            await sleep(delay)

    raise AssertionError("unreachable")
