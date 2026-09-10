const form = document.querySelector('#budget');
const income = document.querySelector('#income');
const expense = document.querySelector('#expense');
const category = document.querySelector('#category');
const balance = document.querySelector('#balance');
const error = document.querySelector('#error');
function calculate(save = true) {
  const i = Number(income.value), e = Number(expense.value);
  if (!income.value || !expense.value || !Number.isFinite(i) || !Number.isFinite(e) || i < 0 || e < 0) {
    error.textContent = 'Enter non-negative amounts.';
    return;
  }
  error.textContent = '';
  balance.textContent = (i - e).toFixed(2);
  if (save) localStorage.setItem('pocket-budget', JSON.stringify({income: income.value, expense: expense.value, category: category.value}));
}
try {
  const saved = JSON.parse(localStorage.getItem('pocket-budget') || 'null');
  if (saved) { income.value = saved.income; expense.value = saved.expense; category.value = saved.category; }
} catch (_) { /* Invalid local data falls back to form defaults. */ }
calculate(false);
form.addEventListener('submit', event => { event.preventDefault(); calculate(); });
document.querySelector('#reset').addEventListener('click', () => {
  localStorage.removeItem('pocket-budget'); income.value = '1000'; expense.value = '200'; category.value = 'food'; calculate(false);
});
