"""命令行入口：把依赖接线起来，跑通一次推荐（`python -m app`）。

Implements: architecture-blueprint.md §5（集成契约的实际接线点）
Verifies: REQ-ADS-FR-003（端到端可运行）、REQ-ADS-FR-004（结构化输出）

**本模块是唯一允许读写文件 / 读配置的层** —— `app.pipeline` 保持纯编排（依赖注入），
文件系统与配置访问集中在此，使管道可离线测试。

用法：
    python -m app --scene '{"time_slot":"night","device":"mobile","user_tags":["student"]}'
    python -m app --time-slot night --device mobile --tag student
    python -m app --time-slot night --device mobile --audit logs/audit.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ads.banned_words import BannedWords
from ads.repository import AdRepository
from audit import JsonlAuditStore
from compliance.rules import SceneRules
from render import to_json
from selector import MockLLM

from .config import AppConfig, ConfigError
from .pipeline import recommend

DEFAULT_CONFIG = "config.yaml"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app",
        description="场景化广告推荐引擎（V1）—— 端到端跑一次推荐",
    )
    p.add_argument("--config", default=DEFAULT_CONFIG, help="配置路径（默认 config.yaml）")
    src = p.add_mutually_exclusive_group()
    src.add_argument(
        "--scene",
        help='JSON 形式的场景，例如 \'{"time_slot":"night","device":"mobile"}\'',
    )
    src.add_argument("--time-slot", help="时段：morning/afternoon/evening/night")
    p.add_argument("--device", help="设备：mobile/tablet/desktop")
    p.add_argument("--tag", action="append", default=[], help="用户标签（可重复）")
    p.add_argument("--audit", help="审计日志路径（覆盖配置）")
    p.add_argument("--indent", type=int, default=2, help="输出 JSON 缩进（0 = 单行）")
    return p


def _scene_from_args(args: argparse.Namespace) -> dict:
    """从命令行参数得到原始场景输入（dict）。"""
    if args.scene:
        try:
            parsed = json.loads(args.scene)
        except json.JSONDecodeError as e:
            raise SystemExit(f"--scene 不是合法 JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise SystemExit("--scene 必须是 JSON 对象")
        return parsed
    if not args.time_slot or not args.device:
        raise SystemExit("需要 --scene，或同时给出 --time-slot 与 --device")
    return {
        "time_slot": args.time_slot,
        "device": args.device,
        "user_tags": list(args.tag),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(__file__).resolve().parents[2]

    # ---- ① 配置：启动期校验，非法即大声失败（不静默取默认值） ----
    try:
        config = AppConfig.load(root / args.config)
    except ConfigError as e:
        print(f"配置错误：\n{e}", file=sys.stderr)
        return 2

    # ---- ② 场景输入 ----
    try:
        scene_raw = _scene_from_args(args)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2

    # ---- ③ 只读数据源 ----
    try:
        repo = AdRepository.load(root / config.data.ads_path)
        banned = BannedWords.load(root / config.data.banned_words_path)
        rules = SceneRules.load(root / config.data.scene_rules_path)
    except Exception as e:  # noqa: BLE001 —— 启动期数据问题须明确报告后退出（fail loudly）
        print(f"数据加载失败：{e}", file=sys.stderr)
        return 2

    audit_path = Path(args.audit) if args.audit else (root / config.audit.log_path)
    store = JsonlAuditStore(audit_path)

    # ---- ④ 跑管道（离线用 MockLLM；真实 LLM 接入属 P8） ----
    rec = recommend(
        scene_raw,
        repo=repo,
        banned_words=banned,
        rules=rules,
        client=MockLLM(),
        audit_store=store,
        config=config,
    )

    indent = None if args.indent == 0 else args.indent
    print(to_json(rec.result, indent=indent))
    # 审计 ID 走 stderr，保持 stdout 只含渲染结果（便于管道化消费）
    print(f"[audit_id] {rec.audit_id or '(审计失败)'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
