"""Portable evidence from actual run records. No invented efficiency percentages."""
import io
import json
import zipfile
from datetime import datetime, timezone

from .settings import FIXTURES, ROOT


def report_markdown(run):
    def cell(value):
        return str(value or '').replace('|', '\\|').replace('\n', ' ').replace('\r', '')
    usage = run.get('usage', {})
    rows = ['# LoopCheck — verification report', '',
        'Generated from recorded browser execution. The sample bugs are deliberately seeded in original example code.', '',
        f'- Run: {run["id"]}', f'- Status: {run["state"]}',
        f'- Started (UTC): {datetime.fromtimestamp(run["created"], timezone.utc).isoformat()}',
        f'- Model: {cell(run.get("model") or "No model request")}',
        f'- Trigger: {cell(run.get("trigger", "manual"))}',
        f'- Elapsed: {run.get("seconds", "pending")} seconds (machine and API time included)',
        f'- Provider-reported estimate: CNY {usage.get("reported_cny", 0):.6f}',
        f'- Reserved without returned usage: CNY {usage.get("unknown_reserved_cny", 0):.6f}',
        f'- Requests: {usage.get("calls", 0)}', '', '## Reported problem', '',
        cell(run.get('symptom')), '', '## Browser checks', '',
        '| Check | Before | After | Observed result |', '| --- | --- | --- | --- |']
    before = {c['id']: c for c in (run.get('before') or {}).get('checks', [])}
    after = {c['id']: c for c in (run.get('after') or {}).get('checks', [])}
    requirement_before = (run.get('requirement_before') or {}).get('checks', [])
    for item in requirement_before:
        match = next((c for c in after.values() if c['label'] == item['label'] and c['id'] not in before), None)
        if match:
            before[match['id']] = item
    for key in dict.fromkeys([*before, *after]):
        a, b = after.get(key), before.get(key)
        def status(check):
            return 'PASS' if check and check['passed'] else 'FAIL' if check else 'Not run'
        rows.append(f'| {cell((a or b)["label"])} | {status(b)} | {status(a)} | {cell((a or b)["actual"])} |')
    rows += ['', '## Reusable requirement', '', '```json',
             json.dumps(run.get('requirement'), ensure_ascii=False, indent=2), '```', '',
             '## Human time', '',
             f'Self-reported assisted time: {run.get("human_seconds")} seconds. '
             f'Self-reported comparison: {run.get("baseline_seconds")} seconds.',
             'A single self-report does not establish a general efficiency improvement.', '',
             '## Patch', '', '```diff', (run.get('diff') or 'No patch').replace('```', "'''"), '```', '',
             '## Tool execution', '', ' → '.join(run.get('tool_calls', [])), '',
             'Only independently passing patches can be adopted. Version snapshots are retained.']
    return '\n'.join(rows)


def project_zip(version, requirements):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('app.js', version['code'])
        for name in ('index.html', 'style.css'):
            archive.write(FIXTURES / name, name)
        archive.write(ROOT / 'LICENSE', 'LICENSE')
        archive.writestr('checks.json', json.dumps([r['spec'] for r in requirements], ensure_ascii=False, indent=2))
        archive.writestr('README.txt', 'LoopCheck example export\n\nOpen index.html in a modern browser. '
            'This export contains the selected source version and its recorded behavioral checks. '
            'The source may include seeded bugs or unverified changes; consult the run report. '
            'No API key or private workspace cookie is included.\nVersion hash: ' + version['hash'])
    return output.getvalue()
