# SE Project — 场景化广告推荐引擎（Ad Recommendation Engine）

CS5351 Agentic Software Engineering Project · 2026-2027

在人类监督下，用 AI coding agent 构建一个**场景化广告推荐引擎**：
给定广告素材库与用户场景特征（时段 / 设备 / 用户标签），系统选出一条广告并渲染展示。
核心命题：**AI 做推荐决策（LLM）+ 确定性代码做合规兜底**。

## 版本演进

| 版本 | 内容 | 状态 |
|---|---|---|
| V1 | 规则预筛 → LLM 闭集选择 → 合规过滤 → 渲染（无 RAG、无竞价） | 基线（需求 + 技术方案已定） |
| V2 | 报价竞价框架：LLM 降级为相关性建议，竞价引擎确定性定胜负 | 需求候选 |
| V3 | RAG 场景向量召回 | 占位 |

## 文档索引

| 文档 | 路径 | 说明 |
|---|---|---|
| V1 需求与功能点 | `docs/req/requirements-v1-draft.md` | REQ-001~020，含验收标准 |
| V2 竞价候选需求 | `docs/req/requirements-v2-bidding-draft.md` | REQ-021~039，硬性数学校验 |
| V1 技术实现方案 | `docs/design/technical-design-v1.md` | 模块划分、实施顺序 P0~P8 |

## 目录规划（对齐课程要求）

```
SE_Project/
├── README.md
├── AGENTS.md                  # coding-agent 治理入口（D3，后续）
├── Prompt.md                  # 静态启动 prompt（D9，后续）
├── docs/
│   ├── req/                   # 需求（D1：requirements.yaml + req-schema.json）
│   ├── architecture/          # 架构文档（D2，11 类产物）
│   ├── design/                # 设计草案
│   └── code-governance/       # 编码与验证治理（D3/D4）
├── src/                       # 源代码（D8，后续）
├── test/
│   ├── offline/               # 确定性测试
│   └── live/                  # 依赖 API 的测试
└── transcripts/               # agent 会话记录（D5，后续）
```
