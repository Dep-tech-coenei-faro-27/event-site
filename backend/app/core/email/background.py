import logging
import queue
import threading

from app.core.email.base import EmailSender

logger = logging.getLogger(__name__)


class BackgroundEmailSender(EmailSender):
    """EmailSender that delivers through another sender on its own threads.

    ``send_html`` returns at once, so a slow or unreachable mail server cannot
    hold up requests. When the queue is full the email is dropped and logged.
    """

    def __init__(
        self, sender: EmailSender, workers: int = 4, max_queue: int = 200
    ) -> None:
        self.sender = sender
        self._queue: queue.Queue[tuple[str, str, str]] = queue.Queue(maxsize=max_queue)
        for _ in range(workers):
            threading.Thread(target=self._work, daemon=True).start()

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        try:
            self._queue.put_nowait((to_email, subject, html_body))
        except queue.Full:
            logger.warning("Email queue is full, dropping email: %s", subject)

    def _work(self) -> None:
        while True:
            to_email, subject, html_body = self._queue.get()
            try:
                self.sender.send_html(to_email, subject, html_body)
            except Exception as exc:
                logger.warning("Failed to send email: %s", exc)
            finally:
                self._queue.task_done()
