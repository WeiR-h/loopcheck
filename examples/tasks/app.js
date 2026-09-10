// Original demo fixture. The duplicate-title deletion bug is intentional.
const STORAGE_KEY = 'loopcheck-tasks';
let tasks = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
const list = document.getElementById('task-list');
const input = document.getElementById('task-input');

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function removeTask(id) {
  const selected = tasks.find(task => task.id === id);
  if (!selected) return;
  tasks = tasks.filter(task => task.title !== selected.title);
  persist();
  render();
}

function render() {
  list.replaceChildren();
  for (const task of tasks) {
    const row = document.createElement('li');
    row.dataset.testid = 'task-row';
    row.dataset.id = task.id;
    row.dataset.completed = String(task.done);
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = task.done;
    checkbox.setAttribute('aria-label', '完成 ' + task.title);
    checkbox.addEventListener('change', () => {
      task.done = checkbox.checked;
      persist();
      render();
    });
    const text = document.createElement('span');
    text.textContent = task.title;
    const remove = document.createElement('button');
    remove.textContent = '删除';
    remove.dataset.action = 'delete';
    remove.addEventListener('click', () => removeTask(task.id));
    row.append(checkbox, text, remove);
    list.append(row);
  }
  document.getElementById('task-count').textContent = tasks.length + ' 项';
  document.getElementById('empty').hidden = tasks.length > 0;
}

document.getElementById('task-form').addEventListener('submit', event => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return;
  tasks.push({ id: crypto.randomUUID(), title, done: false });
  input.value = '';
  persist();
  render();
});

render();
