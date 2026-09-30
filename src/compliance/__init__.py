"""合规过滤模块（REQ-006~009/016）。

- models.py     CheckResult / ComplianceVerdict
- rules.py      SceneRules 规则加载（品类禁忌 + 场景硬约束）
- pipeline.py   确定性纯函数管道：任一检查失败 → REJECT（REQ-006）
"""
