# 原始会话记录（raw）

本目录保存 **agent 会话存储的原始字节**，不做任何改写。可读化版本在上一级目录。

| 文件 | 会话 | 大小 | 说明 |
|---|---|---|---|
| `2026-10-06-session.v4.jsonl.zstd` | `session-a8810df4-2c17-4226-b48e-1a453890c191` | ~5.9 MB | V1 从零构建（2026-10-06 → 11-02，39 轮 / 1149 次工具调用 / 16 次审批） |
| `2026-11-17-session.v4.jsonl.zstd` | `session-7cc4a18d-21fb-4881-a8a8-9fc484f2ecca` | ~1.1 MB | V2 整合与 CI 修复（12 轮 / 189 次工具调用） |

## 格式

DSH 每追加一批事件就写入一个独立的 zstd frame，因此文件是**多个 frame 首尾相接**，不是单个压缩流。
一般的 `zstd -d` 只解第一个 frame，会得到一个只有几行的残缺文件——这正是本目录需要 README 的原因。

解压后是 JSONL，每行一个事件，`type` 字段区分：

```
session                  会话元数据（id / cwd / version / 创建时间）
turn/start, turn/end     一轮对话的边界
user/message             用户输入（含平台注入的上下文，需按内容区分）
assistant/message        模型输出（text / reasoning / tool-call 三类内容块）
tool/call, tool/result   工具调用与结果（按 callId 配对）
approval/asked|decided   需要人工批准的提权请求与决定
todo/write               任务清单快照
job/registered|settled   后台作业生命周期
```

## 逐帧解压（Node.js ≥ 22，用内置 zstd）

```js
const fs = require('fs');
const zlib = require('zlib');
const buf = fs.readFileSync('2026-11-17-session.v4.jsonl.zstd');
const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);
const starts = [];
for (let i = 0; (i = buf.indexOf(MAGIC, i)) >= 0; i += 4) starts.push(i);
const out = [];
for (let s = 0; s < starts.length; ) {
  let done = false;
  for (let e = s + 1; e <= starts.length; e++) {
    const end = e < starts.length ? starts[e] : buf.length;
    try { out.push(zlib.zstdDecompressSync(buf.subarray(starts[s], end))); s = e; done = true; break; }
    catch {}
  }
  if (!done) s++;
}
process.stdout.write(Buffer.concat(out));
```

> 解压 + 排版脚本：`transcripts/tools/export-session.js`（可读化版本由它生成）。
