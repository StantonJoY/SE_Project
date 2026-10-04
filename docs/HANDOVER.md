# CS5351 项目交接文档（HANDOVER）

> 快照日期：2026-10-04 · 新对话开场先读本文件再动手，可无缝继续。
> 配套文档：`docs/req/requirements-v1-draft.md`（REQ-001~020）、`docs/req/requirements-v2-bidding-draft.md`（REQ-021~039）、`docs/design/technical-design-v1.md`（V1 技术方案）。

---

## 1. 项目一句话

**场景化广告推荐引擎**（CS5351 Agentic Software Engineering Project）：给定广告素材库与用户场景特征（时段/设备/用户标签），系统选出一条广告渲染展示。核心命题：**AI 做推荐决策（LLM）+ 确定性代码做合规兜底**——"AI 是顾问，代码是执行官"。

## 2. 30 秒速览

| 项 | 状态 |
|---|---|
| 版本 | **V1 基线**（无 RAG、无竞价）；V2=竞价候选、V3=RAG 占位 |
| 技术栈 | Python 3.10+（本地 3.14.7）、**无数据库**（JSON 文件 + JSONL 日志）、jsonschema + pytest |
| 进度 | **P0~P3 完成**：骨架 / ads 素材库 / compliance 合规 / scene 场景 |
| 测试 | **34 个全绿**（ads 14 + compliance 12 + scene 8），0.98s |
| 下一步 | **P4 selector**：LLMClient 接口 + MockLLM + 输出解析（REQ-004/005/010/016） |
| 仓库 | `D:\CityU\SE\project\SE_Project`，remote `git@github.com:StantonJoY/SE_Project.git` |

常用命令（仓库根目录）：
```
.\.venv\Scripts\python.exe -m pytest test/offline     # 跑全量离线测试
.\.venv\Scripts\python.exe scripts\demo_p1.py          # 跑 P1 功能演示
```

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
   output_exists → banned_words → category → scene，任一失败 REJECT
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

- compliance 为**确定性纯函数管道**：`check_output → check_banned_words → check_category → check_scene`，任一失败 → `ComplianceVerdict(approved=False)`（REQ-006 零逃逸）。
- 降级策略（REQ-010/011，P5 实现）：LLM 解析失败重试 1 次；`ad_id` 不在候选集、`confidence<0.5`、候选集为空、过滤 REJECT → 返回结构化 `no_ad`（含原因码），不崩溃。

## 5. 已落地代码与数据（P0~P3）

### 源码
| 文件 | 要点 |
|---|---|
| `src/ads/schema.py` | AD_SCHEMA：必填字段、`ad_id` 格式 `ad_\d+`、设备枚举、`additionalProperties:false` |
| `src/ads/models.py` | `Ad` / `SceneRestrictions`（frozen dataclass） |
| `src/ads/repository.py` | `AdRepository.load`（逐条 jsonschema 校验 + ad_id 去重，违规抛 `AdLoadError`）、`get`、`filter_by_scene`（duck-typing scene） |
| `src/ads/banned_words.py` | `BannedWords.load/check`——返回**最长命中词**（更具体） |
| `src/compliance/models.py` | `CheckResult` / `ComplianceVerdict`（`rejected_rule()` 定位首个失败） |
| `src/compliance/rules.py` | `SceneRules.load`：品类黑名单、夜间禁品类、校园禁品类 |
| `src/compliance/pipeline.py` | 四个纯函数 check + `run_compliance` 管道 |
| `src/scene/schema.py` | SCENE_SCHEMA：time_slot/device 枚举、user_tags 可选 |
| `src/scene/models.py` | `Scene(time_slot, device, user_tags=())` |
| `src/scene/parser.py` | `parse_scene`：非法抛 `SceneInputError`；user_tags 去重保序 |

### 数据
| 文件 | 内容 |
|---|---|
| `data/ads.json` | 8 条种子素材（覆盖 food_delivery/gaming/education/retail/adult/financial_guarantee/subscription，含夜间/校园/设备限制分支） |
| `data/banned_words.json` | 24 个违禁词 |
| `data/scene_rules.json` | `category_blacklist: [medical, financial_guarantee, adult]`、`night_blocked_categories: [gaming]`、`campus_blocked_categories: [adult]` |

### 其他
- `config.yaml`：LLM provider=mock、confidence_threshold=0.5、max_retries=1、数据路径、审计日志路径
- `scripts/demo_p1.py`：P1 功能演示（加载/查询/场景预筛/违禁词）

## 6. 测试（test/offline，34 个全绿）

- `test_ads.py`（14）：加载条数、缺文件/坏 JSON、重复 ad_id、缺字段/非法枚举拒绝、get、夜间/校园/设备场景预筛、违禁词命中/未命中/最长命中
- `test_compliance.py`（12）：每项 Invariant 的**反例测试**——违禁词 REJECT、金融/成人品类 REJECT、夜间游戏 REJECT、校园成人 REJECT、设备不符 REJECT、候选集外输出 REJECT、正常广告 APPROVE、管道 rejected_rule 定位
- `test_scene.py`（8）：正常解析、缺字段/非法枚举/非对象/多余字段/标签类型错拒绝、去重保序

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
| D1 机器可读需求 | 草案 md 已有；**未转 requirements.yaml + req-schema.json** |
| D2 架构文档 | 仅 technical-design-v1.md；**11 类架构产物未建**（ADR/Invariants/Trace Matrix 等） |
| D3 编码治理 | 未开始（AGENTS.md / .opencode / .agent 等） |
| D4 验证治理 | test/ 雏形有；review-memo / debt-register / bug-diary 未建 |
| D5 Agent Transcripts | transcripts/ 空 |
| D6 Report | 未开始（含贡献权重表，>15 页 ≤1 万字） |
| D7 GitHub 仓库 | 已建、有 commit 历史；**分支保护 + 6 道 CI 门禁未配置** |
| D8 源码与测试 | src/（3 模块）+ test/offline 雏形；live 目录空 |
| D9 Prompt.md | 未创建 |

## 12. 环境与工具

- 本地 Windows；项目 `D:\CityU\SE\project\SE_Project`；产物副本在 `D:\CityU\SE\project\`（requirements-v1/v2、technical-design-v1）
- venv：`.venv`（Python 3.14.7；jsonschema 已装，pytest 9.1.1）
- git：SSH 已认证（github 用户 StantonJoY）；无 .env/密钥入库
- 注意：`src/ad_recommender.egg-info/` 为 editable 安装产物，已被 `.gitignore` 排除
