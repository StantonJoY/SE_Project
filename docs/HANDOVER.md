# CS5351 项目交接文档（HANDOVER）

> 快照日期：2026-10-04 · **本文档为 V1 技术交接**（状态字段已于 2026-10-06 更新至最新）。
>
> **接手 V2（竞价轮次）的人请先读 → [`docs/HANDOVER-V2.md`](HANDOVER-V2.md)**
> —— 那份包含 V1 的欠缺清单（三类）、V2 的两个必须先解决的设计冲突
> （状态设计 / 审计可读性）、V2 开工前的必备清单、以及本项目踩过的九个坑。
>
> 配套文档：`docs/req/requirements-v1-draft.md`（REQ-001~020）、`docs/req/requirements-v2-bidding-draft.md`（REQ-021~039）、`docs/design/technical-design-v1.md`（V1 技术方案）。

---

## 1. 项目一句话

**场景化广告推荐引擎**（CS5351 Agentic Software Engineering Project）：给定广告素材库与用户场景特征（时段/设备/用户标签），系统选出一条广告渲染展示。核心命题：**AI 做推荐决策（LLM）+ 确定性代码做合规兜底**——"AI 是顾问，代码是执行官"。

## 2. 30 秒速览

| 项 | 状态 |
|---|---|
| 版本 | **V1 基线**（无 RAG、无竞价）；V2=竞价候选（归属 `docs2/` 轮次）、V3=RAG 占位 |
| 技术栈 | Python 3.10+（本地 3.14.7）、**无数据库**（JSON 文件 + JSONL 日志）、jsonschema + PyYAML + pytest |
| 进度 | **7 个架构元素全部实现**（ads / scene / compliance / selector / render / audit / app）+ **P7 完成**（固定评估集 + 版本溯源 + 变异验证）。D1/D2/D4/D7/D9 完成；D3/D8 部分 |
| 测试 | **285 个离线测试全部通过**（15 个模块，0 error） |
| 验证门 | **十项检查全绿**：ruff / mypy / 依赖 / schema / fitness / pytest / 审计 / AI-use 日志 / 门禁 1 / **门禁 4** |
| **评估集** | `eval/eval_cases.json` **25 条**（11 MUST_PASS / 14 MUST_FAIL）；`python eval/eval_runner.py` 一键 replay；当前达成率 **1.0000**、违规 **0** |
| **变异验证** | `python scripts/mutation_check.py` —— **13/13 条不变量**注入违规后其反例测试**确实失败** |
| 下一步 | **P8 真实 LLM 接入**（供应商选型见 `OQ-001`）。届时须按 `ADR-003` T2 **重标定评估口径**（达成率预期下降，**非异常**） |
| 阻塞 | **无硬阻塞**。剩余未覆盖：`REQ-ADS-GOV-002` 与 `INV-ADS-009/010/011` 的**流程侧**（属 D3 的权限模型与 hook） |
| 仓库 | `D:\CityU\SE\project\SE_Project`，remote `git@github.com:StantonJoY/SE_Project.git` |

**端到端复跑（一行）**：
```
.\.venv\Scripts\python.exe -m app --time-slot night --device mobile --tag student
```
输出广告形态 JSON（含 `explanation` 与 `audit_id`）；审计记录追加写入 `logs/audit.jsonl`
（`--audit <path>` 可覆盖）。

常用命令（仓库根目录）：
```
.\.venv\Scripts\python.exe scripts\validate_requirements.py      # 门禁 3 · Schema + 架构输入双向校验
.\.venv\Scripts\python.exe scripts\fitness_functions.py          # Tier 1 · 结构门（S1-S3 / V1-V4）
.\.venv\Scripts\python.exe scripts\audit_implementation.py       # 实现 ↔ 需求/规约 一致性审计
.\.venv\Scripts\ruff.exe check src test scripts                  # 门禁 2 · lint
.\.venv\Scripts\mypy.exe --no-incremental --cache-dir=D:\CityU\.mypycache   # 门禁 2 · 类型
.\.venv\Scripts\python.exe scripts\check_dependencies.py         # 门禁 2 · 依赖
.\.venv\Scripts\python.exe scripts\check_safety_paths.py --show-paths       # 门禁 2 · 安全路径
.\.venv\Scripts\python.exe scripts\check_test_approval.py --files <paths>   # 门禁 1
.\.venv\Scripts\python.exe scripts\check_ai_use_log.py --files <paths>      # 门禁 6
.\.venv\Scripts\python.exe scripts\check_semantic_eval.py --files <paths>   # 门禁 4
.\.venv\Scripts\python.exe -m pytest test/offline                 # 门禁 5 · 回归
```

