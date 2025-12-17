#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import yaml


def _read_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def load_cfg(config_path: Path | None) -> dict:
    """
    設定ファイルの優先順位:
      1) --config で指定されたファイル
      2) ./ .semgrep.yaml  (実行したディレクトリ内)
      3) .github/ci/semgrep_basic_setting.yml  (リポジトリルート相当から)
         ※ これは「今のcwd」からの相対なので、基本は --config を推奨
    """
    if config_path is not None:
        if not config_path.exists():
            raise FileNotFoundError(f"--config not found: {config_path}")
        return _read_yaml(config_path)

    local_cfg = Path(".semgrep.yaml")
    if local_cfg.exists():
        return _read_yaml(local_cfg)

    fallback = Path(".github/ci/setting.yml")
    if fallback.exists():
        return _read_yaml(fallback)

    fallback = Path("../.github/ci/setting.yml")
    if fallback.exists():
        return _read_yaml(fallback)

    fallback = Path("../../.github/ci/setting.yml")
    if fallback.exists():
        return _read_yaml(fallback)

    # ここまで来たら「どこにも無い」
    raise FileNotFoundError("Missing config: --config / ./.semgrep.yaml / .github/ci/semgrep_basic_setting.yml")


def get_rule_id(r: dict) -> str:
    return (r.get("check_id") or r.get("rule_id") or "") or ""


def get_path(r: dict) -> str:
    return (r.get("path") or "") or ""


def get_message(r: dict) -> str:
    extra = r.get("extra") or {}
    return ((extra.get("message") or "") or "")


def get_severity(r: dict) -> str:
    extra = r.get("extra") or {}
    return (((extra.get("severity") or "UNKNOWN") or "UNKNOWN").upper())


def matches_drop_entry(r: dict, entry: dict) -> bool:
    # drop の 1要素内は AND
    rid = get_rule_id(r)
    path = get_path(r)
    msg = get_message(r)

    if "rule" in entry and rid != str(entry["rule"]):
        return False
    if "path_contains" in entry and str(entry["path_contains"]) not in path:
        return False
    if "message_contains" in entry and str(entry["message_contains"]) not in msg:
        return False

    # 空 entry は無効
    if not any(k in entry for k in ("rule", "path_contains", "message_contains")):
        return False

    return True


def should_drop(r: dict, drop_list: list) -> bool:
    # drop 配列は OR
    for e in drop_list:
        if isinstance(e, dict) and matches_drop_entry(r, e):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="semgrep.json", help="input semgrep json path")
    ap.add_argument("--setting", required=False, help="settings yml path (with optional drop:)")
    ap.add_argument("--out-txt", default="semgrep.txt", help="output txt path")
    ap.add_argument("--out-md", default="semgrep.md", help="output md path")
    ap.add_argument("--max-txt", type=int, default=3000, help="max chars for txt")
    args = ap.parse_args()

    json_path = Path(args.json)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    results = data.get("results") or []
    errors = data.get("errors") or []

    cfg = load_yaml(Path(args.setting)) if args.setting else {}
    drop_list = cfg.get("drop") or []

    filtered = [r for r in results if not should_drop(r, drop_list)]

    total = len(filtered)
    error_count = len(errors)

    by_rule = Counter((get_rule_id(r) or "?") for r in filtered)
    by_file = Counter((get_path(r) or "?") for r in filtered)
    by_sev = Counter(get_severity(r) for r in filtered)

    # TXT（Slack用）
    lines: list[str] = []
    lines.append("Semgrep Summary")
    lines.append(f"- findings: {total}")
    if error_count:
        lines.append(f"- errors: {error_count}")
    if total:
        lines.append("- severity: " + ", ".join(f"{k}:{v}" for k, v in sorted(by_sev.items())))
        lines.append("")
        lines.append("Top rules:")
        for rid, cnt in by_rule.most_common(10):
            lines.append(f"- {rid}: {cnt}")
        lines.append("")
        lines.append("Sample findings:")
        for r in filtered[:20]:
            path = get_path(r) or "?"
            start = (r.get("start") or {}).get("line", "?")
            rid = get_rule_id(r) or "?"
            msg = get_message(r).replace("\n", " ")
            lines.append(f"- {path}:{start} [{rid}] {msg}".strip())

    out_txt = "\n".join(lines)[: args.max_txt]
    Path(args.out_txt).write_text(out_txt, encoding="utf-8")

    # MD（人間用）
    md: list[str] = []
    md.append("# Semgrep report\n")
    md.append(f"- findings: **{total}**")
    if error_count:
        md.append(f"- errors: **{error_count}**")
    if total:
        md.append("- severity: " + ", ".join(f"**{k}**:{v}" for k, v in sorted(by_sev.items())))
        md.append("\n## Top rules")
        for rid, cnt in by_rule.most_common(20):
            md.append(f"- `{rid}`: {cnt}")
        md.append("\n## Top files")
        for fp, cnt in by_file.most_common(20):
            md.append(f"- `{fp}`: {cnt}")
        md.append("\n## Findings (first 50)")
        for r in filtered[:50]:
            path = get_path(r) or "?"
            start = (r.get("start") or {}).get("line", "?")
            rid = get_rule_id(r) or "?"
            msg = get_message(r).replace("\n", " ")
            md.append(f"- `{path}:{start}` **{rid}** — {msg}")

    Path(args.out_md).write_text("\n".join(md), encoding="utf-8")

    print(out_txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
