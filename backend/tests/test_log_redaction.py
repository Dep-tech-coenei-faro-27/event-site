import logging

import app.main  # noqa: F401  (installs the access-log filter)
from app.core.log_redaction import RedactCallbackSecrets


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1", "GET", path, "1.1", 200),
        exc_info=None,
    )


def test_callback_key_is_redacted_from_the_access_log():
    record = _access_record(
        "/api/payment/callback?orderId=ENEI-ABCDEF&amount=50.00&key=SUPERSECRET"
    )

    assert RedactCallbackSecrets().filter(record) is True

    logged = record.args[2]
    assert "SUPERSECRET" not in logged
    assert "key=REDACTED" in logged
    assert "orderId=ENEI-ABCDEF" in logged
    assert "amount=50.00" in logged


def test_callback_apk_is_redacted_from_the_access_log():
    record = _access_record("/api/payment/callback?apk=SUPERSECRET&oid=ENEI-ABCDEF")

    RedactCallbackSecrets().filter(record)

    assert "SUPERSECRET" not in record.args[2]
    assert "apk=REDACTED" in record.args[2]


def test_unrelated_paths_are_left_untouched():
    record = _access_record("/api/payment/transactions/ENEI-ABCDEF")
    original = record.args

    assert RedactCallbackSecrets().filter(record) is True

    assert record.args == original


def test_key_substring_is_not_redacted():
    record = _access_record("/api/health?monkey=banana")

    RedactCallbackSecrets().filter(record)

    assert record.args[2] == "/api/health?monkey=banana"


def test_uvicorn_access_logger_has_the_redaction_filter():
    filters = logging.getLogger("uvicorn.access").filters

    assert any(isinstance(f, RedactCallbackSecrets) for f in filters)
