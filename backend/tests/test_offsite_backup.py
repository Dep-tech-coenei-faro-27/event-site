"""Testes dos scripts de cópia externa, com `rclone` e `curl` de brincar.

Nada sai da máquina: os dois comandos são scripts que só registam o que receberam.
"""

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
OFFSITE = SCRIPTS / "offsite-backup.sh"
CHECK = SCRIPTS / "check-offsite-backup.sh"

pytestmark = pytest.mark.skipif(shutil.which("sh") is None, reason="precisa de sh")

FAKE_RCLONE = """#!/bin/sh
echo "rclone $*" >> "$FAKE_LOG"
case "$1" in
  listremotes) printf '%s\\n' "$FAKE_REMOTES" ;;
  copy) [ "${FAKE_RCLONE_FAIL:-}" = "copy" ] && exit 5 ;;
esac
exit 0
"""

FAKE_CURL = """#!/bin/sh
for last; do :; done
echo "curl $last" >> "$FAKE_LOG"
exit 0
"""

FAKE_BACKUP = """#!/bin/sh
mkdir -p "$1"
echo dados > "$1/db-20261014-030000.dump"
"""


def _executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def sandbox(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(bin_dir / "rclone", FAKE_RCLONE)
    _executable(bin_dir / "curl", FAKE_CURL)

    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    _executable(project / "scripts" / "backup.sh", FAKE_BACKUP)

    log = tmp_path / "calls.log"
    log.write_text("", encoding="utf-8")
    backups = tmp_path / "backups"

    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "FAKE_LOG": str(log),
        "FAKE_REMOTES": "enei-cifrado:  crypt\nenei-claro:  drive",
        "PROJECT_DIR": str(project),
        "BACKUP_DIR": str(backups),
    }
    for name in ("BACKUP_REMOTE", "BACKUP_ALLOW_PLAINTEXT", "BACKUP_HEARTBEAT_URL"):
        env.pop(name, None)

    def run(script=OFFSITE, **extra):
        return subprocess.run(
            ["sh", str(script)],
            env={**env, **extra},
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )

    return run, log, backups


def _calls(log: Path) -> list[str]:
    return [line for line in log.read_text(encoding="utf-8").splitlines() if line]


def test_refuses_a_remote_that_is_not_encrypted(sandbox):
    run, log, backups = sandbox

    result = run(BACKUP_REMOTE="enei-claro:enei")

    assert result.returncode == 1
    assert "crypt" in result.stderr
    assert not any(call.startswith("rclone copy") for call in _calls(log))
    assert not backups.exists()


def test_refuses_a_plain_local_path_as_destination(sandbox):
    run, log, _ = sandbox

    result = run(BACKUP_REMOTE="/tmp/copias")

    assert result.returncode == 1
    assert not any(call.startswith("rclone copy") for call in _calls(log))


def test_encrypted_remote_copies_and_records_the_success(sandbox):
    run, log, backups = sandbox

    result = run(BACKUP_REMOTE="enei-cifrado:enei")

    assert result.returncode == 0, result.stderr
    calls = _calls(log)
    assert any(
        call.startswith("rclone copy") and "enei-cifrado:enei" in call for call in calls
    )
    assert any(
        call.startswith("rclone delete") and "--min-age 30d" in call for call in calls
    )
    assert (backups / "offsite-last-success").read_text().strip().isdigit()


def test_plaintext_destination_needs_an_explicit_override(sandbox):
    run, log, _ = sandbox

    result = run(BACKUP_REMOTE="enei-claro:enei", BACKUP_ALLOW_PLAINTEXT="1")

    assert result.returncode == 0, result.stderr
    assert any(call.startswith("rclone copy") for call in _calls(log))


def test_heartbeat_pings_start_and_success(sandbox):
    run, log, _ = sandbox

    result = run(
        BACKUP_REMOTE="enei-cifrado:enei", BACKUP_HEARTBEAT_URL="https://hc.example/abc"
    )

    assert result.returncode == 0, result.stderr
    pings = [call for call in _calls(log) if call.startswith("curl")]
    assert pings == ["curl https://hc.example/abc/start", "curl https://hc.example/abc"]


def test_a_failing_copy_pings_fail_and_does_not_record_success(sandbox):
    run, log, backups = sandbox

    result = run(
        BACKUP_REMOTE="enei-cifrado:enei",
        BACKUP_HEARTBEAT_URL="https://hc.example/abc",
        FAKE_RCLONE_FAIL="copy",
    )

    assert result.returncode != 0
    pings = [call for call in _calls(log) if call.startswith("curl")]
    assert pings[-1] == "curl https://hc.example/abc/fail"
    assert "curl https://hc.example/abc" not in pings
    assert not (backups / "offsite-last-success").exists()


def test_refusing_an_unencrypted_remote_also_pings_fail(sandbox):
    run, log, _ = sandbox

    result = run(
        BACKUP_REMOTE="enei-claro:enei", BACKUP_HEARTBEAT_URL="https://hc.example/abc"
    )

    assert result.returncode == 1
    assert _calls(log)[-1] == "curl https://hc.example/abc/fail"


def test_check_fails_when_there_was_never_a_copy(sandbox):
    run, _, _ = sandbox

    result = run(CHECK)

    assert result.returncode == 1
    assert "Nenhuma cópia" in result.stderr


def test_check_passes_when_the_last_copy_is_recent(sandbox, tmp_path):
    run, _, backups = sandbox
    backups.mkdir()
    (backups / "offsite-last-success").write_text(str(int(time.time()) - 3600))

    result = run(CHECK)

    assert result.returncode == 0, result.stderr


def test_check_fails_when_the_last_copy_is_older_than_the_limit(sandbox):
    run, _, backups = sandbox
    backups.mkdir()
    (backups / "offsite-last-success").write_text(str(int(time.time()) - 30 * 3600))

    assert run(CHECK).returncode == 1
    assert run(CHECK).stderr.strip().startswith("A última cópia externa tem")
