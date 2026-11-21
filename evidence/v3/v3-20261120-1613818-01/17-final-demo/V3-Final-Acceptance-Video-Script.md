# V3 最终验收演示视频脚本

> 版本：V3 最终验收
> 测试代码 Commit：`161381887e421a121cd2878fcbf397d42a8ac818`
> 文档/证据 Commit：`4da29339ae7e150302fe7123422bf78fa8135c04`
> 当前工作区 HEAD：`4da2933`（该 commit 只修改测试文档，不改变被测代码）
> Run ID：`v3-20261120-1613818-01`
> 录制方式：1080p 终端 + evidence 画面
> 目标时长：9–11 分钟

## 1. 录制前准备

```powershell
Set-Location 'E:\cityu\SE\project\SE_Project-v3-test'

$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

$RunId = 'v3-20261120-1613818-01'
$Evidence = "E:\cityu\SE\project\SE_Project-v3-test\evidence\v3\$RunId"
$Demo = "$Evidence\17-final-demo"

New-Item -ItemType Directory -Force $Demo | Out-Null
```

录制规则：

- 不显示 API key、Authorization 或 endpoint 中的敏感参数。
- Live semantic 部分展示已保存的真实模型结果，不现场调用 API。
- V1 统一标注为 `Mock / Offline`，不写 live。
- Gate 1 统一标注为 `DEFERRED / FAIL`，不能隐藏。
- 最终结论必须显示 `PASS_WITH_LIMITATIONS`，不能写成课程交付完全 PASS。

## 2. 时间线

### 0:00–0:40 · 基线与范围

展示：

```powershell
git branch --show-current
git rev-parse HEAD
python --version
python -m pip show ad-recommender
```

口述重点：

```text
当前 HEAD 是 4da2933，为 docs/evidence commit；
实际测试代码是 1613818；
本轮验证 V3：5,000 条 Steam 语料、内容分级、
V2 定价与预算、完整回归和真实 relevance prompt。
V1 是 Mock/Offline，本视频不声称 V1 live。
```

### 0:40–1:40 · 真实语料与 manifest

展示：

```powershell
Get-Content 'data\corpus\manifest.json' -Raw -Encoding UTF8
```

口述重点：

```text
5,000 条语料；
items/tags 各 5,000 行；
空 genres 总共 34 条；
required_age >= 13 总共 715 条；
manifest 的 items/tags SHA-256 已与实际最终文件对齐。
```

### 1:40–2:40 · V1 corpus 正常与非法场景

运行：

```powershell
python -m app --corpus --time-slot night --device mobile --tag student --audit "$Demo\v1-normal.audit.jsonl" 1> "$Demo\v1-normal.stdout.json" 2> "$Demo\v1-normal.stderr.txt"
"V1_NORMAL_EXIT=$LASTEXITCODE"

python -m app --corpus --time-slot day --device mobile --audit "$Demo\v1-invalid.audit.jsonl" 1> "$Demo\v1-invalid.stdout.json" 2> "$Demo\v1-invalid.stderr.txt"
"V1_INVALID_EXIT=$LASTEXITCODE"
```

展示结果：

```text
正常：kind=ad，ad_16120，audit=1，候选 30 条
非法：kind=no_ad，reason_code=scene_invalid，exit=0
```

说明 V1 的 stdout 需要 UTF-8 环境，本次录制已设置 `PYTHONIOENCODING=utf-8`。

### 2:40–3:40 · 内容分级与年龄兜底

运行：

```powershell
python -m pytest test/offline/test_v3_compliance.py -q -p no:cacheprovider
"COMPLIANCE_EXIT=$LASTEXITCODE"
```

口述重点：

```text
family / campus / competitive 三档；
warnings 与 descriptors 取并集；
Among Us 由 warnings 一侧拦截；
required_age 是第二道兜底；
合规五步顺序不变。
```

### 3:40–5:10 · V2 定价、竞价与预算

运行：

```powershell
$DB = "$Demo\v2-demo.sqlite3"

python -m app.cli_v2 --corpus --request-id v3-demo-1 --time-slot afternoon --device desktop --tag family --db $DB 1> "$Demo\v2-r1.stdout.json" 2> "$Demo\v2-r1.stderr.txt"
"V2_R1_EXIT=$LASTEXITCODE"

python -m app.cli_v2 --corpus --request-id v3-demo-1 --time-slot afternoon --device desktop --tag family --db $DB 1> "$Demo\v2-r1-replay.stdout.json" 2> "$Demo\v2-r1-replay.stderr.txt"
"V2_REPLAY_EXIT=$LASTEXITCODE"

python -m app.cli_v2 --corpus --request-id v3-demo-1 --time-slot night --device mobile --tag gamer --db $DB 1> "$Demo\v2-conflict.stdout.json" 2> "$Demo\v2-conflict.stderr.txt"
"V2_CONFLICT_EXIT=$LASTEXITCODE"
```

