"""Assinala migrations que podem partir o código da versão anterior.

No deploy, as migrations correm antes de o código novo entrar (ver cd.yml), por isso
durante uns segundos o código antigo corre sobre o esquema já migrado. Acrescentar
tabelas ou colunas é seguro. Remover ou renomear (ou apertar o tipo de uma coluna) tem
de ser feito em duas entregas: primeiro o código deixa de usar a coluna, depois a
migration remove-a.

Uso:
    python scripts/check_migrations.py origin/dev   só as migrations novas ou alteradas
    python scripts/check_migrations.py --all        todas (para ver como a regra funciona)

Quando a alteração for mesmo intencional, acrescenta na linha da operação, ou na linha
de cima, o comentário "# destructive: ok - motivo".
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

VERSIONS = "backend/alembic/versions"
MARKER = "destructive: ok"
ALWAYS = {"drop_table", "drop_column", "rename_table"}
RAW_SQL = re.compile(r"\b(DROP|RENAME|TRUNCATE|DELETE\s+FROM)\b", re.IGNORECASE)


def _is_false(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _reason(call: ast.Call, name: str, source: str) -> str | None:
    if name in ALWAYS:
        return f"op.{name}() remove ou renomeia"
    if name == "alter_column":
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        if "new_column_name" in keywords:
            return "op.alter_column() renomeia uma coluna"
        if "type_" in keywords:
            return "op.alter_column() muda o tipo de uma coluna"
        if "nullable" in keywords and _is_false(keywords["nullable"]):
            return "op.alter_column() torna uma coluna obrigatória"
    if name == "execute":
        text = ast.get_source_segment(source, call) or ""
        if RAW_SQL.search(text):
            return "op.execute() com SQL que remove ou apaga"
    return None


def violations(source: str) -> list[tuple[int, str]]:
    """(linha, motivo) das operações arriscadas dentro de upgrade()."""
    tree = ast.parse(source)
    lines = source.splitlines()
    upgrade = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "upgrade"
        ),
        None,
    )
    if upgrade is None:
        return []

    found = []
    for node in ast.walk(upgrade):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
        ):
            continue
        reason = _reason(node, node.func.attr, source)
        if reason is None:
            continue
        here = lines[node.lineno - 1]
        above = lines[node.lineno - 2] if node.lineno > 1 else ""
        if MARKER in here or MARKER in above:
            continue
        found.append((node.lineno, reason))
    return sorted(found)


def changed_files(base: str) -> list[Path]:
    output = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=AM",
            f"{base}...HEAD",
            "--",
            VERSIONS,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [Path(line) for line in output.splitlines() if line.endswith(".py")]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    if argv[1] == "--all":
        files = sorted(Path(VERSIONS).glob("*.py"))
    else:
        files = changed_files(argv[1])

    problems = 0
    for path in files:
        for line, reason in violations(path.read_text(encoding="utf-8")):
            problems += 1
            print(f"{path}:{line}: {reason}")

    if problems:
        print(
            "\nDurante o deploy o código antigo corre uns segundos sobre o esquema "
            "novo. Faz a alteração em duas entregas (primeiro o código deixa de usar "
            "a coluna, depois a migration remove-a) ou, se for intencional, "
            'acrescenta na linha o comentário "# destructive: ok - motivo".'
        )
        return 1
    print(f"Migrations verificadas: {len(files)}, sem operações destrutivas.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
