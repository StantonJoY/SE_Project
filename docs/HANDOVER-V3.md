# V3 交付说明（Handover · 给测试同学）

> **分支**：`v3`（领先 `main`；本轮 8 个提交）
> **一句话**：把 14 条手写广告换成 **5,000 条 Steam 真实语料**，加了**场景内容分级**，
> 并把**广告费 = 定价 5%** 接到 V2 竞价上。
> **状态**：代码与测试完成；`ADR-006` 仍是 `Proposed`，`TA-0005` 未签 —— 所以 CI 的 Gate 1 会红，属预期。

---

## 1. 先跑起来（三条命令）

```bash
# ① V1 + 真实语料（推荐先跑这个）
python -m app --corpus --time-slot night --device mobile --tag student

# ② V2 竞价 + 真实语料（自动用 config-v3.yaml）
python -m app.cli_v2 --corpus --request-id r1 --time-slot afternoon --device desktop --tag family

# ③ V3 固定评估集（14 条用例）
python eval/v3_runner.py
```

预期：① 出 `{"kind":"ad",...}` 或 `no_ad/compliance_rejected`；② 出带 `auction` 的成交结果；
③ `用例 14 条 | 通过 14 | 达成率 1.0000 | 合规逃逸 0`。

> 不需要装数据库、不需要网络。首次运行会加载 5,000 条语料（约 180 ms）。

---

## 2. V3 到底改了什么

| | V1 | V2 | **V3（本轮）** |
|---|---|---|---|
| 候选来源 | 14 条手写素材 | 同 V1 | **5,000 条真实 Steam 语料**（只读） |
| 候选怎么选 | 全部进 prompt | 全部进 prompt | **按场景标签命中数取 top-K**（V1 K=30 / V2 K=4） |
| 内容分级 | 只有品类黑名单 | 同 V1 | **`warnings ∪ descriptors` × 三档场景 + 年龄兜底** |
| 价格 | 无 | 固定 bid 文件 | **广告费 = 定价 5%，预算 = 20 次曝光** |

**一句话记住**：真实数据有坑（34 条空 genres、97% 年龄是 0、34% 只有 warnings 没有 descriptors），
我们用**确定性兜底**把坑填了，合规仍然是最终否决权。

---

## 3. 三条链路怎么走

```
items.jsonl + tags.jsonl（5,000 条）
      │ ① CorpusRepository.load（只读；不加载 description_clean）
      ▼
  CorpusItem  ──② select_candidates──▶ 按场景标签命中数取 top-K
      │ ③ corpus_to_ad
      ▼
   (Ad, CorpusFacts)          Ad → 管道；Facts → 合规旁路
      │
      ├─ V1：④ pipeline.recommend ──▶ LLM 建议 → ⑤ compliance（五步）→ 渲染 → 审计
      └─ V2：④ pipeline_v2 ──▶ 相关性 → 竞价（bid=5% 定价）→ ⑤ compliance → 原子结算
```

**合规五步没有变**：`output_exists → banned_words → banned_check → category → scene`。
内容分级塞在 `scene` 这一步**内部**，不是第六步。

---

## 4. 测试同学的可执行验收表

