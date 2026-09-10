"""Original, explicitly seeded evaluation cases; never used to generate model repairs."""
from .settings import FIXTURES

SCENARIOS = {
    'duplicates': {'name': '同名任务误删', 'name_en': 'Duplicate tasks disappear',
        'symptom': '两条任务名称相同，删除其中一条会同时删除另一条。请只删除选中的任务，并保留其他功能。',
        'symptom_en': 'Deleting one of two identically named tasks deletes both. Keep the other task and preserve existing behavior.'},
    'persistence': {'name': '刷新后任务丢失', 'name_en': 'Tasks vanish on refresh',
        'symptom': '新增任务并勾选完成后，刷新页面任务就消失了。请保留任务内容和完成状态。',
        'symptom_en': 'After adding and completing a task, reloading loses it. Preserve task contents and completion state.'},
    'toggle': {'name': '完成状态反转', 'name_en': 'Completion flips back',
        'symptom': '点击任务的完成框后，完成状态总是反过来，无法正常勾选。请修好并保留删除和刷新功能。',
        'symptom_en': 'The completion checkbox flips back when clicked. Fix it and preserve deletion and persistence.'},
}


def scenario_code(name):
    if name not in SCENARIOS:
        raise ValueError('请选择已有的原创场景')
    original = (FIXTURES / 'app.js').read_text(encoding='utf-8')
    if name == 'duplicates':
        return original
    # Independent seeded variants, disclosed as examples in the UI and documentation.
    code = original.replace('tasks = tasks.filter(task => task.title !== selected.title);',
                            'tasks = tasks.filter(task => task.id !== id);')
    if name == 'persistence':
        return code.replace('localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));',
                            '// Seeded example: the save operation is missing.')
    return code.replace('task.done = checkbox.checked;', 'task.done = !checkbox.checked;')
