# LoopCheck — verification report

Generated from recorded browser execution. The sample bugs are deliberately seeded in original example code.

- Run: a3719fbefad94e49aafdc8e0e8e8ae90
- Status: adopted
- Started (UTC): 2026-09-09T09:43:48.286387+00:00
- Model: qwen3.7-flash
- Trigger: manual
- Elapsed: 25.87 seconds (machine and API time included)
- Provider-reported estimate: CNY 0.003152
- Reserved without returned usage: CNY 0.000000
- Requests: 5

## Reported problem

After adding and completing a task, reloading loses it. Preserve task contents and completion state.

## Browser checks

| Check | Before | After | Observed result |
| --- | --- | --- | --- |
| 新增与勾选仍然可用 | PASS | PASS | 新增 1 条，勾选后状态为已完成 |
| 删除同名项，保留另一条记录 | PASS | PASS | 删除第一条后，第二条的内容和标识保持不变 |
| 不同排列下只删除选中项 | PASS | PASS | 三条混排记录中只删除选中的第三条 |
| 刷新后保留任务和完成状态 | FAIL | PASS | 刷新后，任务内容和勾选状态均保留 |
| 删除同名任务时只删除选中项 | PASS | PASS | 保存的 6 个操作与断言已执行 |
| Delete only the selected task with duplicate titles | PASS | PASS | 保存的 6 个操作与断言已执行 |
| Tasks and completion state must persist across page reloads | FAIL | PASS | 保存的 6 个操作与断言已执行 |

## Reusable requirement

```json
{
  "title": "Tasks and completion state must persist across page reloads",
  "steps": [
    {
      "action": "add",
      "value": "Buy coffee",
      "index": 0,
      "count": 0,
      "done": true
    },
    {
      "action": "toggle",
      "value": "",
      "index": 0,
      "count": 0,
      "done": true
    },
    {
      "action": "reload",
      "value": "",
      "index": 0,
      "count": 0,
      "done": true
    },
    {
      "action": "expect_count",
      "value": "",
      "index": 0,
      "count": 1,
      "done": true
    },
    {
      "action": "expect_title",
      "value": "Buy coffee",
      "index": 0,
      "count": 0,
      "done": true
    },
    {
      "action": "expect_done",
      "value": "",
      "index": 0,
      "count": 0,
      "done": true
    }
  ]
}
```

## Human time

Self-reported assisted time: None seconds. Self-reported comparison: None seconds.
A single self-report does not establish a general efficiency improvement.

## Patch

```diff
--- a/app.js
+++ b/app.js
@@ -5,7 +5,7 @@
 const input = document.getElementById('task-input');
 
 function persist() {
-  // Seeded example: the save operation is missing.
+  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
 }
 
 function removeTask(id) {

```

## Tool execution

read_project → run_checks → record_requirement → edit_app

Only independently passing patches can be adopted. Version snapshots are retained.