| # | 操作 | 预期 |
|---|---|---|
| 1 | `python -m app --corpus --time-slot night --device mobile --tag student` | 返回 `ad` 或 `no_ad/compliance_rejected`；stderr 有 `[corpus] 候选 30 条`；耗时 < 1 s |
| 2 | 同上，`--tag family` | 候选仍是 30 条；被拒条目的审计 `detail` 会写 `档位 family 禁止的内容 [...]` |
| 3 | 同上，`--tag gamer` | 被拒条目更少（竞技档只拦血腥/性），`detail` 写 `档位 competitive ...` |
| 4 | `--time-slot day`（非法枚举） | `no_ad` + `reason_code: scene_invalid`，进程退出码 0 |
| 5 | `python -m app.cli_v2 --corpus --request-id r1 ...` | 出 `ad` + `auction`（`bid_cents`/`price_cents`/`budget_before/after`） |
| 6 | 同一条命令**再跑一次**（同 `--request-id`、同输入、同 `--db`） | 返回**完全相同**的结果，`budget_after` 不变（幂等，不二次扣费） |
| 7 | **同一场景**、换一个 `--request-id`，沿用同一 `--db` | 预算接着扣：`5700 → 5400`（每条 300 分），证明跨请求持久 |
| 8 | `--request-id r1` 但**换场景** | `no_ad` + `reason_code: request_conflict`，不扣费 |
| 9 | `python eval/v3_runner.py` | 14/14、逃逸 0、p95 < 5 ms |
| 10 | `pytest test/offline -q` | **671 passed**，约 27 s |
| 11 | `python scripts/mutation_check.py` | **33/33** 全部被检出 |

> ⚠️ **三档之间不要直接比通过率**：`family` / `student` / `gamer` 映射到的标签不同，选出的候选集本来就不同。
> 实测同一时段/设备下：family 30 选 21、campus 30 选 10、competitive 30 选 24 —— 差异主要来自候选集，
> 不是档位松紧。判断档位是否生效，看**审计里的 `detail` 文案**（会写"档位 X 禁止的内容 [...]"）。
>
> 另：某些场景会**稳定**返回 `no_ad / compliance_rejected`（例：`night + mobile + gamer` 的 top-4 恰好都被拦下）。
> 这是内容分级在正常工作，不是故障。

---

## 5. 三档场景规则（被测对象）

| 档位 | 怎么触发 | 禁项 | 年龄上限 |
|---|---|---|---|
| `family` | `--tag family` / `parent` | 暴力、血腥、性、毒品、酒精、脏话、恐怖、赌博 | 0 |
| `campus` | `--tag student` / `teacher`，**以及默认** | 暴力、血腥、性、毒品、赌博 | 13 |
| `competitive` | `--tag gamer` / `esports` | 血腥、性 | 18 |

判定 = `content_warnings ∪ descriptor 映射` 与禁项求交集；年龄是**第二道**兜底。

值得单独验的一条：`Among Us`（`descriptors` 为空但 `warnings=[Violence, Blood]`）在 `family` 必须被拒
—— 只看 descriptors 的实现会放行它，这是本项目最看重的反例。

---

## 6. 已知限制（**测试时别当 bug**）

| # | 现象 | 原因 |
|---|---|---|
| 1 | 同一个场景反复跑，选中的总是同一条（如 `ad_16120`） | 离线用 `MockLLM`，按**字典序**选最小 ad_id。**不要用输出判断"相关性好不好"** |
| 2 | V2 语料模式候选只有 4 条 | V2 的 token 估算用 UTF-8 字节（比 V1 保守约 3 倍），2000 预算只装得下 4 条（ADR-006 D8） |
| 3 | V2 第一次跑较慢（约 1.4 s） | 要把 5,000 条报价 seed 进 SQLite；第二次约 1.3 s（含进程启动） |
| 4 | 换 `--db` 路径后预算"重置" | 账本是文件级持久（`logs/bidding-v3.sqlite3`），换路径等于换账本 |
| 5 | 免费游戏出价 1 分 | `Bid` 契约要求 `bid_cents ≥ 1`；免费/缺价保底 1 分 |
| 6 | 直接调 `run_compliance()` 不传 `policy` 时不做内容分级 | 这是刻意的：保证 V1 行为不变（有测试锁定） |
| 7 | 只有 5,000 条，不是 25,899 条 | 分层抽样（边界样本全含），见 `data/corpus/manifest.json` |
| 8 | CI 的 Gate 1 红 | `TA-0005` 未签（需要具名人类批准测试），不是代码问题 |

---

## 7. 出问题怎么查

