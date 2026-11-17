#!/usr/bin/env node
/**
 * 把 DSH（DeepSeek Harness）会话存储导出为可读的 Markdown 转录稿。
 *
 * 用法：
 *   node transcripts/tools/export-session.js <session.v4.jsonl.zstd> <output.md>
 *
 * 为什么需要它：
 *   DSH 每追加一批事件就写一个独立的 zstd frame，整个文件是多帧首尾相接。
 *   普通 zstd 解压只会得到第一个 frame（几行元数据）。这里逐帧解压后再排版。
 *
 * 排版约定（保持可核查，不做润色）：
 *   - 用户消息、助手正文原样保留；助手正文超过 MAX_ASSISTANT 字符时截断并标注
 *   - 省略模型内部 reasoning 块（体积原因），但不影响 human↔agent 交互的还原
 *   - 工具调用按 callId 与结果配对，参数与结果各截断到一行
 *   - 平台注入的上下文（runtime context / system-reminder 等）标注为“非人类输入”
 */
'use strict';

const fs = require('fs');
const zlib = require('zlib');
const path = require('path');

const MAX_ASSISTANT = 2500;
const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);

function decodeFrames(buf) {
  const starts = [];
  for (let i = 0; (i = buf.indexOf(MAGIC, i)) >= 0; i += 4) starts.push(i);
  const chunks = [];
  for (let s = 0; s < starts.length; ) {
    let ok = false;
    for (let e = s + 1; e <= starts.length; e++) {
      const end = e < starts.length ? starts[e] : buf.length;
      try {
        chunks.push(zlib.zstdDecompressSync(buf.subarray(starts[s], end)));
        s = e;
        ok = true;
        break;
      } catch {
        /* 帧内出现魔数假起点时，尝试更长的切片 */
      }
    }
    if (!ok) s++;
  }
  return Buffer.concat(chunks).toString('utf-8');
}

const ts = (ms) =>
  Number.isFinite(ms) ? new Date(ms).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '—';
const oneLine = (s, n) => {
  const t = String(s ?? '').replace(/\s+/g, ' ').trim();
  return t.length > n ? t.slice(0, n) + '…' : t;
};
const INJECTED = /^Current runtime context|^<system-reminder>|^Additional instructions from:|^Time sampled/;

