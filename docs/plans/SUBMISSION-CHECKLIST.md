# 提交打包清单（ZIP）

> **用途**：把仓库打成提交包前的最后一遍核对。
> 脚本化部分可复制执行；判断项需人工确认。
> 日期：2026-11-25

---

## 1. 打包前的事实（实测）

| 项 | 值 |
|---|---|
| 工作树总大小（不含 `.git`） | **85 MB** |
| `.git` 目录 | **67 MB** |
| 最大单文件 | `evidence/v3/…/17-final-demo/video demo.mp4` **60 MB** |
| 次大 | `transcripts/raw/2026-10-06-session.v4.jsonl.zstd` 5.9 MB |
| 语料 | `data/corpus/tags.jsonl` 3.4 MB + `items.jsonl` 2.1 MB |
| 证据库 | 4 个 `.sqlite3` 共约 8.8 MB（**已入库**，是 V2 E2E 的原始记录） |

**判断点**：多数教学平台的附件上限是 20–50 MB。若上限低于 85 MB，只有两个选项：

1. **去掉 60 MB 视频**（保留 `evidence/…/17-final-demo/screenshots/` 的 10 张图，视频另存或给链接）；
2. 把视频压到 10 MB 以内（本机无 ffmpeg，需要你本地压）。

其余 25 MB 属于语料 + 证据，不建议再压——它们是"系统真的跑过"的依据。

---

## 2. 不要进包的东西

| 类别 | 路径 | 原因 |
|---|---|---|
| Git 元数据 | `.git/` | 67 MB，提交不需要历史（除非课程明确要求带 `.git`） |
| Python 缓存 | 全部 `__pycache__/`、`*.pyc` | 机器相关，会在别的机器上报错 |
| 测试缓存 | `.pytest_cache/` | 同上 |
| 运行日志 | `logs/` | 本地账本/审计残留，含路径信息 |
| 虚拟环境 | `.venv/`（若存在） | 体积大且不可移植 |

> `.gitignore` 已覆盖 `__pycache__`、`.pytest_cache`、`logs`、`*.egg-info`、`.venv`，
> 但**磁盘上仍存在**这些目录——直接压缩文件夹会把它们打进去，必须先删。

---

## 3. 清理命令（在仓库根执行）

```powershell
# 1) 删缓存与日志（可逆：下次运行会重建）
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force logs -ErrorAction SilentlyContinue

# 2) 确认工作区干净、无未跟踪文件
git status --porcelain          # 期望：空输出

# 3) 跑一遍门禁，确保交付的就是绿的
python -m pytest test/offline -q
python scripts/validate_requirements.py
python scripts/fitness_functions.py
python scripts/check_repo_completeness.py
```

---

## 4. 打包（排除 `.git` 与上述目录）

```powershell
$src = "D:\CityU\SE\project\SE_Project"
$out = "D:\CityU\SE\project\SE_Project_60989886.zip"
Remove-Item $out -ErrorAction SilentlyContinue
Compress-Archive -Path "$src\*" -DestinationPath $out `
  -CompressionLevel Optimal
```

> `Compress-Archive` 不支持排除规则，所以**必须先执行 §3 的清理**。
> 若要保留 `.git`（课程要求"仓库 + 报告"时可能需要），改用：
> `Compress-Archive -Path "$src\*" -DestinationPath $out` 前不要删 `.git`，但体积会到 150 MB。

---

## 5. 打完包后的自检

| # | 检查 | 命令 / 方法 |
|---|---|---|
| 1 | 包里没有缓存 | 解压后 `Get-ChildItem -Recurse -Directory -Filter __pycache__` 应为空 |
| 2 | 包里有报告 | 解压后根目录可见 `Report.md` |
| 3 | 包里有五份以上会话记录 | `transcripts/*.md` ≥ 5（现有 7） |
| 4 | 包里有证据目录 | `evidence/v3/` 与本目录 README |
| 5 | 解压后能跑测试 | 解压到新目录 → `pytest test/offline -q` → 679 passed |
| 6 | 报告无占位符 | 搜索 `student ID pending` 应为 0（现已为 0） |

---

## 6. 未完成的判断项（提交前必须清掉）

| 项 | 现状 | 动作 |
|---|---|---|
| ~~Gao Zhechun 的学号~~ | ✅ 已填 60880776（2026-11-25） | 完成 |
| 视频是否入包 | 60 MB | 按平台上限决定：保留 / 压缩 / 移除 |
| 报告是否按学号命名 | 现为 `Report.md` | 课程只要求"single markdown file"，命名按助教要求 |

---

## 7. 课程"Required Repository Structure"待人工核对

课程 PDF 第 5 节列出了要求的仓库结构，但该节正文在文本提取中不可读。
请对照 PDF 原文确认以下三项是否与要求一致：

- [ ] 报告位置（当前：仓库根 `Report.md`）
- [ ] 会话记录位置（当前：`transcripts/`）
- [ ] 证据位置（当前：`evidence/`）

若课程要求不同（例如报告需放 `docs/`），改位置后同步更新 `docs/README.md` 与 `Report.md` 的引用。