| 症状 | 查什么 |
|---|---|
| 启动就报"配置校验失败" | `config.yaml` / `config-v3.yaml` 的字段与取值（fail loudly，不静默取默认） |
| `[corpus] 候选 0 条` | 场景标签在 `corpus.tag_mapping` 里没有映射（空匹配返回空，不硬凑） |
| `no_ad / compliance_rejected` | 看审计里的 `compliance.rejected_rule` 与 `detail`（会写明命中哪个标签/哪条规则） |
| `no_ad / budget_exceeded` | 候选太多超出 token 预算（V2 调 `corpus.top_k`） |
| `status_unknown` | 存储结果不确定，**用同一个 request_id 重试**，不要换 ID |
| 退出码 `2` | 启动期错误（配置/数据），stderr 有具体原因 |

审计日志：V1 默认 `logs/audit.jsonl`（`--audit` 可覆盖）；V2 的权威审计在 SQLite 账本里
（`requests` / `audit` 两张表）。

---

## 8. 文件地图（本轮新增/修改）

```
src/corpus/                  ← 新架构元素（第 9 个）
  models.py                   CorpusItem（不持有 description_clean）/ CorpusFacts
  repository.py               只读加载 + fail-closed（缺文件/坏 JSON/空/重复/缺标签）
  projection.py               corpus_to_ad（ad_id = ad_<item_id>；category 三级兜底）
  select.py                   确定性 top-K（命中数降序 + item_id 升序）
  pricing.py                  bid = max(1, round(price×5%))、budget = bid×20（唯一来源）
  config.py                   K ≤ 50（由 token 预算反推）、预算次数、场景标签映射

src/compliance/content_rules.py   ContentRules / ContentTier / ContentPolicy
src/compliance/pipeline.py        run_compliance(..., policy=None)、check_scene(..., policy=None)
src/app/cli.py                    --corpus 接线（V1）
src/app/cli_v2.py                 --corpus 接线（V2，自动用 config-v3.yaml）
src/app/pipeline.py               透传 content_policy
src/app/pipeline_v2.py           candidate_ids（top-K 收窄）+ content_policy

data/corpus/{items,tags}.jsonl    5,000 条（items 2.1 MB + tags 3.4 MB）
data/corpus/manifest.json         源行数 / 抽样规则 / 两份文件 SHA-256
data/corpus/demo_ids.txt          必须保留的 30 条 demo id
data/bids-corpus.json             5,000 条报价（bid/budget，由 pricing 派生）
data/scene-content-rules.yaml     三档禁项 + 年龄上限 + descriptor 语义（safety-critical）
config-v3.yaml                    V2 语料模式配置（top_k=4、独立账本）

eval/v3_cases.json + v3_runner.py 14 条固定评估（含 3 条负例）
scripts/build_corpus_subset.py    子集构建（确定性，双跑逐字节一致）
scripts/build_bids_v3.py          报价 sidecar 生成
```

---

## 9. 复现与重抽样

```bash
# 从全量 25,899 条重新生成 5,000 条子集（需要全量文件，仓库里没有）
python scripts/build_corpus_subset.py \
    --items <全量 items.jsonl> --tags <全量 tags.jsonl> \
    --out-dir data/corpus --n 5000

# 重新生成报价（语料或 5% 口径变了要重跑）
python scripts/build_bids_v3.py
```

抽样规则（确定性，无随机）：必含 30 条 demo、**空 genres 全部 34 条**、**`required_age ≥ 13` 全部 715 条**、
每个 `content_descriptors` 组合 200 条、免费游戏 200 条，余量按主 genre 轮转。

---

## 10. 提示词现状（ADR-006 D9，**测试同学重点看**）

### 10.1 它长什么样

V1 是**六层**结构（`## SYSTEM / ## INSTRUCTIONS / ## RETRIEVED / ## HISTORY / ## STATE / ## USER`）：

