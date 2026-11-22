"""V3 输出编码回归测试（REQ-ADS-FR-004 / 测试同学 F-006）。

Verifies: REQ-ADS-FR-004（结构化输出契约：机器可读）

背景：Windows 下 `sys.stdout` 默认编码是 GBK/CP936，把 CLI 输出重定向到文件后
得到的是 GBK 字节，按 UTF-8 解析即失败——机器读不了。JSON 按 RFC 8259 必须是 UTF-8，
所以输出要绕过文本层直接写字节。

本模块**先于实现**写成（TA-0005 在实现前签署）：实现前它必须红。
"""

from __future__ import annotations

import io
import json
import sys

import app.cli as cli


class _GbkStdout:
    """模拟 Windows 默认的 GBK stdout，但带二进制缓冲区。"""

    encoding = "gbk"

    def __init__(self) -> None:
        self.buffer = io.BytesIO()
        self.text: list[str] = []

    def write(self, chunk: str) -> int:  # pragma: no cover - 仅在回退分支被用到
        self.text.append(chunk)
        return len(chunk)

    def flush(self) -> None:  # pragma: no cover
        return None


def test_write_stdout_emits_utf8_bytes(monkeypatch):
    """REQ-ADS-FR-004：输出必须是 UTF-8 字节，且在 GBK 环境下仍可被 json 解析。"""
    payload = json.dumps({"kind": "ad", "title": "深夜咖啡外卖"}, ensure_ascii=False)
    fake = _GbkStdout()
    monkeypatch.setattr(sys, "stdout", fake)

    writer = getattr(cli, "write_stdout", None)
    assert writer is not None, "app.cli 必须提供 write_stdout（F-006 修复）"
    writer(payload + "\n")

    raw = fake.buffer.getvalue()
    decoded = json.loads(raw.decode("utf-8"))
    assert decoded["title"] == "深夜咖啡外卖"
    assert fake.text == [], "有二进制缓冲区时不得走文本层（否则又退回 GBK）"
