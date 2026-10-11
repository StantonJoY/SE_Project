# eval/reports/ —— 评估集 replay 报告目录（append-only）

本目录存放 `python eval/eval_runner.py` 每次运行产出的 JSON 报告，
文件名形如 `replay-YYYYMMDDTHHMMSS.json`。

**append-only**：新报告只追加，**不覆盖**历史 —— 与审计日志同一原则
（`docs/architecture/memory-design.md` §2 S1：证据只写不读）。
这样"某次 replay 的结论"可以事后复核，而不是被下一次运行抹掉。

报告的字段与语义见 `eval/eval_runner.py` 的 `_write_report`；
判定规则（分母分离、违规零容忍、阈值语义）见
`docs/architecture/adr-003-evaluation-set-as-architecture.md`。

> 报告写入失败**不影响判定**（`eval_runner` 会打印警告但退出码不变）——
> 判定由内存中的 `ReplayReport` 决定，落盘只是留证。
