from abc import ABC, abstractmethod


class EmailDeliveryError(RuntimeError):
    """Raised when an email cannot be delivered by a transport."""


class EmailSender(ABC):
    """Reusable contract for sending HTML emails.

    Implementations are swappable (SMTP, provider SDKs, in-memory fakes)
    without changing the code that consumes them.
    """

    @abstractmethod
    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        """Send an HTML email to a single recipient, raising on failure."""
