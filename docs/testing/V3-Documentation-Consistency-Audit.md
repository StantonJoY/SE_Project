# V3 文档一致性审查（Documentation Consistency Audit）

> **对象**：`main` @ `7ff5cc2`（V3 合入后的文档/流程面）
> **执行**：2026-11-22 · 编码 agent 自查 + 人工判读
> **结论**：修复 9 类缺口；发现并关闭一处**门禁覆盖漏洞**；4 类历史快照刻意不改
> **配对证据**：`docs/testing/V3-Test-Report.md`（功能面）、本文件（文档面）

---

## 1. 为什么要单独审这一遍

V3 的功能验证由独立测试完成（`docs/testing/V3-Test-Report.md`），但那条线只验证"系统行为对不对"。
文档面还有一类失效不会被测试抓到：**同一事实在三处写了三个版本**，或者**门禁实际检查的范围比它声称的窄**。
V3 一次性合并了 21 个提交、200 多个文件，正是这类漂移最容易发生的时点。

本审查只回答三个问题：

1. 文档里的数字，还有没有与仓库现状不一致的？
2. 流程工件（验收状态、复核记录、索引、债务处置）有没有缺的？
3. 门禁的**实际覆盖**与它**声称的覆盖**是否一致？

---

## 2. 方法

三类检查，全部可复跑（§6 给命令）：

| 类型 | 手段 | 抓什么 |
|---|---|---|
| 结构一致性 | 脚本遍历 45 份 `.md`，解析 `[text](path)` 并校验目标存在 | 断链、改名后未更新的引用 |
| 数字一致性 | 关键词扫描（`617`/`648`/`675`/`16 条不变量`/`6 道门禁`…） | 过期计数 |
| 语义一致性 | 人工比对 `blueprint §4` ↔ `fitness_functions.ELEMENT_BY_PACKAGE` ↔ 检查器解析结果 | 编号漂移、覆盖漏洞 |

人工判读的原则只有一条：**区分"活文档"与"历史快照"**。
`HANDOVER.md`、`HANDOVER-V2.md`、各测试报告的运行数字、ADR 的决策时点描述都属于后者，
改了就不是快照，而是伪造当时的证据。

---

## 3. 发现与处置

### 3.1 高：门禁覆盖漏洞（架构元素编号漂移）

| 项 | 内容 |
|---|---|
| 现象 | `architecture-blueprint.md` §4 用 ⑧=`eval/`、⑨=`scripts/`；而 `fitness_functions.ELEMENT_BY_PACKAGE` 用 ⑧=`bidding`、⑨=`corpus`。两套编号互不相干 |
| 后果 | `check_repo_completeness.py` 从 blueprint 解析元素清单，因此只解析出 7 个（ads…app）。**R2 检查（"声明的元素必须有目录且已交付"）从未覆盖 `src/bidding/` 与 `src/corpus/`** |
| 严重度 | 高 —— 这是"门禁声称保护 9 个元素、实际保护 7 个"，与 BUG-008（`src/audit/` 从未被跟踪）同类 |
| 修复 | `architecture-blueprint.md` §4 对齐 ①..⑨（⑧ bidding、⑨ corpus）；`eval/`、`scripts/` 移入「验证资产（不占元素编号）」表；`check_repo_completeness` 现在解析 9 个 |
| 连带 | 断言 `test_checker_parses_seven_elements` 过时 → 改名 `test_checker_parses_all_elements`，断言 9 个。**改测试前先签 `TA-0007`**（20:40，早于改动提交） |

### 3.2 中：缺失的流程工件

| 缺什么 | 补什么 | 证据 |
|---|---|---|
| V3 无验收状态文件（V2 有） | `docs/v3-approval-status.yaml`：交付信息、ADR-006 批准、TA-0005/0006、七道门禁实况、已知限制 | 本文件 §4 |
| 复核记录停在 V2 | `review-memo.md` 追加「V3 复核记录（2026-11-22）」，判定 `ACCEPTED WITH DOCUMENTED GAP` | 该文件 |
| 45 份文档无入口 | `docs/README.md`：按"我要做什么"分 6 类 | 该文件 |
| `TD-018` 只有描述无处置 | 补「处置（2026-11-22）」：TA-0005 前置批准 + TA-0006 事后验收 | `debt-register.md` |
| `AGENTS.md` 停在 V2 | 顶部加 V3 状态块（61 需求 / 36 不变量 / 9 元素 / 679 测试 / 33 变异 / 7 门禁 / 57 用例） | `AGENTS.md` |

