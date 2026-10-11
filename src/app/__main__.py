"""`python -m app` 的入口点。

Implements: REQ-ADS-FR-003（端到端可运行）
Verifies: 使 `python -m app` 可执行（包级别入口的标准做法）

本文件只做转发，不含逻辑 —— 逻辑在 `app/cli.py` 与 `app/pipeline.py`。
"""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