> **P4+P5+P6 已完成（2026-10-06）**：`src/selector/`（AI 建议层）、`src/app/`（编排 + 10 条降级路径）、
> `src/render/`（两形态 schema）、`src/audit/`（JSONL 审计 + 22 条 monitor 登记）。
> 批准链：ADR-001/002 `Accepted`（Shane）→ `docs/plans/P4-selector.md` 获批 →
> P4 测试**先于实现**获批（`TA-0002`，门禁 1 的正例）→ P4 实现 →
> P5/P6 按人类「先跑通」指示实现（`TA-0003` **批准晚于实现** ⚠️，登记为 `TD-023`）。
>
> **覆盖进展**：需求 `test_backed` **17/22**、不变量反例覆盖 **12/16**（计数经脚本核对）。
> 仍开放 20 条技术债；`TD-001`（22 条 monitor 的**采集与告警接线**）与
> `TD-003`（评估集）是最重的两条。

> **架构输入链路（A1→A2→A5→ADR→Blueprint）**：
> `requirements.yaml`（RE）→ `asr-register.md`（A1：18 ASR + 4 impl，五维 Litmus）
> → `invariants.md`（A2：16 条不变量，六字段，fallback 全 fail-closed）
> → `concern-clusters.md`（A5：5 个 concern cluster + 优先级 + 6 组冲突裁决 + 7 条假设）
> → `adr-001/002`（决策）→ `architecture-blueprint.md`（根目录，11 节可执行约束）
> → `runtime-policy-catalog.md`（**17 条**失败策略）。
> 三处双向一致性由 `validate_requirements.py` 强制：注册表的 `asr_id`/`invariants` 与两个登记册互相回指，孤儿条目即报错。
>
> **架构决策要点**：本项目**没有运行时人类复核环节**，故 `REVIEW` 的等价物是 **`no_ad`**（不展示即 fail-closed）；
> 审计写入失败 → 整体失败；行为测试失败而结构测试通过 → **改架构而非 patch 代码**（ADR-002 D3）。
>
> **CORE 工件进度**（课程规定 5 份）：**5/5 全部完成** ——
> `architecture-blueprint.md` ✅、`docs/architecture/invariants.md` ✅、`docs/architecture/trace-matrix.md` ✅、
> `docs/architecture/memory-design.md` ✅、`docs/architecture/adr-001/002-*.md` ✅（扁平命名，非 `adr/` 子目录）。
>
> **架构债 21 条**（编号 `TD-001`~`TD-022`，其中 3 条已关闭）：见 `docs/debt-register.md`。
> **`TD-001` 最严重**：22 条需求的运行时 monitor 全部未实现（落地主要在 P6）。
> **`TD-022`**：元素 ⑤–⑦（`render`/`audit`/`app`）仍空 —— 系统**尚不能端到端跑通一次推荐**。
>
> **2026-10-06 代码审计结论**：见 `docs/bug-diary.md`。
> 修复 `BUG-006`（违禁词命中非确定性）、`BUG-007`（`BannedWords.load` fail-closed 不一致）；
> 补齐 4 个覆盖缺口涉及的素材（`data/ads.json` 由 8 条扩至 **14 条**），
> 并把 `banned_check` 从"声明却不强制"实装为管道第五步（**仅 `checked` 放行**）。

> 环境提示（受限沙箱）：本机若在受限沙箱内运行，子进程**无法在 `D:\CityU` 的子目录创建文件/目录**，
> 因此 `test_ads.py` 中 5 个使用 pytest `tmp_path` 的用例会以 `PermissionError` 报错（非代码缺陷）。
> 把 `TEMP`/`TMP` 指到 `D:\CityU`（工作区根）可让子进程拿到临时目录。

