import logging
import re

REDACTED = "REDACTED"
SECRET_QUERY_PARAMS = ("key", "apk")
_SECRET_QUERY_RE = re.compile(r"([?&](?:key|apk)=)[^&\s]*", re.IGNORECASE)
_ACCESS_LOG_ARGS = 5


class RedactCallbackSecrets(logging.Filter):
    """Remove the ifthenpay anti-phishing key from uvicorn's access log.

    The payment callback is a GET whose secret travels in the query string, so
    uvicorn logs it by default. nginx already masks the callback path; this
    covers the container log, where that key must never appear.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not (isinstance(args, tuple) and len(args) == _ACCESS_LOG_ARGS):
            return True

        path = args[2]
        if not isinstance(path, str):
            return True
        if not any(f"{param}=" in path for param in SECRET_QUERY_PARAMS):
            return True

        record.args = (
            args[0],
            args[1],
            _SECRET_QUERY_RE.sub(rf"\1{REDACTED}", path),
            args[3],
            args[4],
        )
        return True


def install_access_log_redaction() -> None:
    """Attach the redaction filter to the uvicorn access logger once."""
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactCallbackSecrets) for f in access_logger.filters):
        access_logger.addFilter(RedactCallbackSecrets())
