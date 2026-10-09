import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from urllib import error, parse, request

from app.core.config import settings
from app.domains.payments.models import TransactionStatus

logger = logging.getLogger(__name__)


class PaymentGatewayError(RuntimeError):
    """Raised when the payment provider is unreachable or answers badly."""


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


_STATUS_MAP = {
    "paid": TransactionStatus.CONFIRMED,
    "success": TransactionStatus.CONFIRMED,
    "confirmed": TransactionStatus.CONFIRMED,
    "failed": TransactionStatus.FAILED,
    "error": TransactionStatus.FAILED,
    "canceled": TransactionStatus.FAILED,
    "cancelled": TransactionStatus.FAILED,
    "declined": TransactionStatus.FAILED,
    "expired": TransactionStatus.EXPIRED,
    "pending": TransactionStatus.PENDING,
}


def _normalize_status(raw: object) -> TransactionStatus:
    if isinstance(raw, str):
        return _STATUS_MAP.get(raw.strip().lower(), TransactionStatus.PENDING)
    return TransactionStatus.PENDING


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
        transaction_id = data.get("transactionId") or data.get("TransactionId")
        if not transaction_id:
            raise PaymentGatewayError("gateway response is missing transactionId")
        return MBWayPayment(
            provider_reference=str(transaction_id),
            status=_normalize_status(data.get("status")),
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
        return _normalize_status(data.get("status"))


class SimulatedMBWayGateway:
    """Answers like ifthenpay without contacting it, for local/dev/frontend work."""

    name = "simulated"

    def create_payment(
        self,
        *,
        reference: str,
        amount_cents: int,
        phone: str,
        email: str,
    ) -> MBWayPayment:
        return MBWayPayment(
            provider_reference=f"SIM-{reference}",
            status=TransactionStatus.PENDING,
        )

    def get_status(
        self, *, reference: str, provider_reference: str | None
    ) -> TransactionStatus:
        return TransactionStatus.PENDING


def get_mbway_gateway() -> MBWayGateway:
    if not settings.MBWAY_KEY:
        return SimulatedMBWayGateway()
    return IfThenPayMBWayGateway(
        mbway_key=settings.MBWAY_KEY,
        base_url=settings.MBWAY_BASE_URL,
        timeout_seconds=settings.MBWAY_TIMEOUT_SECONDS,
        auth_token=settings.MBWAY_AUTH_TOKEN,
    )