```
## INSTRUCTIONS
约束（不可协商）：
1) 只能从候选列表中选择 ad_id，不得输出列表之外的任何条目；
2) 不得自创或改写候选条目的标题、品类与标签；
3) 必须输出 JSON，字段恰为 ad_id / reason / confidence，不得增减字段；
4) 你的输出仅为建议，是否展示由确定性合规层裁决；
5) 只依据候选行给出的品类与标签判断匹配度，**不得使用你对这些作品的外部知识**。

## RETRIEVED
- ad_115100 | RPG | Costume Quest | tags: Fantasy,Comedy,Turn-Based Combat,...
（30 行，V1 K=30）

## HISTORY
[HISTORY] 不适用（无状态单轮推荐）

## STATE
[场景] 时段=afternoon（下午） / 设备=desktop（桌面） / 用户标签=family；家庭场景，偏好温和、合家欢内容
```

V2 是两段（system + 一段 JSON 用户消息），只传 4 个候选，`relevance` 定义为"与场景标签的匹配度，
**不是**作品知名度。

### 10.2 本轮改了什么（只改事实缺陷，不做调优）

| # | 改动 | 为什么 |
|---|---|---|
| 1 | 场景摘要带语义（`family` → "家庭场景，偏好温和内容"） | 原来只给裸枚举，模型不知道含义 |
| 2 | 「广告」→「候选条目（本轮素材为游戏条目）」 | 语义漂移 |
| 3 | 新增第 5 条约束：**不得使用对外部知识** | 名作先验会压过标签匹配 |
| 4 | `HISTORY` 层去掉内部文档路径，缩成一行 | 纯噪音、占预算 |

版本号：`PROMPT_TEMPLATE_VERSION = ctx-v1.1`、`RELEVANCE_PROMPT_VERSION = relevance-v2.2`
（审计的 `provenance.prompt_version` 会记录，便于以后对比）。

**明确没做**：没把合规禁项写进 prompt（那是合规的职责），没加摘要/示例（预算不够）。

### 10.3 交给测试同学的验证清单

> 前提：离线 replay 用的是 `MockLLM`（按字典序选 `ad_id`），**改 prompt 对离线结果零影响**。
> 下面这些只能在**真实模型**下做（P8 接入后）。

| # | 怎么测 | 想证明什么 |
|---|---|---|
| 1 | 同一场景跑 20 次，统计"选中条目的标签命中数"分布 | 模型是按标签匹配选，还是在乱选 |
| 2 | 造 5 条**标题诱导**样本（标题写 "Family Fun" 但标签是 `Gore`），看模型是否被标题带偏 | 外部知识/标题先验是否仍占上风 |
| 3 | 造 5 条**名作对照**（`Counter-Strike 2` vs 冷门但标签更匹配的条目） | 是否按标签而不是知名度 |
| 4 | 检查审计 `provenance.prompt_version` | 确认用的是 `ctx-v1.1` / `relevance-v2.2` |
| 5 | 回归：`eval_runner.py` / `v2_runner.py` / `v3_runner.py` | 改 prompt 后旧分区不退化 |

### 10.4 改 prompt 的红线（别踩）

1. **不要动输出 schema**（`ad_id / reason / confidence`、`scores[]`）——解析器是严格闭集；
2. **不要把合规禁项写进 prompt**——安全边界在合规层，不由模型自律；
3. **改完必须 bump 版本号**并重跑三套 replay（`check_semantic_eval.py` 会因 prompt 变更而触发）；
4. **不要在 `RETRIEVED` 里塞长文本**——V1 已用 1567/2000 token，再加就触发压缩甚至 `budget_exceeded`；
5. **不要用离线 Mock 结果证明"prompt 变好了"**——它根本不读语义。

---

## 11. 待办（不在本轮代码范围）

| 项 | 说明 |
|---|---|
| `TA-0005` | 具名人类的测试前置批准；签了 Gate 1 才会绿 |
| `ADR-006` | 状态 `Proposed` → `Accepted`（具名批准） |
| 分支保护 | 收尾阶段再开（见 `pre_TODO.md` P0-3） |
| `v3 → main` 的 PR | 建议在 TA-0005 之后 |
