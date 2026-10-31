from anyio import from_thread, to_thread
from starlette.requests import Request

from app.core.config import settings
from app.core.security import ACCESS_COOKIE_NAME, create_access_token, hash_password
from app.db.session import engine
from app.domains.auth.dependencies import get_current_verified_user
from app.domains.payments.gateway import MBWayPayment, get_mbway_gateway
from app.domains.payments.models import TransactionStatus
from app.domains.payments.router import initiate_threads
from app.domains.users.models import User
from app.main import app
from tests.helpers import INITIATE_URL, authenticate, seed_ticket_tiers

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


def test_signing_in_a_request_does_not_keep_a_database_connection(db_session):
    """The session is checked in a thread of its own, and the endpoint waits for another
    one. If the check kept its connection while waiting, a burst of slow requests (a
    slow payment provider) would hold every connection with no thread free to finish
    and the whole API would stall until DB_POOL_TIMEOUT (measured in the load test)."""
    db_session.expire_on_commit = False  # like SessionLocal
    user = User(
        name="Ana Silva",
        email="ana@example.com",
        password_hash=hash_password("Password123!"),
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(user.id, user.token_version)
    request = Request(
        {
            "type": "http",
            "headers": [(b"cookie", f"{ACCESS_COOKIE_NAME}={token}".encode())],
        }
    )

    signed_in = get_current_verified_user(request, db_session)

    assert not db_session.in_transaction()
    assert signed_in.id == user.id


class ThreadCountingGateway:
    """Records, from inside the call to the provider, whose threads are busy."""

    name = "counting"

    def __init__(self) -> None:
        self.busy: dict[str, float] = {}

    def create_payment(self, **_) -> MBWayPayment:
        def count() -> None:
            shared = to_thread.current_default_thread_limiter().borrowed_tokens
            self.busy = {
                "shared": shared,
                "payments": initiate_threads().borrowed_tokens,
            }

        from_thread.run_sync(count)
        return MBWayPayment(provider_reference="COUNT-1")

    def get_status(self, **_) -> TransactionStatus:
        return TransactionStatus.PENDING


def test_a_slow_provider_does_not_hold_the_shared_threads(
    auth_client, email_sender, db_session
):
    """Starting a payment waits on the provider in threads of its own: at 9 s per call
    the shared threads ran out and every request (even /health/ready) waited."""
    seed_ticket_tiers(db_session)
    authenticate(auth_client, email_sender, db_session)
    gateway = ThreadCountingGateway()
    app.dependency_overrides[get_mbway_gateway] = lambda: gateway

    response = auth_client.post(
        INITIATE_URL, json={"ticket_tier": "geral", "phone": "912345678"}
    )

    assert response.status_code == 201
    assert gateway.busy == {"shared": 0, "payments": 1}


def test_the_payment_threads_come_from_the_settings():
    assert initiate_threads().total_tokens == settings.PAYMENT_INITIATE_THREADS
