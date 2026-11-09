"""Procura vulnerabilidades conhecidas nas dependências que vão para produção.

Uso:
    python3 scripts/audit_deps.py backend    pip-audit sobre o uv.lock (sem o grupo dev)
    python3 scripts/audit_deps.py frontend   npm audit --omit=dev, nível high ou acima

Falha (código 1) se encontrar uma vulnerabilidade que não esteja em
audit-exceptions.toml, ou se esse ficheiro tiver uma exceção sem motivo, sem data de
revisão, ou com a data de revisão já passada. Cada exceção diz o ecossistema, o
identificador (GHSA, CVE ou PYSEC), o pacote, o motivo e até quando vale:

    [[exception]]
    ecosystem = "python"          # ou "npm"
    id = "GHSA-xxxx-xxxx-xxxx"
    package = "nome-do-pacote"
    reason = "Porque é que não nos afeta, ou porque ainda não há correção."
    review_by = 2026-12-31

Precisa de uv (backend) ou npm (frontend); só usa a biblioteca padrão do Python.
"""

import datetime
import json
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCEPTIONS = ROOT / "audit-exceptions.toml"
PIP_AUDIT = "pip-audit==2.10.1"
NPM_LEVELS = {"high", "critical"}
REQUIRED = ("ecosystem", "id", "package", "reason", "review_by")


@dataclass(frozen=True)
class Finding:
    package: str
    version: str
    ids: frozenset[str]
    detail: str

    def label(self) -> str:
        return f"{self.package} {self.version}: {', '.join(sorted(self.ids))}"


def load_exceptions(
    text: str, ecosystem: str, today: datetime.date
) -> tuple[list[dict], list[str]]:
    """Exceções válidas deste ecossistema e os problemas no ficheiro (todos)."""
    entries = tomllib.loads(text).get("exception", [])
    valid, problems = [], []
    for n, entry in enumerate(entries, start=1):
        where = f"exceção {n} ({entry.get('id', 'sem id')})"
        missing = [k for k in REQUIRED if not str(entry.get(k, "")).strip()]
        if missing:
            problems.append(f"{where}: falta {', '.join(missing)}")
            continue
        if entry["ecosystem"] not in ("python", "npm"):
            problems.append(f"{where}: ecosystem tem de ser python ou npm")
            continue
        if not isinstance(entry["review_by"], datetime.date):
            problems.append(f"{where}: review_by tem de ser uma data (AAAA-MM-DD)")
            continue
        if entry["review_by"] < today:
            problems.append(
                f"{where}: a data de revisão ({entry['review_by']}) já passou; "
                "volta a ver se já há correção e renova a data ou remove a exceção"
            )
            continue
        if entry["ecosystem"] == ecosystem:
            valid.append(entry)
    return valid, problems


def is_excepted(finding: Finding, exceptions: list[dict]) -> bool:
    return any(
        e["package"].lower() == finding.package.lower() and e["id"] in finding.ids
        for e in exceptions
    )


def pip_audit_findings(report: dict) -> list[Finding]:
    return [
        Finding(
            package=dep["name"],
            version=dep["version"],
            ids=frozenset([v["id"], *v.get("aliases", [])]),
            detail=f"corrigido em {', '.join(v['fix_versions']) or 'nenhuma versão'}",
        )
        for dep in report.get("dependencies", [])
        for v in dep.get("vulns", [])
    ]


def npm_audit_findings(report: dict) -> list[Finding]:
    """As vulnerabilidades high ou critical, uma por pacote e aviso."""
    found = {}
    for vuln in report.get("vulnerabilities", {}).values():
        for via in vuln.get("via", []):
            # Um texto em "via" só aponta para outro pacote, que tem a sua entrada.
            if not isinstance(via, dict) or via.get("severity") not in NPM_LEVELS:
                continue
            advisory = via.get("url", "").rstrip("/").rsplit("/", 1)[-1]
            key = (via["name"], advisory)
            found[key] = Finding(
                package=via["name"],
                version=via.get("range", ""),
                ids=frozenset([advisory]),
                detail=f"{via['severity']}: {via.get('title', '')}",
            )
    return list(found.values())


def run_pip_audit() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        requirements = Path(tmp) / "requirements.txt"
        subprocess.run(
            [
                "uv", "export", "--frozen", "--no-dev", "--no-emit-project",
                "--format", "requirements-txt", "--quiet", "-o", str(requirements),
            ],
            cwd=ROOT / "backend",
            check=True,
        )  # fmt: skip
        # Sai com 1 quando encontra alguma coisa; o relatório JSON diz o quê.
        result = subprocess.run(
            [
                "uv", "tool", "run", PIP_AUDIT, "--disable-pip", "--progress-spinner",
                "off", "-f", "json", "-r", str(requirements),
            ],
            capture_output=True,
            text=True,
        )  # fmt: skip
    return _parse(result, "pip-audit")


def run_npm_audit() -> dict:
    result = subprocess.run(
        ["npm", "audit", "--omit=dev", "--json"],
        cwd=ROOT / "frontend",
        capture_output=True,
        text=True,
    )
    return _parse(result, "npm audit")


def _parse(result: subprocess.CompletedProcess, tool: str) -> dict:
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = None
    # O npm devolve {"error": ...} quando não chega ao registo.
    if not isinstance(report, dict) or "error" in report:
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(
            f"{tool} não devolveu um relatório (código {result.returncode})"
        )
    return report


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ("backend", "frontend"):
        print(__doc__)
        return 2
    if argv[0] == "backend":
        ecosystem, findings = "python", pip_audit_findings(run_pip_audit())
    else:
        ecosystem, findings = "npm", npm_audit_findings(run_npm_audit())

    text = EXCEPTIONS.read_text() if EXCEPTIONS.exists() else ""
    exceptions, problems = load_exceptions(text, ecosystem, datetime.date.today())
    excepted = [f for f in findings if is_excepted(f, exceptions)]
    blocking = [f for f in findings if f not in excepted]

    for f in excepted:
        print(f"exceção  {f.label()} ({f.detail})")
    for f in blocking:
        print(f"FALHOU   {f.label()} ({f.detail})")
    for p in problems:
        print(f"FALHOU   {EXCEPTIONS.name}: {p}")
    if blocking or problems:
        print(
            "\nAtualiza o pacote (uv lock --upgrade-package NOME ou npm audit fix) ou, "
            f"se não for possível, acrescenta uma exceção em {EXCEPTIONS.name} com "
            "motivo e data de revisão (ver docs/deploy.md)."
        )
        return 1
    print(f"Sem vulnerabilidades por resolver ({len(excepted)} exceções em uso).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