---

## 3. 课程背景与硬约束（CS5351）

- 人类监督下用 AI coding agent 完成完整软件工程生命周期；应用须含**至少一个真实 AI 组件**（LLM 功能/RAG/AI 决策路径），且**至少一个确定性安全边界**（AI 输出必须受确定性代码约束）。
- 交付物 D1~D9：机器可读需求（YAML+Schema）、11 类架构文档、编码治理（AGENTS.md 等）、验证治理（三层测试/评审备忘录/债务登记/Bug 日记）、5 份 agent 会话记录、报告（>15 页 ≤1 万字）、GitHub 仓库（6 道 CI 阻塞门禁）、源码与测试、静态 Prompt.md。
- 报告须含成员相对贡献（平均 1.0）；**提交文件统一用学号命名（60989886）**。
- VHIS 是参考模式，不可直接扩展。

## 4. 架构（V1）

### 4.1 数据流

```
场景特征输入（time_slot / device / user_tags）
   ↓  scene.parse_scene 校验（REQ-003，非法直接拒绝）
① 规则预筛（ads.filter_by_scene）：素材自身场景硬约束 → 候选集
   ↓
② LLM 选取（selector，AI 组件）：候选集内闭集选择，输出 JSON {ad_id, reason, confidence}
   ↓
③ 合规过滤（compliance.run_compliance，确定性安全边界）：
   output_exists → banned_words → banned_check → category → scene，任一失败 REJECT
   ↓
④ 渲染输出（render）+ 审计日志（audit，JSONL）
```

### 4.2 模块划分（模块 ↔ 架构元素一一对应，均为平级顶层包）

| 模块 | 路径 | 职责 | 对应 REQ |
|---|---|---|---|
| ads | `src/ads/` | 素材 schema/加载/查询/场景预筛/违禁词 | 001/002/008 |
| scene | `src/scene/` | 场景输入校验与规范化 | 003 |
| selector | `src/selector/`（P4） | LLM 接口 + mock + 真实实现 + 输出解析 | 004/005/010/016 |
| compliance | `src/compliance/` | 合规纯函数管道 | 006~009/016 |
| render | `src/render/`（P6） | 结果结构、序列化 | 012 |
| audit | `src/audit/`（P6） | JSONL 审计日志 | 013 |
| app | `src/app/`（P5） | pipeline 编排 + CLI | 011/014/015 |

> 包布局注意：`pyproject.toml` 用 `[tool.setuptools.packages.find] where=["src"]`，**ads/compliance/scene 等是平级顶层包**，模块间一律用绝对导入（`from ads.xxx import ...`），禁止相对跨包导入。

### 4.3 安全边界（课程灵魂）

- compliance 为**确定性纯函数管道（五步）**：`check_output → check_banned_words → check_banned_check → check_category → check_scene`，任一失败 → `ComplianceVerdict(approved=False)`（REQ-ADS-NFR-SAFETY-001 零逃逸）。
- 降级策略（REQ-ADS-FR-003/011，P5 实现）：LLM 解析失败重试 1 次；`ad_id` 不在候选集、`confidence<0.5`、候选集为空、过滤 REJECT → 返回结构化 `no_ad`（含原因码），不崩溃。

## 5. 已落地代码与数据（P0~P3）

### 源码
| 文件 | 要点 |
|---|---|
| `src/ads/schema.py` | AD_SCHEMA：必填字段、`ad_id` 格式 `ad_\d+`、设备枚举、`additionalProperties:false` |
| `src/ads/models.py` | `Ad` / `SceneRestrictions`（frozen dataclass） |
| `src/ads/repository.py` | `AdRepository.load`（逐条 jsonschema 校验 + ad_id 去重，违规抛 `AdLoadError`）、`get`、`filter_by_scene`（duck-typing scene） |
| `src/ads/banned_words.py` | `BannedWords.load/check`——**专属 `BannedWordsLoadError`**（fail-closed，含空表拒绝）；命中规则：**最长优先 → 同长取 Unicode 码点最小**（与词表顺序无关，`BUG-006` 修复） |
| `src/compliance/models.py` | `CheckResult` / `ComplianceVerdict`（`rejected_rule()` 定位首个失败） |
| `src/compliance/rules.py` | `SceneRules.load`：品类黑名单、夜间禁品类、校园禁品类 |
| `src/compliance/pipeline.py` | **五个**纯函数 check + `run_compliance` 管道（含 `banned_check` fail-closed 状态门） |
| `src/scene/schema.py` | SCENE_SCHEMA：time_slot/device 枚举、user_tags 可选 |
| `src/scene/models.py` | `Scene(time_slot, device, user_tags=())` |
| `src/scene/parser.py` | `parse_scene`：非法抛 `SceneInputError`；user_tags 去重保序 |

