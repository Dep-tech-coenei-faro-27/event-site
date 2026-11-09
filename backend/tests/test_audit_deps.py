import datetime
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit_deps.py"
spec = importlib.util.spec_from_file_location("audit_deps", SCRIPT)
audit_deps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_deps)

TODAY = datetime.date(2026, 10, 27)
PIP_REPORT = {
    "dependencies": [
        {"name": "fastapi", "version": "1.0.0", "vulns": []},
        {
            "name": "dnspython",
            "version": "2.8.0",
            "vulns": [
                {
                    "id": "CVE-2026-114605",
                    "aliases": ["GHSA-45c3-73f7-pv4m"],
                    "fix_versions": ["2.9.0"],
                }
            ],
        },
    ]
}
NPM_REPORT = {
    "vulnerabilities": {
        "lodash": {
            "via": [
                {
                    "name": "lodash",
                    "severity": "high",
                    "url": "https://github.com/advisories/GHSA-35jh-r3h4-6jhm",
                    "range": "<4.17.21",
                    "title": "Command Injection in lodash",
                },
                {
                    "name": "lodash",
                    "severity": "moderate",
                    "url": "https://github.com/advisories/GHSA-29mw-wpgm-hmr9",
                },
            ]
        },
        # Só depende do lodash: aparece como texto e não conta outra vez.
        "some-wrapper": {"via": ["lodash"]},
    }
}


def exception(**overrides) -> str:
    entry = {
        "ecosystem": '"python"',
        "id": '"GHSA-45c3-73f7-pv4m"',
        "package": '"dnspython"',
        "reason": '"Not reachable from our code."',
        "review_by": "2026-12-31",
    } | overrides
    return "[[exception]]\n" + "".join(
        f"{k} = {v}\n" for k, v in entry.items() if v is not None
    )


def test_pip_audit_report_lists_each_vulnerability_with_its_aliases():
    [finding] = audit_deps.pip_audit_findings(PIP_REPORT)

    assert finding.package == "dnspython"
    assert finding.ids == {"CVE-2026-114605", "GHSA-45c3-73f7-pv4m"}


def test_npm_report_keeps_only_high_and_critical_advisories():
    [finding] = audit_deps.npm_audit_findings(NPM_REPORT)

    assert finding.package == "lodash"
    assert finding.ids == {"GHSA-35jh-r3h4-6jhm"}


def test_exception_matches_by_alias_and_package():
    [finding] = audit_deps.pip_audit_findings(PIP_REPORT)
    valid, problems = audit_deps.load_exceptions(exception(), "python", TODAY)

    assert problems == []
    assert audit_deps.is_excepted(finding, valid)


def test_exception_for_another_package_or_ecosystem_does_not_apply():
    [finding] = audit_deps.pip_audit_findings(PIP_REPORT)
    other_package, _ = audit_deps.load_exceptions(
        exception(package='"requests"'), "python", TODAY
    )
    other_ecosystem, _ = audit_deps.load_exceptions(
        exception(ecosystem='"npm"'), "python", TODAY
    )

    assert not audit_deps.is_excepted(finding, other_package)
    assert other_ecosystem == []


def test_exception_without_reason_or_date_is_a_problem():
    _, no_reason = audit_deps.load_exceptions(exception(reason='"  "'), "python", TODAY)
    _, no_date = audit_deps.load_exceptions(exception(review_by=None), "python", TODAY)
    _, text_date = audit_deps.load_exceptions(
        exception(review_by='"soon"'), "python", TODAY
    )

    assert "falta reason" in no_reason[0]
    assert "falta review_by" in no_date[0]
    assert "tem de ser uma data" in text_date[0]


def test_expired_exception_no_longer_applies():
    valid, problems = audit_deps.load_exceptions(
        exception(review_by="2026-10-26"), "python", TODAY
    )

    assert valid == []
    assert "já passou" in problems[0]


def test_expired_exception_of_the_other_ecosystem_is_still_reported():
    _, problems = audit_deps.load_exceptions(
        exception(ecosystem='"npm"', review_by="2026-01-01"), "python", TODAY
    )

    assert len(problems) == 1


def test_repository_exceptions_file_is_well_formed():
    # Só a forma: o prazo é o passo do CI que o vê (com a data de hoje).
    text = (SCRIPT.parents[1] / "audit-exceptions.toml").read_text()

    for ecosystem in ("python", "npm"):
        _, problems = audit_deps.load_exceptions(text, ecosystem, datetime.date.min)
        assert problems == []
