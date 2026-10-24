import base64
import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from urllib import error, parse, request

from fastapi import HTTPException, status

from app.core.config import settings
from app.domains.payments.models import TransactionStatus

logger = logging.getLogger(__name__)

PAYMENTS_OFF_MESSAGE = "Payments are currently disabled."


class PaymentGatewayError(RuntimeError):
    """Raised when the payment provider is unreachable or answers badly.

    ``code`` is the provider's own error code when it gave one (Stripe's ``code``).
    """

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class AlreadyRefundedError(PaymentGatewayError):
    """The provider says this payment was already refunded in full."""


class UnrecognisedStatusError(PaymentGatewayError):
    """The provider answered, but with a status we do not know how to read."""


@dataclass(frozen=True)
class MBWayPayment:
    """The provider's answer to a payment request."""

    provider_reference: str | None
    status: TransactionStatus = TransactionStatus.PENDING


@runtime_checkable
class MBWayGateway(Protocol):
    name: str

    def create_payment(
        self,
        *,
        reference: str,
        amount_cents: int,
        phone: str,
        email: str,
    ) -> MBWayPayment: ...

    def get_status(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus: ...


@runtime_checkable
class RefundingGateway(Protocol):
    """A gateway that can give the money back through its API."""

    name: str

    def refund(
        self, *, reference: str, provider_reference: str | None, amount_cents: int
    ) -> str:
        """Refund the whole payment and return the provider's refund id."""
        ...


@runtime_checkable
class LookupGateway(Protocol):
    """A gateway that can find a payment again by our reference."""

    name: str

    def find_payment(self, *, reference: str) -> str | None:
        """The provider's id of the payment we made with this reference, if any."""
        ...


@runtime_checkable
class CancellingGateway(Protocol):
    """A gateway that can end a payment that is still waiting."""

    name: str

    def cancel_payment(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus:
        """End the payment: ``CONFIRMED`` if it was paid at that very moment,
        ``EXPIRED`` once it can no longer be paid."""
        ...


# ifthenpay MB WAY v2 status codes (see the official SDK's MbwayService):
# on creation only "000" means "accepted, pending"; on a status query "000" means
# "paid". The codes are the same shape but come from two different endpoints.
CREATE_OK = "000"
_STATUS_MAP = {
    "000": TransactionStatus.CONFIRMED,  # paid
    "123": TransactionStatus.PENDING,  # pending payment
    "020": TransactionStatus.FAILED,  # rejected by the user
    "101": TransactionStatus.EXPIRED,  # expired (4-minute window)
    "122": TransactionStatus.FAILED,  # declined
}


def _normalize_status(raw: object) -> TransactionStatus:
    """Read the provider's status code, as text or as a number.

    Anything else (a missing status, an unknown code) is an error and not "still
    waiting": a payment that is waiting keeps its seat, so an answer we cannot read
    must not be mistaken for that.
    """
    if raw is not None and not isinstance(raw, bool):
        status = _STATUS_MAP.get(str(raw).strip())
        if status is not None:
            return status
    logger.error("ifthenpay returned an unrecognised status: %r", raw)
    raise UnrecognisedStatusError(f"unrecognised status {raw!r}")


class IfThenPayMBWayGateway:
    """Real ifthenpay MB WAY v2 client (docs: ifthenpay.com)."""

    name = "ifthenpay"

    def __init__(
        self,
        *,
        mbway_key: str,
        base_url: str,
        timeout_seconds: int,
        auth_token: str = "",
        http_post: Callable[[str, dict, dict], Any] | None = None,
        http_get: Callable[[str, dict], Any] | None = None,
    ) -> None:
        self.mbway_key = mbway_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.auth_token = auth_token
        self._http_post = http_post or self._post_json
        self._http_get = http_get or self._get_json

    def _headers(self, *, json_body: bool) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if json_body:
            headers["Content-Type"] = "application/json"
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def _read_json(self, req: request.Request) -> dict:
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise PaymentGatewayError(
                f"gateway responded with HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise PaymentGatewayError(f"gateway unreachable: {exc.reason}") from exc

        try:
            data = json.loads(body or b"{}")
        except json.JSONDecodeError as exc:
            raise PaymentGatewayError("gateway returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise PaymentGatewayError("gateway returned an unexpected payload")
        return data

    def _post_json(self, url: str, payload: dict, headers: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method="POST")
        return self._read_json(req)

    def _get_json(self, url: str, headers: dict) -> dict:
        req = request.Request(url, headers=headers, method="GET")
        return self._read_json(req)

    def create_payment(
        self,
        *,
        reference: str,
        amount_cents: int,
        phone: str,
        email: str,
    ) -> MBWayPayment:
        payload = {
            "mbWayKey": self.mbway_key,
            "orderId": reference,
            "amount": f"{amount_cents / 100:.2f}",
            "mobileNumber": f"351#{phone}",
            "email": email,
        }
        data = self._http_post(self.base_url, payload, self._headers(json_body=True))
        code = str(data.get("Status", "")).strip()
        if code != CREATE_OK:
            message = data.get("Message") or "no message"
            raise PaymentGatewayError(
                f"gateway refused the payment request (Status={code!r}: {message})"
            )
        request_id = data.get("RequestId") or data.get("requestId")
        if not request_id:
            raise PaymentGatewayError("gateway response is missing RequestId")
        return MBWayPayment(
            provider_reference=str(request_id),
            status=TransactionStatus.PENDING,
        )

    def get_status(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus:
        if not provider_reference:
            return TransactionStatus.PENDING
        query = parse.urlencode(
            {"mbWayKey": self.mbway_key, "requestId": provider_reference}
        )
        data = self._http_get(
            f"{self.base_url}/status?{query}", self._headers(json_body=False)
        )
        return _normalize_status(data.get("Status"))


STRIPE_API_BASE = "https://api.stripe.com/v1"
_STRIPE_INTENT_ID = re.compile(r"pi_[A-Za-z0-9]+")
# A PaymentIntent that went back to ``requires_payment_method`` carries the reason in
# ``last_payment_error.code``. Only this one means "the time to approve ran out";
# every other code is a refusal (the person declined, MB WAY declined or is
# unavailable).
_STRIPE_EXPIRED_CODE = "payment_intent_payment_attempt_expired"
# ``requires_action`` is the MB WAY wait (``next_action.type`` is
# ``mb_way_await_authorization``); the others are transitions that settle soon.
_STRIPE_WAITING = {"requires_action", "processing", "requires_confirmation"}
# A card refund is ``re_...``; a refund of an MB WAY payment comes back as ``pyr_...``
# (seen in the sandbox with the API version we pin).
_PAYMENT_REFERENCE = re.compile(r"ENEI-[A-Z0-9]{10}")
_STRIPE_REFUND_ID = re.compile(r"(?:re|pyr)_[A-Za-z0-9]+")
# ``pending``: Stripe accepted the refund and the money is on its way back.
_STRIPE_REFUND_OK = {"succeeded", "pending"}


def _ended_intent(intent: dict) -> TransactionStatus | None:
    """``CONFIRMED`` or ``EXPIRED`` if the PaymentIntent is over, else ``None``."""
    if intent.get("status") == "succeeded":
        return TransactionStatus.CONFIRMED
    if intent.get("status") == "canceled":
        return TransactionStatus.EXPIRED
    return None


def stripe_status(intent: dict) -> TransactionStatus:
    """Read a Stripe PaymentIntent the way ``_normalize_status`` reads ifthenpay.

    An answer we cannot read is an error and not "still waiting", for the same
    reason: a payment that is waiting keeps its seat.
    """
    status = intent.get("status")
    if status == "succeeded":
        return TransactionStatus.CONFIRMED
    if status in _STRIPE_WAITING:
        return TransactionStatus.PENDING
    if status == "canceled":
        return TransactionStatus.FAILED
    if status == "requires_payment_method":
        code = (intent.get("last_payment_error") or {}).get("code")
        if code == _STRIPE_EXPIRED_CODE:
            return TransactionStatus.EXPIRED
        if code:
            return TransactionStatus.FAILED
        # Never confirmed, or no reason given: not something we can call over.
    logger.error("Stripe returned an unrecognised status: %r", status)
    raise UnrecognisedStatusError(f"unrecognised status {status!r}")


class StripeMBWayGateway:
    """MB WAY through Stripe's PaymentIntents API.

    Docs: docs.stripe.com/payments/mb-way.

    Same shape as the ifthenpay flow, with no redirect and no Stripe.js: the server
    creates and confirms the PaymentIntent with the phone number from our own form,
    the person approves in the MB WAY app, and we read the PaymentIntent back (the
    status poll, and the webhook once it is wired). The PaymentIntent id is the
    provider reference.
    """

    name = "stripe"

    def __init__(
        self,
        *,
        secret_key: str,
        timeout_seconds: int,
        api_version: str,
        base_url: str = STRIPE_API_BASE,
        http_request: Callable[[str, str, dict | None, dict], dict] | None = None,
    ) -> None:
        self.secret_key = secret_key
        self.timeout_seconds = timeout_seconds
        self.api_version = api_version
        self.base_url = base_url.rstrip("/")
        self._http_request = http_request or self._request_json

    def _headers(self, extra: dict | None = None) -> dict[str, str]:
        token = base64.b64encode(f"{self.secret_key}:".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "Stripe-Version": self.api_version,
            "Accept": "application/json",
        }
        headers.update(extra or {})
        return headers

    def _request_json(
        self, method: str, url: str, form: dict | None, headers: dict
    ) -> dict:
        data = None
        if form is not None:
            data = parse.urlencode(form).encode("utf-8")
            headers = {**headers, "Content-Type": "application/x-www-form-urlencoded"}
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
        except error.HTTPError as exc:
            message, code = self._describe_http_error(exc)
            raise PaymentGatewayError(message, code=code) from exc
        except error.URLError as exc:
            raise PaymentGatewayError(f"stripe unreachable: {exc.reason}") from exc
        try:
            parsed = json.loads(body or b"{}")
        except json.JSONDecodeError as exc:
            raise PaymentGatewayError("stripe returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise PaymentGatewayError("stripe returned an unexpected payload")
        return parsed

    @staticmethod
    def _describe_http_error(exc: error.HTTPError) -> tuple[str, str | None]:
        # Only the code and message Stripe documents for errors: never the request.
        try:
            detail = json.loads(exc.read() or b"{}").get("error") or {}
        except (json.JSONDecodeError, AttributeError):
            detail = {}
        code = detail.get("code") or detail.get("type") or "unknown"
        message = str(detail.get("message") or "no message")[:200]
        own_code = detail.get("code")
        return (
            f"stripe responded with HTTP {exc.code} ({code}): {message}",
            own_code if isinstance(own_code, str) else None,
        )

    def create_payment(
        self,
        *,
        reference: str,
        amount_cents: int,
        phone: str,
        email: str,
    ) -> MBWayPayment:
        form = {
            "amount": str(amount_cents),
            "currency": "eur",
            "payment_method_types[]": "mb_way",
            "payment_method_data[type]": "mb_way",
            "payment_method_data[billing_details][phone]": f"+351{phone}",
            "confirm": "true",
            "metadata[reference]": reference,
        }
        # The same reference always means the same PaymentIntent: a repeated request
        # (a timeout we retried, a double click) cannot create a second charge.
        headers = self._headers({"Idempotency-Key": f"enei-{reference}"})
        intent = self._http_request(
            "POST", f"{self.base_url}/payment_intents", form, headers
        )
        intent_id = intent.get("id")
        if not isinstance(intent_id, str) or not _STRIPE_INTENT_ID.fullmatch(intent_id):
            raise PaymentGatewayError("stripe response is missing the PaymentIntent id")
        return MBWayPayment(
            provider_reference=intent_id, status=TransactionStatus.PENDING
        )

    def get_status(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus:
        if not provider_reference:
            return TransactionStatus.PENDING
        return stripe_status(self._intent_of(reference, provider_reference))

    def _intent_of(self, reference: str, provider_reference: str | None) -> dict:
        """The PaymentIntent of this payment, read back from Stripe."""
        if not provider_reference or not _STRIPE_INTENT_ID.fullmatch(
            provider_reference
        ):
            raise PaymentGatewayError("not a Stripe PaymentIntent id")
        intent = self._http_request(
            "GET",
            f"{self.base_url}/payment_intents/{provider_reference}",
            None,
            self._headers(),
        )
        if (intent.get("metadata") or {}).get("reference") != reference:
            # Never act on a PaymentIntent that is not this payment's.
            raise PaymentGatewayError("PaymentIntent does not belong to this payment")
        return intent

    def find_payment(self, *, reference: str) -> str | None:
        """Find the PaymentIntent we made for this reference, by its metadata.

        For a payment whose id we never saved: Stripe created it but the answer to
        the creation got lost. Exactly one match is an answer; none, or more than
        one, is not (the search can lag a little behind a new payment, so "none"
        only means "not yet").
        """
        if not _PAYMENT_REFERENCE.fullmatch(reference):
            raise PaymentGatewayError("not a payment reference")
        query = parse.urlencode({"query": f"metadata['reference']:'{reference}'"})
        result = self._http_request(
            "GET",
            f"{self.base_url}/payment_intents/search?{query}",
            None,
            self._headers(),
        )
        matches = [
            item["id"]
            for item in result.get("data") or []
            if isinstance(item, dict)
            and (item.get("metadata") or {}).get("reference") == reference
            and isinstance(item.get("id"), str)
            and _STRIPE_INTENT_ID.fullmatch(item["id"])
        ]
        if len(matches) > 1:
            logger.error("Payment %s matches more than one PaymentIntent", reference)
            return None
        return matches[0] if matches else None

    def refund(
        self, *, reference: str, provider_reference: str | None, amount_cents: int
    ) -> str:
        """Give back the whole payment through ``POST /refunds``.

        Nothing is refunded unless the PaymentIntent is this payment's, was paid, and
        was paid for exactly what we charged. The idempotency key makes repeating the
        call safe: it returns the same refund and never a second one.
        """
        intent = self._intent_of(reference, provider_reference)
        if intent.get("status") != "succeeded":
            raise PaymentGatewayError(
                "the PaymentIntent was not paid: nothing to refund"
            )
        if intent.get("currency") != "eur" or (
            intent.get("amount_received") != amount_cents
        ):
            raise PaymentGatewayError(
                "the PaymentIntent was paid for another amount than charged"
            )
        form = {
            "payment_intent": str(provider_reference),
            "amount": str(amount_cents),
            "reason": "requested_by_customer",
            "metadata[reference]": reference,
        }
        headers = self._headers({"Idempotency-Key": f"enei-refund-{reference}"})
        try:
            refund = self._http_request(
                "POST", f"{self.base_url}/refunds", form, headers
            )
        except PaymentGatewayError as exc:
            if exc.code == "charge_already_refunded":
                raise AlreadyRefundedError(str(exc), code=exc.code) from exc
            raise
        refund_id = refund.get("id")
        if not isinstance(refund_id, str) or not _STRIPE_REFUND_ID.fullmatch(refund_id):
            raise PaymentGatewayError("stripe response is missing the refund id")
        if refund.get("status") not in _STRIPE_REFUND_OK:
            raise PaymentGatewayError(
                f"the refund was not accepted (status {refund.get('status')!r})"
            )
        return refund_id

    def cancel_payment(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus:
        """End a PaymentIntent that is still waiting, so it can no longer be paid.

        A payment approved at the very same instant cannot be cancelled: then it is
        paid, and that is what is returned (``CONFIRMED``), never ``EXPIRED``.
        """
        intent = self._intent_of(reference, provider_reference)
        outcome = _ended_intent(intent)
        if outcome is not None:
            return outcome
        headers = self._headers({"Idempotency-Key": f"enei-cancel-{reference}"})
        try:
            self._http_request(
                "POST",
                f"{self.base_url}/payment_intents/{provider_reference}/cancel",
                {"cancellation_reason": "abandoned"},
                headers,
            )
        except PaymentGatewayError as exc:
            # Stripe refuses to cancel a payment that changed state under us (approved
            # just now, or ended by Stripe). The sandbox does it with the code
            # ``payment_intent_unexpected_state`` or with only the message "already in
            # a terminal state", and the PaymentIntent can still read as waiting for a
            # moment. Whatever the refusal says, read the payment again and let that
            # decide: over (paid or cancelled) is an answer; still waiting is not, and
            # the payment then simply stays as it was until the next look.
            try:
                outcome = _ended_intent(self._intent_of(reference, provider_reference))
            except PaymentGatewayError:
                raise exc from None
            if outcome is None:
                raise
            return outcome
        return TransactionStatus.EXPIRED


class SimulatedMBWayGateway:
    """Answers like ifthenpay without contacting it, for local/dev/frontend work.

    It answers ``pending``. With a positive ``confirm_after_seconds`` it reports the
    payment as confirmed once that many seconds have elapsed since it was created,
    so the ticket/QR/email flow can run end to end without ifthenpay. With a
    positive ``expire_after_seconds`` it reports ``expired`` after that time (like
    ifthenpay's 4-minute window), because a seat is held until the provider ends the
    payment and a payment that never ends would hold it for ever. The confirming
    mode is only allowed with ``PAYMENTS_MODE=simulated``: ``live`` and ``off``
    refuse to start with it enabled.
    """

    name = "simulated"
    _REFERENCE_PREFIX = "SIM"

    def __init__(
        self,
        *,
        confirm_after_seconds: int = 0,
        expire_after_seconds: int = 0,
        now: Callable[[], float] = time.time,
    ) -> None:
        self.confirm_after_seconds = confirm_after_seconds
        self.expire_after_seconds = expire_after_seconds
        self._now = now

    def create_payment(
        self,
        *,
        reference: str,
        amount_cents: int,
        phone: str,
        email: str,
    ) -> MBWayPayment:
        # The creation instant travels inside the provider reference so the gateway
        # stays stateless and ``get_status`` can measure the elapsed time.
        created_at = int(self._now())
        return MBWayPayment(
            provider_reference=f"{self._REFERENCE_PREFIX}-{created_at}-{reference}",
            status=TransactionStatus.PENDING,
        )

    def refund(
        self, *, reference: str, provider_reference: str | None, amount_cents: int
    ) -> str:
        """Nothing moves: lets the refund flow be tried locally."""
        return f"SIMREFUND-{reference}"

    def _created_at(self, provider_reference: str | None) -> int | None:
        if not provider_reference:
            return None
        parts = provider_reference.split("-", 2)
        if len(parts) != 3 or parts[0] != self._REFERENCE_PREFIX:
            return None
        if not parts[1].isdigit():
            return None
        return int(parts[1])

    def get_status(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus:
        created_at = self._created_at(provider_reference)
        if created_at is None:
            return TransactionStatus.PENDING
        elapsed = self._now() - created_at
        expires = self.expire_after_seconds
        confirms = self.confirm_after_seconds
        if (
            confirms > 0
            and elapsed >= confirms
            and (expires <= 0 or confirms < expires)
        ):
            return TransactionStatus.CONFIRMED
        if expires > 0 and elapsed >= expires:
            return TransactionStatus.EXPIRED
        return TransactionStatus.PENDING


def get_mbway_gateway() -> MBWayGateway:
    if settings.PAYMENTS_MODE == "off":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENTS_OFF_MESSAGE,
        )
    if settings.PAYMENTS_MODE == "live" and settings.PAYMENTS_PROVIDER == "stripe":
        return StripeMBWayGateway(
            secret_key=settings.STRIPE_SECRET_KEY,
            timeout_seconds=settings.MBWAY_TIMEOUT_SECONDS,
            api_version=settings.STRIPE_API_VERSION,
        )
    if settings.PAYMENTS_MODE == "live":
        return IfThenPayMBWayGateway(
            mbway_key=settings.MBWAY_KEY,
            base_url=settings.MBWAY_BASE_URL,
            timeout_seconds=settings.MBWAY_TIMEOUT_SECONDS,
            auth_token=settings.MBWAY_AUTH_TOKEN,
        )
    # Only PAYMENTS_MODE=simulated reaches here (off raises 503, live is handled
    # above), and the settings reject a confirm delay for any other mode.
    return SimulatedMBWayGateway(
        confirm_after_seconds=settings.PAYMENTS_SIMULATED_CONFIRM_AFTER_SECONDS,
        expire_after_seconds=settings.MBWAY_PAYMENT_TIMEOUT_SECONDS,
    )