### 数据
| 文件 | 内容 |
|---|---|
| `data/ads.json` | **14 条素材**：原 8 条种子 + 6 条为规则可达性补齐（含 `medical` 品类、未声明 `not_night` 的 gaming、未声明 `not_campus` 的 adult、`banned_check=pending`/`banned` 各 1 条）。覆盖 8 个品类，全部规则分支可达 |
| `data/banned_words.json` | 24 个违禁词（15 个 2 字词 / 6 个 3 字词 / 3 个 4 字词） |
| `data/scene_rules.json` | `category_blacklist: [medical, financial_guarantee, adult]`、`night_blocked_categories: [gaming]`、`campus_blocked_categories: [adult]` |

### 其他
- `config.yaml`：LLM provider=mock、confidence_threshold=0.5、max_retries=1、数据路径、审计日志路径
- `scripts/demo_p1.py`：P1 功能演示（加载/查询/场景预筛/违禁词）

## 6. 测试（test/offline，**86 个全绿**）

- `test_ads.py`：加载条数与文件一致（**相对量断言**，不再写死条数）、**规则品类必有素材**（死规则防线）、缺文件/坏 JSON/顶层非数组/重复 ad_id、缺字段/非法枚举拒绝、get、夜间/校园/设备场景预筛、违禁词命中/未命中/最长命中
- `test_banned_words.py`（13）：**确定性**（等长命中顺序无关 / 24 种排列唯一 / 码点序规则 / 最长优先）、**load fail-closed**（缺文件/坏 JSON/顶层非数组/元素非字符串/空表）、**24 个词逐一反例**、对照样本不误拦
- `test_compliance.py`（20）：每项 Invariant 的**反例测试**——违禁词 REJECT、**`banned_check` 状态 REJECT（含 `pending`）**、**管道顺序契约**、金融/成人品类 REJECT、夜间游戏 REJECT、校园成人 REJECT、设备不符 REJECT、候选集外输出 REJECT、正常广告 APPROVE、`rejected_rule` 定位
- `test_scene.py`（8）：正常解析、缺字段/非法枚举/非对象/多余字段/标签类型错拒绝、去重保序
- `test_requirements_registry.py`（30）：注册表 ↔ 架构输入双向一致性；含 12 个负向测试
- 另有 `scripts/audit_implementation.py`（九组一致性审计，当前 **0 发现 / 48 通过**）

## 7. 提交历史（main，均已 push）

```
d85f910 feat: add P3 scene module (REQ-003) and replace FakeScene stubs with Scene
3ea7868 feat: add P2 compliance pipeline (REQ-006~009) and P1 demo script
edac673 feat: add P0 skeleton and P1 ads module (schema/load/query/banned words)
d097d34 docs: add V1 requirements, V2 bidding candidate requirements, V1 technical design
```

## 8. 技术决策摘要（正式 ADR 待补进 docs/architecture/）

| 决策 | 内容 |
|---|---|
| ADR-001 | V1 用 LLM 闭集选择 + 确定性兜底，不用 RAG（RAG 留 V3） |
| ADR-002 | 无数据库：JSON 文件 + 内存 + JSONL 日志 |
| ADR-003 | compliance 为纯函数管道，任一失败 REJECT/降级 |
| ADR-004 | LLM 输出必须 JSON schema 化，解析失败重试 1 次后降级 |
| ADR-005 | 离线测试一律 MockLLM，真实 LLM 只在 live 测试（评估可确定性 replay） |
| ADR-006 | 包布局：setuptools 平级顶层包，跨模块绝对导入 |