口述重点：

```text
bid = max(1, round(price × 5%))；
budget = bid × 20；
相同 request_id 重放不二次扣费；
相同 request_id 换场景返回 request_conflict；
预算账本不能透支。
```

### 5:10–6:20 · 全量回归、replay 与 mutation

展示证据摘要，不重新打印完整测试输出：

```powershell
$JUnit = 'evidence\v3\v3-20261120-1613818-01\12-post-ruff\offline-full.junit.xml'
[xml]$x = Get-Content $JUnit -Raw -Encoding UTF8
[pscustomobject]@{
    Tests = $x.testsuites.testsuite.tests
    Failures = $x.testsuites.testsuite.failures
    Errors = $x.testsuites.testsuite.errors
} | Format-List
```

展示已保存的 replay 和 mutation：

```powershell
Get-Content 'evidence\v3\v3-20261120-4d0479f-01\09-replay\v1-replay.stdout.txt' -Tail 8
Get-Content 'evidence\v3\v3-20261120-4d0479f-01\09-replay\v2-replay.stdout.txt' -Tail 8
Get-Content 'evidence\v3\v3-20261120-4d0479f-01\09-replay\v3-replay.stdout.txt' -Tail 8
Get-Content 'evidence\v3\v3-20261120-4d0479f-01\10-mutation\mutation.stdout.txt' -Tail 12
```

口述数字：

```text
675 tests passed
V1 replay: 11/11 + 14/14
V2 replay: 18 cases，violations=0
V3 replay: 14/14，violations=0
Mutation: 33/33
```

### 6:20–7:20 · 静态检查与覆盖率

展示：

```powershell
Get-ChildItem 'evidence\v3\v3-20261120-1613818-01\14-final-static' -Filter '*.stdout.txt' | Select-Object Name,Length
Get-Content 'evidence\v3\v3-20261120-1613818-01\15-coverage\v3-coverage.stdout.txt' -Tail 30
```

口述数字：

```text
Ruff、mypy、dependencies、Schema、fitness、
repository completeness、safety paths、implementation audit：PASS
V3 new module coverage：86% total
```

### 7:20–8:20 · Live prompt semantic quality

展示已保存结果，不现场调用 API：

```powershell
Get-Content 'evidence\v3\v3-20261120-1613818-01\16-live-prompt\live-prompt-multi-scene-results.json' -TotalCount 20 -Encoding UTF8
Get-Content 'evidence\v3\v3-20261120-1613818-01\16-v1-live-prompt\v1-live-semantic-results.json' -TotalCount 20 -Encoding UTF8
```

展示 V2 结论：

```text
prompt version = relevance-v2.2
6 scenes × 5 runs = 30/30 structural
title-bait = 5/5
known-title = 5/5
semantic quality = PASS_WITH_LIMITATIONS
```

展示 V1 test-only 结论：

```text
prompt version = ctx-v1.1
6 scenes × 3 runs = 18/18 structural
all outcomes = ad
test-only live semantic quality = PASS_WITH_LIMITATIONS
```

明确限制：

```text
只测试 deepseek-flash；
只使用一个 provider；
样本不是完整 human-labeled Steam gold set；
V1 产品默认路径仍是 Mock/Offline；
V1 live 是 test-only harness，不是产品 CLI 默认路径。
```

### 8:20–9:20 · Gate 1 与最终结论

展示：

```powershell
Get-Content 'evidence\v3\v3-20261120-1613818-01\13-governance\test-approval.stdout.txt' -Encoding UTF8
```

明确说明：

```text
Gate 1 当前为 DEFERRED / FAIL；
原因包括 mapping/evidence 缺口和 TA-0005 未签；
这不是 V3 功能失败，但会阻断课程正式交付。
```

最终屏幕上显示：

```text
V3 Functional Testing: PASS
V3 Full Regression: PASS（675）
V3 Replay: PASS
V3 Mutation: PASS（33/33）
V3 Static Checks: PASS
V3 Coverage: RECORDED（86%）
V2 Live Prompt: PASS_WITH_LIMITATIONS
V1 Live Prompt (test-only): PASS_WITH_LIMITATIONS
V1 Product Default Path: Mock / Offline
V3 Governance: DEFERRED / FAIL
V3 Course Delivery Readiness: CHANGES REQUIRED
```

## 3. 录后文件

建议保存：

```text
evidence/v3/v3-20261120-1613818-01/17-final-demo/
├── V3-Final-Acceptance.mp4
├── 01-baseline.txt
├── 02-corpus.txt
├── 03-v1-e2e.txt
├── 04-v2-e2e.txt
├── 05-tests-replay-mutation.txt
├── 06-live-prompt.txt
├── 07-gates-limitations.txt
├── checksums.sha256
└── README.md
```
