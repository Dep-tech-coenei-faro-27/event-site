"""The live status stream of a payment (Server-Sent Events), and the loop behind it.

``GET /payment/transactions/{reference}/events`` keeps one request open per payment
being waited for. It first sends the current status, then every change as it happens,
with a heartbeat so proxies do not close a quiet connection. The stream holds no
database connection while it waits: a session is only used to authenticate, to read
the status at the start and by the loop that asks the provider.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select

from app.core.config import settings
from app.core.rate_limit import RateLimit, enforce_rate_limit
from app.db.session import SessionLocal
from app.domains.auth.dependencies import get_current_verified_session
from app.domains.payments.events import FINAL_STATUSES, events
from app.domains.payments.gateway import MBWayGateway, get_mbway_gateway
from app.domains.payments.models import Transaction
from app.domains.payments.service import (
    pending_references_to_sweep,
    refresh_pending_payment,
)

logger = logging.getLogger(__name__)

RECONCILE_CONCURRENCY = 4


def format_status(value: str) -> str:
    return f"event: status\ndata: {json.dumps({'status': value})}\n\n"


def authorize(request: Request, reference: str) -> int:
    """Check the session and that the payment is the person's. Returns the user id.

    The payment of someone else does not exist for this person (404), like the poll.
    """
    with SessionLocal() as db:
        user = get_current_verified_session(request, db).user
        rule = RateLimit(
            "payment_status", settings.RATE_LIMIT_PAYMENT_STATUS_PER_MINUTE, 60
        )
        enforce_rate_limit(db, (rule,), str(user.id))
        found = db.scalar(
            select(Transaction.id).where(
                Transaction.reference == reference, Transaction.user_id == user.id
            )
        )
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
            )
        return user.id


def current_status(reference: str) -> str | None:
    with SessionLocal() as db:
        value = db.scalar(
            select(Transaction.status).where(Transaction.reference == reference)
        )
        return None if value is None else value.value


async def event_stream(
    reference: str, user_id: int, queue: "asyncio.Queue[str]"
) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + settings.PAYMENT_EVENTS_MAX_SECONDS
    try:
        yield "retry: 3000\n\n"
        # Read after subscribing: a change in between is in the queue, never lost.
        current = await run_in_threadpool(current_status, reference)
        if current is None:
            return
        yield format_status(current)
        if current in FINAL_STATUSES:
            return
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return  # the browser reconnects and is told the status again
            try:
                new = await asyncio.wait_for(
                    queue.get(),
                    min(settings.PAYMENT_EVENTS_HEARTBEAT_SECONDS, remaining),
                )
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            yield format_status(new)
            if new in FINAL_STATUSES:
                return
    finally:
        events.unsubscribe(reference, user_id, queue)


def _refresh(reference: str, gateway: MBWayGateway) -> None:
    with SessionLocal() as db:
        refresh_pending_payment(db, reference, gateway)


async def reconcile_once() -> None:
    references = events.listening()
    if not references:
        return
    try:
        gateway = get_mbway_gateway()
    except HTTPException:
        return  # payments are off
    gate = asyncio.Semaphore(RECONCILE_CONCURRENCY)

    async def one(reference: str) -> None:
        async with gate:
            try:
                await run_in_threadpool(_refresh, reference, gateway)
            except Exception:  # noqa: BLE001
                logger.exception("Could not refresh payment %s", reference)

    await asyncio.gather(*(one(reference) for reference in references))


def _references_to_sweep(provider: str) -> list[str]:
    with SessionLocal() as db:
        return pending_references_to_sweep(
            db,
            min_age_seconds=settings.PAYMENT_SWEEP_MIN_AGE_SECONDS,
            limit=settings.PAYMENT_SWEEP_BATCH,
            provider=provider,
        )


async def sweep_once() -> int:
    """Ask the provider about every payment still ``pending`` after a while.

    The safety net for a webhook that never arrived: ``reconcile_once`` only looks at
    payments somebody is waiting for on the status stream, so a payment whose page was
    closed would stay ``pending`` until the person came back. Here every old enough
    ``pending`` payment is asked about (throttled per payment like a poll, a few at a
    time) and the answer is applied as the webhook would. Returns how many were asked.
    """
    try:
        gateway = get_mbway_gateway()
    except HTTPException:
        return 0  # payments are off
    references = await run_in_threadpool(_references_to_sweep, gateway.name)
    if not references:
        return 0
    gate = asyncio.Semaphore(RECONCILE_CONCURRENCY)

    async def one(reference: str) -> None:
        async with gate:
            try:
                await run_in_threadpool(_refresh, reference, gateway)
            except Exception:  # noqa: BLE001
                logger.exception("Could not refresh payment %s", reference)

    await asyncio.gather(*(one(reference) for reference in references))
    return len(references)


async def sweep_forever() -> None:
    """Run ``sweep_once`` every ``PAYMENT_SWEEP_SECONDS`` (``0`` turns it off)."""
    if settings.PAYMENT_SWEEP_SECONDS <= 0:
        return
    while True:
        await asyncio.sleep(settings.PAYMENT_SWEEP_SECONDS)
        try:
            asked = await sweep_once()
            if asked:
                logger.info("Payment sweep asked about %d pending payments", asked)
        except Exception:  # noqa: BLE001
            logger.exception("The payment sweep failed")


async def reconcile_forever() -> None:
    """Ask the provider about the payments somebody is waiting for, once for all.

    Without this the status would only change when a poll or the provider's callback
    arrived. Each payment is asked at most every
    ``PAYMENT_PROVIDER_MIN_INTERVAL_SECONDS`` and only a few at a time, so a slow
    provider cannot take every thread.
    """
    while True:
        await asyncio.sleep(settings.PAYMENT_EVENTS_RECONCILE_SECONDS)
        try:
            await reconcile_once()
        except Exception:  # noqa: BLE001
            logger.exception("The payment reconciliation pass failed")
