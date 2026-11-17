# V1 覆盖汇总历史原文

原 YAML summary 含重复键，2026-10-31 修复机器解析时原样保留于此，不将其过时计数当作 V2 证据。

```yaml
summary:
  requirements_total: 22
  requirements_test_backed: 21
  requirements_pending: 1
  invariants_total: 16
  invariants_negative_test_backed: 13
  invariants_pending: 3
  note: >-
    2026-10-06 P7 落地后更新。计数**由脚本核对**，非手工估算。
    需求覆盖 17 → 21：NFR-PERF-001（四元素补齐）、NFR-QA-001、NFR-QA-002、AI-002 转为 backed。
    不变量覆盖 12 → 13：INV-ADS-016 转为 backed。
    剩余未覆盖的 **1 条需求与 3 条不变量**全部登记去向：
      · REQ-ADS-GOV-002 / INV-ADS-009 / INV-ADS-010 —— D3 交付物（.opencode 权限模型与 hook）待建
      · INV-ADS-011 —— 变异验证已实现（12/12 检出），但其**流程侧**（CI 阻断接线）待 D3
    **变异验证**：12/12 条声明覆盖的不变量，其反例测试在实现被破坏时确实失败。
      · REQ-ADS-AI-002 —— 版本溯源字段未写入审计记录（属 P7/P8）
  invariants_pending: 8
  note: >-
    2026-10-06 P4（selector）落地后更新。计数**由脚本核对**，非手工估算。
    需求覆盖 9 → 12：ARCH-003、NFR-COST-001、AI-001 转为 backed；
    ARCH-002、ARCH-004、NFR-SAFETY-003 证据增强。
    不变量覆盖 5 → 8：INV-ADS-003（畸形输出 fail-closed）、
    INV-ADS-004（解释路径隔离）、INV-ADS-014（预算与压缩后重注入）转为 backed。
    未覆盖的 10 条需求与 8 条不变量**全部登记去向与阻塞原因**（pending_test / blocked_by），
    主要阻塞在 P5（src/app/ 编排与降级）与 P6（src/audit/ 证据）。
    其中 NFR-SAFETY-005 为 partial：confidence 取值域与阈值锁定已覆盖，
    缺「低于阈值 → 降级」的判定（属 P5）。

```