### 3.3 低：过期数字与断链

| 位置 | 原值 | 现值 | 说明 |
|---|---|---|---|
| `invariants.md` 统计行 | 16 条 | 36 条（16+12+8） | 文件里确实有 36 条，统计行没跟着改 |
| `verification-constraints.md` | 全部 16 条 | 36 条 | 同上 |
| `concern-clusters.md` 输入 | A2：16 条 | 36 条 | 同上 |
| `mcp-tool-manifest.md` | 6 道门禁 ×3 | 7 道 | 补 Gate 5b 后未同步 |
| `HANDOVER-V3.md` | 671 passed | 679 | 最后一次加测试后未同步 |
| `requirements-v3-se.md` | 617 个测试 | 679 | 同上 |
| 演示截图链接（2 文件 20 处） | `../../evidence/...` / 缺前缀 | 修正 | `evidence/` 副本与 `docs/testing/` 副本路径不同 |

### 3.4 刻意未改（附理由）

| 保留 | 理由 |
|---|---|
| `HANDOVER.md`、`HANDOVER-V2.md`、`AGENTS.md` 的 V1/V2 段 | 历史快照；已由 V3 状态块显式指认"不作为当前门槛" |
| `docs/testing/V3-*` 中的 675 | 当次运行记录；回填数字等于伪造证据 |
| `ADR-004` 的"六道门禁检查器" | ADR 记录决策时点的事实，不是活文档 |
| `debt-register` 各 TD 的原始现状描述 | 同上 |

---

## 4. 残留风险（本轮不解决）

| 风险 | 影响 | 建议 |
|---|---|---|
| `docs/README.md` 与各文档中的"当前数字"仍会随时间过期 | 同类漂移会复发 | 索引只放"去哪找"，不放数字；数字口径固定为三个单一来源（`invariants.md` / `requirements.yaml` / `acceptance-coverage-map.yaml`） |
| 断链检查不在 CI 里 | 下次改名仍会漏 | 若要自动化，需新增 `scripts/check_docs.py`；`scripts/check_*.py` 属 ADR-004 保护路径，须先立 ADR |
| 3 条流程不变量（`INV-ADS-009/010/011`）无变异支撑 | 覆盖表已如实标 `false` | 属"无法用代码破坏"的流程约束，保持登记即可 |
| `Report.md` 仍在工作区未入库 | 交付物与仓库脱钩 | 定稿后按学号命名并入库 |

---

## 5. 与功能测试的关系

本审查**不能**替代功能验证，也不改变其结论：

- 功能面：679 项离线测试、33/33 变异、三套 replay 违规 0（见 `V3-Test-Report.md`）；
- 文档面：本文件；
- 两者共同支撑 `review-memo.md` 的判定 `ACCEPTED WITH DOCUMENTED GAP`。

---

## 6. 复跑方式

```bash
# 1) 断链（排除 transcripts 的路径式引用）
python - <<'PY'
import re
from pathlib import Path
root = Path('.')
for p in sorted(root.rglob('*.md')):
    if '.git' in p.parts or 'transcripts' in p.parts:
        continue
    text = p.read_text(encoding='utf-8', errors='replace')
    for target in re.findall(r'\[[^\]]*\]\(([^)\s]+?)\)', text):
        if target.startswith(('http', 'mailto', '<')):
            continue
        if not (p.parent / target.split('#')[0]).exists():
            print(f'{p} -> {target}')
PY

# 2) 过期数字（人工判读，排除历史快照目录）
grep -rn --include=*.md -E '617|648|660|671|675 ' docs/ *.md | grep -v transcripts

# 3) 元素编号一致性（唯一来源比对）
python scripts/check_repo_completeness.py | head -5
python -c "import sys; sys.path.insert(0,'scripts'); import fitness_functions as f; print(sorted(f.ELEMENT_BY_PACKAGE))"
```
