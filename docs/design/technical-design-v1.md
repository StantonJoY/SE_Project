# 场景化广告推荐引擎 — V1 技术实现方案

> 状态：方案稿 · 2026-09-30 · 对应需求：`requirements-v1-draft.md`（REQ-001~020）
> 技术约束：**Python，无数据库，无重型框架**；离线可测优先。

---

## 1. 目标与边界

- 交付一个可离线运行、可测试的 V1 应用：场景特征输入 → 选广告 → 渲染输出，全程有确定性合规兜底。
- **不引入**：RAG/向量库、数据库、Web 前端、竞价（V2 再议）。
- **真实 AI 组件**：LLM 闭集选择。实现上先做接口 + mock（离线确定性），再接真实 LLM（live）。
- 规模：素材几十~上百条；单进程 CLI 即可跑通全流程。

---

## 2. 技术栈决策

| 项 | 选型 | 理由 |
|---|---|---|
| 语言 | Python 3.10+ | 团队熟悉；标准库够用 |
| 存储 | JSON 文件（`data/*.json`）+ 进程内内存 | 无数据库；素材量小、结构固定 |
| 审计日志 | JSONL 文件追加写 | 可重放、可 grep、可回放做评估 |
| 配置 | `config.yaml` / 环境变量 | 模型名、key、阈值单一来源 |
| LLM 接入 | 接口抽象（`LLMClient`）+ OpenAI 兼容 client | mock 跑离线测试，真实 API 跑 live |
| CLI | `argparse`（标准库） | 零额外依赖 |
| 校验 | `jsonschema`（唯一第三方运行时依赖） | 素材/输入/输出统一 schema 校验 |
| 测试 | `pytest`（开发依赖） | 标准 |

---

## 3. 数据模型（V1）

### 3.1 素材 `data/ads.json`

```json
{
  "ad_id": "ad_001",
  "title": "深夜咖啡外卖",
  "copy": "加班夜，一杯热美式送到家",
  "category": "food_delivery",
  "target_tags": ["student", "office_worker"],
  "scene_restrictions": {
    "not_night": false,
    "not_campus": false,
    "allowed_devices": ["mobile", "desktop"]
  },
  "banned_check": "pending"
}
```

- 字段含义：`category` 决定品类禁忌；`scene_restrictions` 是广告自身声明的硬约束；`target_tags` 供 LLM 参考做相关性判断。
- 加载期校验：字段完整、`ad_id` 唯一、类型正确（REQ-001/002）。

### 3.2 场景输入

```json
{ "time_slot": "night", "device": "mobile", "user_tags": ["student"] }
```

- 枚举约束：`time_slot ∈ {morning, afternoon, evening, night}`；`device ∈ {mobile, desktop, tablet}`（REQ-003）。

### 3.3 合规规则文件

- `data/banned_words.json`：违禁词表（REQ-008）
- `data/scene_rules.json`：品类禁忌 + 场景硬约束规则（REQ-007/009），如 `{"category_blacklist": ["medical", "financial_guarantee"], "night_blocked_categories": ["gaming"], "campus_blocked_categories": ["adult"]}`

---

## 4. 模块划分（模块 ↔ 架构元素一一对应）

```
src/
├── ads/         素材库模块：schema、加载、查询、违禁词表        ← REQ-001/002/008
├── scene/       场景模块：输入校验、规范化                       ← REQ-003
├── selector/    选择模块：LLM 接口 + mock + 真实实现 + 解析      ← REQ-004/005/010/016
├── compliance/  合规过滤模块：确定性纯函数管道                   ← REQ-006~009/016
├── render/      渲染输出模块：结果结构、JSON 序列化              ← REQ-012
├── audit/       审计日志模块：JSONL 追加写                       ← REQ-013
└── app/         编排模块：pipeline 串联 + CLI                    ← REQ-011/014/015
```

### 4.1 关键接口签名

```python
# ads/
class AdRepository:
    def load(self, path: Path) -> list[Ad]: ...      # REQ-001: 加载+去重校验
    def get(self, ad_id: str) -> Ad | None: ...
    def filter_by_scene(self, scene: Scene) -> list[Ad]: ...  # 规则预筛（场景硬约束）

# selector/
class LLMClient(Protocol):                            # 抽象，AI 组件边界
    def select(self, prompt: str) -> LLMOutput: ...   # 返回 {ad_id, reason, confidence}
class MockLLM(LLMClient): ...                         # 确定性，离线测试用
class OpenAIClient(LLMClient): ...                    # live 用，可替换
def parse_llm_output(raw: str) -> LLMOutput: ...      # 严格 JSON 解析，失败抛异常（REQ-005）

# compliance/
def check_banned_words(ad: Ad) -> CheckResult: ...    # REQ-008
def check_category(ad: Ad) -> CheckResult: ...        # REQ-007
def check_scene(ad: Ad, scene: Scene) -> CheckResult: ...  # REQ-009
def check_output(ad_id: str, candidates: list[Ad]) -> CheckResult: ...  # REQ-005 schema+存在性
def run_compliance(ad: Ad, scene: Scene, candidates: list[Ad]) -> ComplianceVerdict:
    # 纯函数管道：任一步 fail → REJECT；全部 pass → APPROVE（REQ-006）

# app/
def recommend(scene: Scene, config: Config) -> Recommendation:
    # 编排：预筛 → LLM 选择（重试1次）→ 合规过滤 → 渲染/降级 → 审计（REQ-011）
```

### 4.2 降级与重试策略（REQ-010/011）

