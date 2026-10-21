from anyio import to_thread

from app.core.config import settings
from app.db.session import engine

# The threads that answer the sync endpoints: anyio's default limiter.
SERVER_THREADS = 40


def test_the_pool_is_configured_from_the_settings():
    assert engine.pool.size() == settings.DB_POOL_SIZE
    assert engine.pool._max_overflow == settings.DB_MAX_OVERFLOW  # noqa: SLF001
    assert engine.pool.timeout() == settings.DB_POOL_TIMEOUT


def test_the_pool_is_never_smaller_than_the_server_threads():
    """With fewer connections than threads the API stalls under load (see config.py)."""
    assert settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW >= SERVER_THREADS


def test_the_server_threads_are_the_ones_the_pool_is_sized_for():
    import anyio

    async def total_tokens() -> float:
        return to_thread.current_default_thread_limiter().total_tokens

    assert anyio.run(total_tokens) == SERVER_THREADS