## 9. 待办计划（P4~P8）

### P4 selector（下一步）
- 文件：`src/selector/{__init__,models,prompt,client,mock,parser}.py`
- 核心：`LLMClient` 协议 `select(prompt) -> LLMOutput`；`LLMOutput(ad_id, reason, confidence)`；`MockLLM` 确定性实现（离线测试用）；`parse_llm_output` 严格 JSON 解析（失败抛错，REQ-005）；OpenAI 兼容 client 留 P8
- 注意：候选集内闭集选择（REQ-004）；低置信度交给上层降级（REQ-010）
- 测试：`test/offline/test_selector.py`（mock 确定性、解析成功/失败、schema 校验）

### P5 app/pipeline + CLI
- `app/recommend(scene, config) -> Recommendation`：预筛 → LLM 选择（重试 1 次）→ 合规过滤 → 渲染/降级 → 审计
- 降级统一返回结构化 `no_ad`（原因码）；CLI 用 argparse 接收场景 JSON

### P6 render + audit
- 输出结构（广告/无广告两种形态，REQ-012）；JSONL 追加写（REQ-013）

### P7 评估集 + 测试补齐
- `eval/eval_cases.json`（≥20 条：场景 → 期望品类/广告）+ `eval/eval_runner.py` replay
- 每个 fit criterion ≥1 测试（REQ-019/020）

### P8 真实 LLM + live
- OpenAI 兼容 client（需 API key，待定供应商）；`test/live` 冒烟测试

## 10. 待决策项（悬而未决）

1. **LLM 供应商**（P8 需要，考虑香港/内地可用性与成本）
2. 违禁词表扩充（当前 24 词 → 目标 20~50）
3. 素材扩充到 30~50 条（当前 8 条种子，需覆盖更多规则分支）
4. confidence 阈值 0.5 是否合适（P7 评估集调参）
5. 评估集口径：期望广告人工标注 vs 按品类匹配
6. 团队分工确认（`D:\CityU\SE\project\SE project.docx` 有 4 人角色草案：A 产品/流程、B 架构/AI、C 应用/集成、D 质量/治理）
7. V2 竞价细节（成交价规则 pay-as-bid vs 次价、分数公式）——需求已整理，落地前再定

## 11. 课程交付物 D1~D9 对照（现状）

| 交付物 | 现状 |
|---|---|
| D1 机器可读需求 | ✅ **完成**：`docs/req/requirements.yaml`（REQ-001~039）+ `req-schema.json` + `scripts/validate_requirements.py`（Schema gate 落地，含 17 个注册表测试，其中负向测试保证破坏必 FAIL） |
| D2 架构文档 | 仅 technical-design-v1.md；**11 类架构产物未建**（ADR/Invariants/Trace Matrix 等）。注意 `architecture-blueprint.md` 按课程要求须放**仓库根目录** |
| D3 编码治理 | 未开始（AGENTS.md / .opencode / .agent 等） |
| D4 验证治理 | test/ 雏形有；review-memo / debt-register / bug-diary 未建 |
| D5 Agent Transcripts | transcripts/ 空 |
| D6 Report | 未开始（含贡献权重表，>15 页 ≤1 万字） |
| D7 GitHub 仓库 | 已建、有 commit 历史；**分支保护 + 6 道 CI 门禁未配置** |
| D8 源码与测试 | src/（3 模块）+ test/offline 雏形；live 目录空 |
| D9 Prompt.md | 未创建 |

## 12. 环境与工具

- 本地 Windows；项目 `D:\CityU\SE\project\SE_Project`；产物副本在 `D:\CityU\SE\project\`（requirements-v1/v2、technical-design-v1）
- venv：`.venv`（Python 3.14.7；jsonschema 4.26.0、PyYAML 6.0.3、pytest 9.1.1）
- git：SSH 已认证（github 用户 StantonJoY）；无 .env/密钥入库
- 注意：`src/ad_recommender.egg-info/` 为 editable 安装产物，已被 `.gitignore` 排除
