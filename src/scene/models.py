"""场景数据模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scene:
    """一次广告请求的用户场景（REQ-003 校验通过后的规范形态）。

    user_tags 为空元组表示未提供用户画像标签。
    """

    time_slot: str
    device: str
    user_tags: tuple[str, ...] = ()
