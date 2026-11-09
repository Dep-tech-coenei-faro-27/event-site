"""Review the proofs of enrolment that were not approved on their own.

    python -m app.domains.students.review list
    python -m app.domains.students.review show ID
    python -m app.domains.students.review export ID DESTINATION
    python -m app.domains.students.review approve ID [--institution KEY]
    python -m app.domains.students.review reject ID

``show`` prints only facts about the signature, never the name of the student.
``export`` copies the file so the reviewer can open it and records that it was seen.
A proof signed with a tax number (NIPC) not yet known needs ``--institution`` when
approved: the number is then remembered for that institution.
"""

import argparse
import getpass
import json
import shutil
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.domains.students.institutions import institution_by_key, match_institution
from app.domains.students.models import ProofStatus, StudentProof
from app.domains.students.service import (
    FileAlreadyUsedError,
    NipcConflictError,
    ProofAlreadyDecidedError,
    approve_proof,
    proof_path,
    record_view,
    reject_proof,
    waiting_proofs,
)

REASON_TEXT = {
    "no_signature": "o PDF não tem assinatura",
    "not_a_pdf": "imagem: não tem assinatura",
    "signature_not_intact": "assinatura inválida ou documento alterado",
    "signature_not_trusted": "assinatura não confiável",
    "not_a_qualified_seal": "assinatura que não é um selo qualificado",
    "unreadable_pdf": "PDF ilegível",
    "unreadable_text": "texto do PDF ilegível",
    "name_not_found": "o nome da conta não está no documento",
    "school_year_not_current": "o ano letivo atual não está no documento",
    "file_reused": "o mesmo ficheiro foi usado por outra conta",
    "new_nipc": "NIPC novo (instituição por confirmar)",
    "no_nipc_in_seal": "o selo não traz NIPC",
}


def describe(proof: StudentProof) -> dict:
    """The non-personal facts about a proof."""
    report = dict(proof.report or {})
    suggested = match_institution(report.get("signer_organization") or "")
    return {
        "id": proof.id,
        "status": str(proof.status),
        "file_kind": proof.file_kind,
        "submitted_at": proof.submitted_at.isoformat(),
        "file_available": proof.file_name is not None,
        "suggested_institution": suggested.key if suggested else None,
        **report,
    }


def _show(proof: StudentProof) -> None:
    data = describe(proof)
    reasons = [REASON_TEXT.get(code, code) for code in data.get("reasons", [])]
    data["reasons"] = reasons
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _list(db) -> int:
    for proof in waiting_proofs(db):
        reasons = ", ".join(
            REASON_TEXT.get(code, code)
            for code in (proof.report or {}).get("reasons", [])
        )
        print(
            f"{proof.id}\t{proof.submitted_at:%Y-%m-%d %H:%M}\t"
            f"{proof.file_kind}\t{reasons}"
        )
    return 0


def _get(db, proof_id: int) -> StudentProof | None:
    proof = db.get(StudentProof, proof_id)
    if proof is None:
        print("Pedido não encontrado.", file=sys.stderr)
    return proof


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.domains.students.review")
    parser.add_argument("--reviewer", default=getpass.getuser())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    for name in ("show", "export", "approve", "reject"):
        command = commands.add_parser(name)
        command.add_argument("id", type=int)
        if name == "export":
            command.add_argument("destination", type=Path)
        if name == "approve":
            command.add_argument("--institution")
    args = parser.parse_args(argv)
    actor = args.reviewer[:64]

    with SessionLocal() as db:
        if args.command == "list":
            return _list(db)
        proof = _get(db, args.id)
        if proof is None:
            return 1
        if args.command == "show":
            _show(proof)
            return 0
        if args.command == "export":
            if proof.status != ProofStatus.SUBMITTED or not proof.file_name:
                print("O ficheiro já não existe.", file=sys.stderr)
                return 1
            shutil.copyfile(proof_path(proof.file_name), args.destination)
            record_view(db, proof, actor)
            return 0
        if args.command == "approve":
            report = proof.report or {}
            if args.institution and institution_by_key(args.institution) is None:
                print("Instituição desconhecida.", file=sys.stderr)
                return 1
            if report.get("new_nipc") and not args.institution:
                print(
                    "NIPC novo: indique a instituição com --institution CHAVE "
                    f"(sugestão: {describe(proof)['suggested_institution']}).",
                    file=sys.stderr,
                )
                return 1
            try:
                approve_proof(db, proof.id, actor, institution=args.institution)
            except (
                ProofAlreadyDecidedError,
                FileAlreadyUsedError,
                NipcConflictError,
            ) as error:
                print(
                    f"Não foi possível aprovar: {type(error).__name__}.",
                    file=sys.stderr,
                )
                return 1
            return 0
        try:
            reject_proof(db, proof.id, actor)
        except ProofAlreadyDecidedError:
            print("O pedido já foi decidido.", file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(run())
