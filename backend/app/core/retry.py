import asyncio
import logging
from typing import Callable, Any, TypeVar
import httpx

logger = logging.getLogger("webtoon_studio.retry")

T = TypeVar("T")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

async def with_retry(
    async_fn: Callable[[], Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    operation_name: str = "API request"
) -> Any:
    """
    Executes an async callable with exponential backoff for transient HTTP errors
    (429 Too Many Requests, 5xx Server Errors, Timeouts, and Network glitches).
    Non-retryable errors (400, 401, 402, 403, 404) fail immediately.
    """
    delay = initial_delay
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            return await async_fn()
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                retry_after = exc.response.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after and retry_after.isdigit() else delay
                logger.warning(
                    f"{operation_name} returned HTTP {exc.response.status_code}. "
                    f"Retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})..."
                )
                await asyncio.sleep(wait_time)
                delay *= backoff_factor
            else:
                raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            if attempt < max_retries:
                logger.warning(
                    f"{operation_name} failed with {type(exc).__name__}: {exc}. "
                    f"Retrying in {delay:.1f}s (attempt {attempt}/{max_retries})..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                raise
        except Exception:
            raise

    if last_exc:
        raise last_exc
