import logging
import re
from html import unescape

from app.core.email.base import EmailSender

logger = logging.getLogger(__name__)

LINK_PATTERN = re.compile(r'href="([^"]+)"')


class ConsoleEmailSender(EmailSender):
    """EmailSender that only logs the email, for local runs without a mail server."""

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        links = dict.fromkeys(
            unescape(link) for link in LINK_PATTERN.findall(html_body)
        )
        logger.info("Email to %s: %s %s", to_email, subject, list(links))
