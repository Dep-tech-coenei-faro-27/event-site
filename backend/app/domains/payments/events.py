"""Live payment status for the waiting screen, over Server-Sent Events.

The browser opens one long-lived request per payment it is waiting for and is told the
moment the payment changes, instead of asking again every two seconds. Whoever changes a
payment calls :func:`notify`; the open streams of that payment receive the new status.

The registry is in memory, which works because the backend runs as a single process.
With more than one process each would only reach its own streams (it would then need
``LISTEN/NOTIFY`` or Redis). A stream holds no database connection while it waits.
"""

import asyncio
import logging
import threading
from collections import defaultdict

from app.domains.payments.models import TransactionStatus

logger = logging.getLogger(__name__)

# A payment in one of these states cannot change by itself any more.
FINAL_STATUSES = frozenset(
    status.value
    for status in TransactionStatus
    if status is not TransactionStatus.PENDING
)
QUEUE_SIZE = 8


class PaymentEvents:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._listeners: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._per_user: dict[int, int] = defaultdict(int)
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """The event loop that serves the streams (events are handed over to it)."""
        self._loop = loop

    def subscribe(
        self, reference: str, user_id: int, limit: int
    ) -> "asyncio.Queue[str] | None":
        """A queue that receives the statuses of ``reference``, or ``None`` if the
        person already has ``limit`` streams open."""
        with self._lock:
            if self._per_user[user_id] >= limit:
                return None
            self._per_user[user_id] += 1
            queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_SIZE)
            self._listeners[reference].add(queue)
            return queue

    def unsubscribe(
        self, reference: str, user_id: int, queue: "asyncio.Queue[str]"
    ) -> None:
        with self._lock:
            listeners = self._listeners.get(reference)
            if listeners is not None and queue in listeners:
                listeners.discard(queue)
                if not listeners:
                    del self._listeners[reference]
                self._per_user[user_id] = max(0, self._per_user[user_id] - 1)
                if self._per_user[user_id] == 0:
                    del self._per_user[user_id]

    def listening(self) -> list[str]:
        """The payments somebody is waiting for right now."""
        with self._lock:
            return list(self._listeners)

    def publish(self, reference: str, status: str) -> None:
        """Tell the streams of ``reference`` the new status. Safe from any thread and
        never raises: a notification must not break the payment that caused it."""
        try:
            loop = self._loop
            with self._lock:
                queues = list(self._listeners.get(reference, ()))
            if loop is None or not queues:
                return
            loop.call_soon_threadsafe(self._deliver, queues, status)
        except Exception:  # noqa: BLE001
            logger.exception("Could not publish the status of %s", reference)

    @staticmethod
    def _deliver(queues: "list[asyncio.Queue[str]]", status: str) -> None:
        for queue in queues:
            try:
                queue.put_nowait(status)
            except asyncio.QueueFull:
                pass  # it already has news pending; the stream re-reads the state


events = PaymentEvents()


def notify(reference: str, status: TransactionStatus) -> None:
    events.publish(reference, status.value)
