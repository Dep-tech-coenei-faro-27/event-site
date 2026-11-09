"""Check one proof on your own machine and print only facts that are not personal.

    python -m app.domains.students.check_file FILE.pdf [--name "Nome da conta"]

Nothing is sent anywhere and nothing is stored. The output has no name and no text of
the document: whether the signature is sound and trusted, whether it is a qualified
seal of an institution (and which), the school years and whether a validation code
is mentioned. With ``--name`` it also says whether that name is in the document, as
yes or no. Safe to run on a colleague's file and send the output.
"""

import argparse
import re
import sys
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

from app.domains.students import document
from app.domains.students.institutions import match_institution

VALIDATION_CODE = re.compile(r"c[oó]digo\s+de\s+(valida|verifica|autentica)", re.I)
ORGANIZATION_OID = "2.5.4.10"
GIVEN_NAME_OID = "2.5.4.42"


def describe_signature(embedded, context) -> list[str]:
    cert = embedded.signer_cert
    status = validate_pdf_signature(embedded, signer_validation_context=context)
    seal = document._is_qualified_seal(cert)
    person = document._subject_attribute(cert, GIVEN_NAME_OID) is not None
    lines = [
        f"  integra e válida: {status.intact and status.valid}",
        f"  cadeia confiável (lista da UE): {status.trusted}",
        f"  cobre o ficheiro todo: {document._entire_file(status)}",
        f"  emissor: {cert.issuer.native.get('common_name', '?')}",
        f"  certificado válido de {cert.not_valid_before:%Y-%m-%d} "
        f"a {cert.not_valid_after:%Y-%m-%d}",
        f"  selo eletrónico qualificado: {seal}",
        f"  certificado de pessoa (não é selo): {person}",
    ]
    if seal and not person:
        organization = document._subject_attribute(cert, ORGANIZATION_OID)
        matched = match_institution(organization or "")
        lines += [
            f"  entidade: {organization}",
            f"  NIPC: {document._signer_nipc(cert)}",
            f"  instituição reconhecida: {matched.key if matched else 'não'}",
        ]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.domains.students.check_file")
    parser.add_argument("file", type=Path)
    parser.add_argument("--name")
    args = parser.parse_args(argv)

    data = args.file.read_bytes()
    print(f"ficheiro: {len(data)} bytes, PDF: {data.startswith(b'%PDF-')}")
    if not data.startswith(b"%PDF-"):
        print("não é um PDF (imagens vão sempre para revisão manual)")
        return 0

    context = ValidationContext(
        trust_roots=document.load_trust_anchors(),
        allow_fetching=False,
        revocation_mode="soft-fail",
    )
    try:
        signatures = list(
            PdfFileReader(BytesIO(data), strict=False).embedded_signatures
        )
    except Exception:
        print("PDF ilegível")
        return 1
    print(f"assinaturas: {len(signatures)}")
    for number, embedded in enumerate(signatures, start=1):
        print(f"assinatura {number}:")
        try:
            print("\n".join(describe_signature(embedded, context)))
        except Exception:
            print("  não foi possível ler esta assinatura")

    try:
        text = document._extract_text(data)
    except Exception:
        print("texto: ilegível")
        return 0
    years = sorted(
        {f"{first}/{second}" for first, second in document.SCHOOL_YEAR.findall(text)}
    )
    start = document.current_school_year_start(datetime.now(UTC))
    print(f"texto extraído: {bool(text.strip())}")
    print(f"anos letivos no texto: {years or 'nenhum'} (atual: {start}/{start + 1})")
    print(f"menciona código de validação: {bool(VALIDATION_CODE.search(text))}")
    if args.name:
        found = document.name_in_text(args.name, text)
        print(f"o nome indicado está no documento: {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
