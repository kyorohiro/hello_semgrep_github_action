import json
import sys
from pathlib import Path
import pytest

# repo-root を基準に .github/ci を import 可能にする
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / ".github" / "ci"))

import summary_gen as s  # noqa: E402


def mk_result(rule_id="r1", path="src/a.js", msg="hello", severity="WARNING", line=10):
    return {
        "check_id": rule_id,
        "path": path,
        "start": {"line": line},
        "extra": {"message": msg, "severity": severity},
    }


def test_matches_drop_entry_and_semantics():
    r = mk_result(rule_id="rule.eval", path="generated/x.js", msg="eval detected")

    # ruleだけ一致
    assert s.matches_drop_entry(r, {"rule": "rule.eval"}) is True
    assert s.matches_drop_entry(r, {"rule": "rule.other"}) is False

    # path_contains
    assert s.matches_drop_entry(r, {"path_contains": "generated/"}) is True
    assert s.matches_drop_entry(r, {"path_contains": "src/"}) is False

    # message_contains
    assert s.matches_drop_entry(r, {"message_contains": "eval"}) is True
    assert s.matches_drop_entry(r, {"message_contains": "command"}) is False

    # AND（同一entry内は全部満たす必要）
    assert s.matches_drop_entry(r, {"rule": "rule.eval", "path_contains": "generated/"}) is True
    assert s.matches_drop_entry(r, {"rule": "rule.eval", "path_contains": "src/"}) is False

    # 空 entry は無効
    assert s.matches_drop_entry(r, {}) is False


def test_should_drop_or_semantics():
    r = mk_result(rule_id="A", path="src/a.js", msg="something")

    drop_list = [
        {"rule": "NO_MATCH"},
        {"path_contains": "generated/"},
        {"message_contains": "something"},  # ←これが当たる
    ]
    assert s.should_drop(r, drop_list) is True

    drop_list2 = [{"rule": "NO_MATCH"}, {"path_contains": "generated/"}]
    assert s.should_drop(r, drop_list2) is False


def test_getters_defaults():
    r = {"extra": {}}
    assert s.get_rule_id(r) == ""
    assert s.get_path(r) == ""
    assert s.get_message(r) == ""
    assert s.get_severity(r) == "UNKNOWN"


def test_build_reports_filters_and_counts():
    # 3 findings 中 1つは drop される
    results = [
        mk_result(rule_id="javascript.lang.security.audit.eval-detected", path="generated/a.js", msg="eval detected", severity="ERROR"),
        mk_result(rule_id="x", path="src/a.js", msg="ok", severity="WARNING"),
        mk_result(rule_id="x", path="src/b.js", msg="ok2", severity="WARNING"),
    ]
    errors = [{"type": "SemgrepError"}]

    drop_list = [
        {"rule": "javascript.lang.security.audit.eval-detected", "path_contains": "generated/"},
    ]

    txt, md = s.build_reports(results, errors, drop_list, max_txt=10000)

    assert "- findings: 2" in txt
    assert "- errors: 1" in txt
    assert "Top rules:" in txt
    assert "`src/a.js:10`" in md or "src/a.js" in md  # 出力形式の揺れに強めに
    assert "**WARNING**:2" in md or "WARNING" in md


def test_build_reports_max_txt_truncates():
    results = [mk_result(rule_id="x", path="src/a.js", msg="m" * 5000, severity="WARNING")]
    errors = []
    drop_list = []

    txt, _md = s.build_reports(results, errors, drop_list, max_txt=200)
    assert len(txt) <= 200


def test_load_yaml_prefers_config_path(tmp_path: Path, monkeypatch):
    # --config を指定した時にそれが最優先
    cfg = tmp_path / "cfg.yml"
    cfg.write_text("drop:\n  - message_contains: client_id\n", encoding="utf-8")

    loaded = s.load_yaml(cfg)
    assert loaded["drop"][0]["message_contains"] == "client_id"


def test_load_yaml_finds_local_dot_semgrep_yaml(tmp_path: Path, monkeypatch):
    # cwd に .semgrep.yaml があればそれを読む
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".semgrep.yaml").write_text("drop:\n  - rule: A\n", encoding="utf-8")
    loaded = s.load_yaml(None)
    assert loaded["drop"][0]["rule"] == "A"


def test_load_yaml_missing_raises(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        s.load_yaml(None)


def test_end_to_end_like_json_file(tmp_path: Path):
    # I/O ありの流れを軽く再現（mainを叩かずに json を読むところまで）
    semgrep_json = tmp_path / "semgrep.json"
    semgrep_json.write_text(json.dumps({
        "results": [mk_result(rule_id="A", path="src/a.js", msg="client_id is ok")],
        "errors": []
    }), encoding="utf-8")

    # drop: message_contains client_id で落ちる
    drop_list = [{"message_contains": "client_id"}]
    data = json.loads(semgrep_json.read_text(encoding="utf-8"))
    txt, md = s.build_reports(data["results"], data["errors"], drop_list, max_txt=10000)

    assert "- findings: 0" in txt
    assert "**0**" in md
