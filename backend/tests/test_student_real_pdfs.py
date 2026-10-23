"""Real proofs of enrolment, kept outside the repository (they hold personal data).

Point STUDENT_REAL_PROOFS_DIR at a folder with pairs ``name.pdf`` + ``name.json``:

    {"account_name": "Ana Silva", "now": "2026-10-22",
     "qualified_seal": true, "signature_intact": true, "signer_nipc": "501413197"}

``account_name`` and ``now`` are required; every other key is compared with the
findings of the document (the same keys as ``DocumentFindings``). Include documents of
institutions with a qualified seal and of institutions with a validation code, which
must never be a qualified seal. Without the folder these tests are skipped.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.core.config import settings
from app.domains.students.document import inspect_pdf

FOLDER = os.environ.get("STUDENT_REAL_PROOFS_DIR")
CASES = sorted(Path(FOLDER).glob("*.pdf")) if FOLDER else []


@pytest.mark.skipif(not CASES, reason="STUDENT_REAL_PROOFS_DIR is not set")
@pytest.mark.parametrize("pdf", CASES, ids=lambda path: path.stem)
def test_real_proof(pdf, monkeypatch):
    monkeypatch.setattr(settings, "STUDENT_TRUST_ANCHORS_FILE", None)
    expected = json.loads(pdf.with_suffix(".json").read_text())
    now = datetime.fromisoformat(expected.pop("now")).replace(tzinfo=UTC)

    findings = inspect_pdf(pdf.read_bytes(), expected.pop("account_name"), now)

    for key, value in expected.items():
        assert getattr(findings, key) == value, key