function main(argv) {
  const [input, output] = argv;
  if (!input || !output) {
    console.error('用法: node export-session.js <session.v4.jsonl.zstd> <output.md>');
    return 2;
  }
  const recs = decodeFrames(fs.readFileSync(input))
    .split('\n')
    .filter(Boolean)
    .map((l) => JSON.parse(l));

  const head = recs.find((r) => r.type === 'session') || {};
  const times = recs.map((r) => r.time).filter(Number.isFinite);
  const results = new Map();
  const decisions = new Map();
  const todos = [];
  const turns = new Map();
  let model = '';
  let current = 0;

  const T = (n) => {
    if (!turns.has(n)) turns.set(n, { start: null, users: [], assistant: [], calls: [], approvals: [] });
    return turns.get(n);
  };

  for (const r of recs) {
    const d = r.data || {};
    switch (r.type) {
      case 'turn/start':
        current = d.turn;
        T(current).start = r.time;
        break;
      case 'user/message':
        T(current || 1).users.push(
          (d.content || []).filter((c) => c.type === 'text').map((c) => c.text).join('\n'),
        );
        break;
      case 'assistant/message': {
        const blocks = d.message?.content || [];
        if (d.message?.source?.model) model = d.message.source.model;
        const text = blocks.filter((c) => c.type === 'text').map((c) => c.text).join('\n').trim();
        if (text) T(d.turn).assistant.push({ step: d.step, text });
        for (const c of blocks.filter((b) => b.type === 'tool-call')) {
          T(d.turn).calls.push({ name: c.name, args: c.arguments, callId: c.id });
        }
        break;
      }
      case 'tool/result':
        results.set(d.message?.toolCallId, d.message);
        break;
      case 'approval/asked':
        T(current).approvals.push({ id: d.id, reason: d.reason, outcome: null });
        break;
      case 'approval/decided':
        decisions.set(d.id, d.outcome);
        break;
      case 'todo/write':
        todos.push({ time: r.time, items: d.todos || d.items || [] });
        break;
    }
  }
  for (const t of turns.values()) for (const a of t.approvals) a.outcome = decisions.get(a.id) || '未记录';

  const sorted = [...turns.entries()].sort((a, b) => a[0] - b[0]);
  const calls = sorted.reduce((n, [, t]) => n + t.calls.length, 0);
  const approvals = sorted.reduce((n, [, t]) => n + t.approvals.length, 0);

  const argSummary = (raw) => {
    let a = {};
    try {
      a = JSON.parse(raw || '{}');
    } catch {
      return oneLine(raw, 120);
    }
    const pick =
      a.description || a.command || a.file_path || a.path || a.pattern || a.url || a.prompt || a.job_id || a.name || '';
    return oneLine(pick || JSON.stringify(a), 150);
  };

  const out = [];
  out.push(`# Agent 会话记录 · ${path.basename(output, '.md')}`);
  out.push('');
  out.push('> **D5 交付物** · 由 `transcripts/tools/export-session.js` 从 DSH 会话存储导出，仅排版，不改写内容。');
  out.push('> 省略模型内部 `reasoning` 块；助手正文超长截断；工具参数与结果截断并以 `…` 标注。');
  out.push('> 原始记录：`raw/`（多帧 zstd + JSONL，解压方法见 `raw/README.md`）。');
  out.push('');
  out.push('| 项 | 值 |');
  out.push('|---|---|');
  out.push(`| 会话 ID | \`${head.id || '—'}\` |`);
  out.push(`| 工作区 | \`${head.cwd || '—'}\` |`);
  out.push(`| 时间 | ${ts(Math.min(...times))} → ${ts(Math.max(...times))}（Asia/Shanghai） |`);
  out.push(`| 模型 | ${model || '（未记录）'} |`);
  out.push(`| 轮次 / 工具调用 / 审批交互 | ${sorted.length} / ${calls} / ${approvals} |`);
  out.push('');
  out.push('---');
  out.push('');

  for (const [no, t] of sorted) {
    out.push(`## 轮次 ${no} · ${ts(t.start)}`);
    out.push('');
    for (const u of t.users) {
      if (!u.trim()) continue;
      if (INJECTED.test(u.trim())) {
        out.push(`*〔平台注入，非人类输入〕${oneLine(u, 160)}*`);
        out.push('');
        continue;
      }
      out.push('**用户：**');
      out.push('');
      out.push(u.split('\n').map((l) => '> ' + l).join('\n'));
      out.push('');
    }
    for (const a of t.assistant) {
      out.push(`**助手（step ${a.step}）：**`);
      out.push('');
      out.push(a.text.length > MAX_ASSISTANT ? a.text.slice(0, MAX_ASSISTANT) + '\n\n*（正文过长，已截断）*' : a.text);
      out.push('');
    }
    if (t.calls.length) {
      out.push(`**工具调用（${t.calls.length} 次）：**`);
      out.push('');
      out.push('| # | 工具 | 参数摘要 | 结果 |');
      out.push('|---|---|---|---|');
      t.calls.forEach((c, i) => {
        const r = results.get(c.callId);
        const txt = (r?.content || []).filter((x) => x.type === 'text').map((x) => x.text).join(' ');
        out.push(
          `| ${i + 1} | \`${c.name}\` | ${argSummary(c.args).replace(/\|/g, '\\|')} | ${r?.isError ? '❌' : '✅'} ${oneLine(txt, 80).replace(/\|/g, '\\|')} |`,
        );
      });
      out.push('');
    }
    for (const a of t.approvals) {
      out.push(`**审批请求：** ${oneLine(a.reason, 220)}`);
      out.push('');
      out.push(`→ 结果：**${a.outcome}**`);
      out.push('');
    }
  }

  if (todos.length) {
    out.push('---');
    out.push('');
    out.push('## 任务清单（todo）变化');
    out.push('');
    todos.forEach((t, i) => {
      out.push(`**第 ${i + 1} 次（${ts(t.time)}）**`);
      out.push('');
      for (const item of t.items) out.push(`- [${item.status === 'completed' ? 'x' : ' '}] ${item.content} — \`${item.status}\``);
      out.push('');
    });
  }

  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, out.join('\n'), 'utf-8');
  console.log(`已生成 ${output}（${sorted.length} 轮 / ${calls} 次工具调用 / ${approvals} 次审批）`);
  return 0;
}

process.exit(main(process.argv.slice(2)));
