#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import sys
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


def _list(cfg: dict, key: str) -> list[str]:
    v = cfg.get(key, [])
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError(f"{key} must be a list")
    out: list[str] = []
    for x in v:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def build_cmd(cfg: dict, json_mode: bool) -> list[str]:
    base_config = str(cfg.get("base_config", "auto")).strip() or "auto"
    include_options = _list(cfg, "include_options")
    include_dir = _list(cfg, "include_dir") or ["."]
    exclude_dir = _list(cfg, "exclude_dir")
    exclude_rules = _list(cfg, "exclude_rules")

    cmd = ["semgrep", "scan", "--config", base_config]

    for c in include_options:
        cmd += ["--config", c]

    for p in exclude_dir:
        cmd += ["--exclude", p]

    for rid in exclude_rules:
        cmd += ["--exclude-rule", rid]

    if json_mode:
        cmd += ["--json"]

    cmd += include_dir
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=False, help="config yaml path (optional)")
    parser.add_argument("--json", action="store_true", help="add --json to semgrep command")
    args = parser.parse_args()

    config_path = Path(args.config).resolve() if args.config else None
    cfg = load_cfg(config_path)

    cmd = build_cmd(cfg, json_mode=bool(args.json))

    # stdout にはコマンド文字列のみ
    print(" ".join(shlex.quote(x) for x in cmd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

