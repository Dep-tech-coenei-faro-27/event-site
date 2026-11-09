# ruff: noqa: E501  (linhas de shell e JSON dentro de strings)
"""Teste do script `scripts/smoke-test.sh`, com um `curl` de brincar.

Nada sai da máquina. Garante que o script falha quando o backend responde mal e,
sobretudo, que **só lê**: nunca regista, entra nem compra, porque no servidor um
registo mandaria um email verdadeiro.
"""

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SMOKE = Path(__file__).resolve().parents[2] / "scripts" / "smoke-test.sh"

pytestmark = pytest.mark.skipif(shutil.which("sh") is None, reason="precisa de sh")

FAKE_CURL = """#!/bin/sh
for last; do :; done
echo "$*" | tr '\n' ' ' >> "$FAKE_LOG"; echo >> "$FAKE_LOG"
with_code=0
for arg; do [ "$arg" = "-w" ] && with_code=1; done
path="${last#http://fake}"
code=200
body='{"status":"OK"}'
case "$path" in
  /api/payment/tiers)
    body='[{"tier":"acesso","sale_open":false},{"tier":"refeicoes","sale_open":false},{"tier":"completo","sale_open":false},{"tier":"geral","sale_open":false}]' ;;
  /api/payment/callback) code=403 ;;
  /api/payment/initiate|/api/users/me) code=401 ;;
esac
# FAKE_BREAK="caminho=código" muda a resposta desse caminho; FAKE_BODY muda o corpo das modalidades
case "$FAKE_BREAK" in
  "$path"=*) code="${FAKE_BREAK#*=}" ;;
esac
[ "$path" = "/api/payment/tiers" ] && [ -n "$FAKE_BODY" ] && body="$FAKE_BODY"
if [ "$with_code" = 1 ]; then printf '%s\\n%s' "$body" "$code"; else printf '%s' "$body"; fi
"""


@pytest.fixture
def run(tmp_path):
    curl = tmp_path / "curl"
    curl.write_text(FAKE_CURL, encoding="utf-8", newline="\n")
    curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "calls.log"

    def _run(**env):
        result = subprocess.run(
            ["sh", str(SMOKE)],
            capture_output=True,
            text=True,
            env={
                "PATH": f"{tmp_path}:/usr/bin:/bin",
                "SMOKE_BASE": "http://fake",
                "FAKE_LOG": str(log),
                "FAKE_BREAK": "",
                "FAKE_BODY": "",
                **env,
            },
        )
        calls = log.read_text(encoding="utf-8") if log.exists() else ""
        return result, calls

    return _run


def test_everything_answering_as_expected_passes(run):
    result, _ = run()

    assert result.returncode == 0, result.stdout
    assert "Teste de fumo: tudo OK." in result.stdout
    assert "FALHOU" not in result.stdout


@pytest.mark.parametrize(
    "broken",
    [
        "/api/health=500",
        "/api/health/ready=503",
        "/api/payment/tiers=500",
        "/api/payment/callback=200",  # aceitava um callback sem chave
        "/api/payment/initiate=200",  # deixava comprar sem sessão
        "/api/payment/initiate=503",
        "/api/users/me=200",
    ],
)
def test_an_unexpected_answer_fails_the_smoke_test(run, broken):
    result, _ = run(FAKE_BREAK=broken)

    assert result.returncode == 1
    assert "FALHOU" in result.stdout


def test_fewer_than_four_modalities_fails(run):
    result, _ = run(FAKE_BODY='[{"tier":"geral","sale_open":false}]')

    assert result.returncode == 1
    assert "modalidades" in result.stdout


def test_a_tiers_answer_without_the_expected_fields_fails(run):
    result, _ = run(FAKE_BODY='{"detail":"surprise"}')

    assert result.returncode == 1


def test_the_smoke_test_never_registers_logs_in_or_buys(run):
    """It must only read: a registration would send a real email on the server."""
    _, calls = run()

    for forbidden in ("register", "login", "verify", "forgot", "password", "logout"):
        assert forbidden not in calls
    posts = [line for line in calls.splitlines() if "-X POST" in line]
    assert len(posts) == 1 and "/api/payment/initiate" in posts[0]
    assert "Cookie" not in calls and " -b " not in calls  # never signed in
    assert "/auth/" not in SMOKE.read_text(encoding="utf-8")


def test_the_curl_command_can_be_replaced_to_run_inside_the_container(tmp_path):
    runner = tmp_path / "in-container"
    runner.write_text(
        '#!/bin/sh\necho "$*" >> "$FAKE_LOG"\nexec curl "$@"\n', newline="\n"
    )
    runner.chmod(runner.stat().st_mode | stat.S_IXUSR)
    curl = tmp_path / "curl"
    curl.write_text(FAKE_CURL, encoding="utf-8", newline="\n")
    curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "calls.log"

    result = subprocess.run(
        ["sh", str(SMOKE)],
        capture_output=True,
        text=True,
        env={
            "PATH": f"{tmp_path}:/usr/bin:/bin",
            "SMOKE_BASE": "http://fake",
            "SMOKE_CURL": f"{runner} --some-flag",
            "FAKE_LOG": str(log),
            "FAKE_BREAK": "",
            "FAKE_BODY": "",
        },
    )

    assert result.returncode == 0, result.stdout
    assert "--some-flag" in log.read_text(encoding="utf-8")
