"""Rebuild the snapshot of the EU qualified trust services.

    python -m app.domains.students.trust_list [--output FILE]

Reads the EU list of trusted lists (LOTL), then each national list, and keeps the
certificates of the services that issue qualified certificates (CA/QC) and are
granted. The result is a PEM file committed to the repository, so the backend never
needs the network to check a proof and the change can be reviewed in the pull request.

The signatures of the lists are NOT verified here: the files come over https from
the Commission and the national supervisory bodies, and what changes shows up in the
diff of the snapshot. Check that diff before merging it.
"""

import argparse
import base64
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from asn1crypto import pem
from asn1crypto import x509 as asn1_x509
from lxml import etree

from app.domains.students.document import DEFAULT_TRUST_ANCHORS

LOTL_URL = "https://ec.europa.eu/tools/lotl/eu-lotl.xml"
TSL_MIME = "application/vnd.etsi.tsl+xml"
SERVICE_CA_QC = "http://uri.etsi.org/TrstSvc/Svctype/CA/QC"
STATUS_GRANTED = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"
NAMESPACE = {"t": "http://uri.etsi.org/02231/v2#"}
MAX_BYTES = 32 * 1024 * 1024
TIMEOUT_SECONDS = 30
ATTEMPTS = 3


def fetch(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("only https lists are read")
    request = urllib.request.Request(url, headers={"User-Agent": "event-site/1"})
    for attempt in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(  # noqa: S310
                request, timeout=TIMEOUT_SECONDS
            ) as response:
                data = response.read(MAX_BYTES + 1)
            break
        except OSError:
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(2)
    if len(data) > MAX_BYTES:
        raise ValueError("a trusted list is too large")
    return data


def parse(data: bytes) -> etree._Element:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
    return etree.fromstring(data, parser)


def list_locations(lotl: etree._Element) -> list[str]:
    locations = []
    for pointer in lotl.iterfind(".//t:OtherTSLPointer", NAMESPACE):
        mime = pointer.findtext(".//{*}MimeType")
        location = pointer.findtext("t:TSLLocation", namespaces=NAMESPACE)
        if mime == TSL_MIME and location:
            locations.append(location.strip())
    return sorted(set(locations))


def qualified_ca_certificates(national: etree._Element) -> list[bytes]:
    found = []
    for service in national.iterfind(".//t:ServiceInformation", NAMESPACE):
        kind = service.findtext("t:ServiceTypeIdentifier", namespaces=NAMESPACE)
        state = service.findtext("t:ServiceStatus", namespaces=NAMESPACE)
        if kind != SERVICE_CA_QC or state != STATUS_GRANTED:
            continue
        for encoded in service.iterfind(".//t:X509Certificate", NAMESPACE):
            try:
                der = base64.b64decode("".join((encoded.text or "").split()))
                asn1_x509.Certificate.load(der).native  # noqa: B018 - checks it parses
            except Exception:
                continue
            found.append(der)
    return found


def build_snapshot(log=print) -> bytes:
    lotl = parse(fetch(LOTL_URL))
    certificates: dict[bytes, None] = {}
    for location in list_locations(lotl):
        try:
            national = parse(fetch(location))
        except Exception as error:
            log(f"skipped {location}: {type(error).__name__}")
            continue
        for der in qualified_ca_certificates(national):
            certificates[der] = None
    header = (
        "# Certificates of the granted CA/QC services of the EU trusted lists.\n"
        f"# Built by app.domains.students.trust_list on {datetime.now(UTC):%Y-%m-%d}.\n"
        f"# {len(certificates)} certificates.\n"
    )
    body = b"".join(pem.armor("CERTIFICATE", der) for der in sorted(certificates))
    return header.encode() + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.domains.students.trust_list")
    parser.add_argument("--output", type=Path, default=DEFAULT_TRUST_ANCHORS)
    args = parser.parse_args(argv)
    snapshot = build_snapshot(log=lambda line: print(line, file=sys.stderr))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(snapshot)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