| 触发条件 | 行为 |
|---|---|
| LLM 输出解析失败 | 重试 1 次 → 仍失败 → 返回 `no_ad` |
| LLM 输出 `ad_id` 不在候选集 | 拒绝该输出 → 返回 `no_ad` |
| `confidence < 0.5` | 视为不可信 → 返回 `no_ad` |
| 候选集为空 | 跳过 LLM，直接 `no_ad` |
| 合规过滤 REJECT | 丢弃该候选 → 若有第二候选可重试 1 轮 → 否则 `no_ad` |
| LLM 调用超时/异常 | 捕获 → `no_ad`（不崩溃，REQ-011） |

> V1 简化：降级一律返回结构化 `no_ad`（含原因码），不做"换候选再选"的复杂链路（V2 竞价再增强）。

---

## 5. 目录结构

```
ad-recommender/
├── README.md
├── config.yaml                  # 模型、key、阈值（confidence=0.5 等）
├── data/
│   ├── ads.json                 # 素材库（30~50 条）
│   ├── banned_words.json        # 违禁词表
│   └── scene_rules.json         # 品类禁忌 + 场景硬约束
├── src/
│   ├── ads/  scene/  selector/  compliance/  render/  audit/  app/
├── test/
│   ├── offline/                 # 确定性测试（不调 LLM，用 MockLLM）
│   └── live/                    # 真实 LLM 冒烟测试（标记 live）
├── eval/
│   ├── eval_cases.json          # 固定评估集（REQ-019，≥20 条）
│   └── eval_runner.py           # replay：跑评估集，输出通过率/违规数
├── prompts/
│   └── prompt_v1.0.yaml         # 版本化运行时 prompt
└── transcripts/                 # 课程 D5：agent 会话记录（后续）
```

---

## 6. 实施顺序（先做哪个）

按"**确定性骨架优先，AI 后接**"（对应课程 Sprint 2 → Sprint 3 的节奏）：

| 阶段 | 内容 | 依赖 | 验收（对应 REQ） |
|---|---|---|---|
| **P0** | 工程骨架：目录、`pyproject.toml`、pytest、config | — | 空测试可跑 |
| **P1** | **ads 素材库**（先做）：schema + 加载 + 查询 + 违禁词表 | P0 | REQ-001/002/008 |
| **P2** | **compliance 合规过滤**（紧随其后）：纯函数管道 + 失败测试 | P1 | REQ-006~009 |
| P3 | scene 场景模块：输入校验/枚举 | P0 | REQ-003 |
| P4 | selector：`LLMClient` 接口 + `MockLLM` + 解析器 | P2/P3 | REQ-004/005/010/016 |
| P5 | app/pipeline 串联 + CLI + 降级路径 | P4 | REQ-011/014/015 |
| P6 | render + audit 日志 | P5 | REQ-012/013 |
| P7 | 固定评估集 + 全量测试补齐（每个 fit criterion ≥1 测试） | P6 | REQ-019/020 |
| P8 | 接真实 LLM（OpenAI 兼容）+ live 冒烟测试 | P7 | REQ-004(live) |

**为什么先做 P1 ads + P2 compliance**：
1. 纯确定性、零外部依赖（不碰 LLM），当下即可写测试和失败测试；
2. 是整条管道的两个地基（数据源 + 安全边界），后续模块全部依赖它们；
3. 先跑通"安全边界"能尽早暴露 schema 和规则设计的问题，避免返工。

---

## 7. 关键设计决策（ADR 预告，正式版进 `docs/architecture/adr/`）

| ADR | 决策 | 理由 |
|---|---|---|
| ADR-001 | V1 用 LLM 闭集选择 + 确定性兜底，不用 RAG | 满足课程 AI 组件要求且最简；RAG 留 V3 |
| ADR-002 | 无数据库：JSON 文件 + 内存 + JSONL 日志 | 数据量小；省运维；审计可重放 |
| ADR-003 | 合规过滤为纯函数管道，任一步失败 → REJECT/降级 | 安全边界可离线测试、可形式化 |
| ADR-004 | LLM 输出必须 JSON schema 化，解析失败重试 1 次后降级 | 约束 AI 输出为可控数据（课程核心） |
| ADR-005 | 离线测试一律 MockLLM，真实 LLM 只在 live 测试 | 评估集可确定性 replay（REQ-015/019） |

---

## 8. 测试策略

- **三层验证**（课程 D4）：
  - 结构层：模块边界、`src/` 目录与架构元素一一对应
  - 回归层：全部既有测试零回归
  - 行为层：评估集 replay —— 合规零逃逸、`no_ad` 降级路径正确
- 关键失败测试（invariant 必须有"会失败"的测试）：
  - 违禁词广告被 REJECT（REQ-008 反例测试）
  - 敏感品类被 REJECT（REQ-007 反例测试）
  - LLM 返回非法 JSON → 降级 `no_ad`（REQ-005/010 反例测试）
  - LLM 返回候选集外 `ad_id` → 拒绝（REQ-004 反例测试）

---

## 9. 风险与待定项

- [ ] **LLM 供应商**：接哪家（OpenAI 兼容均可）？香港/深圳可用性？live 测试是否可行？
- [ ] **违禁词表范围**：先自造 20~50 词最小集，够不够讲清合规故事？
- [ ] **素材规模与分布**：30~50 条自造素材，品类分布怎么设计才能覆盖所有规则分支？
- [ ] **confidence 阈值**：0.5 是否合适？评估集调参。
- [ ] **配置文件 vs 硬编码**：V1 用 `config.yaml`，敏感 key 走环境变量。
- [ ] 真实 LLM 接入前的 live 测试需要 API key —— 团队成员谁提供/怎么管理（不入库）。
