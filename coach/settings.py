import os
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('LOOPCHECK_DATA', ROOT / 'data' / 'app')).resolve()
FIXTURES = ROOT / 'examples' / 'tasks'
# Beijing text prices in CNY per million tokens, input <= 32K; checked 2026-09-09.
# The request byte limit in BudgetModel keeps this workflow in the first tier.
MODEL_PRICES = {
    'qwen3.7-flash': (0.2, 0.8),
    'qwen3-coder-flash': (1.0, 4.0),
    'qwen3-coder-plus': (4.0, 16.0),
}


def settings():
    values = dotenv_values(ROOT / '.env', encoding='utf-8-sig', interpolate=False)
    def get(key, default=''):
        return os.environ.get(key, values.get(key) or default)
    return {
        'provider': get('AI_PROVIDER', 'dashscope'),
        'model': get('DASHSCOPE_MODEL', 'qwen3.7-flash'),
        'key': get('DASHSCOPE_API_KEY'),
        'budget_cny': min(60.0, max(0.0, float(get('MODEL_BUDGET_CNY', '20')))),
    }


def public_model():
    s = settings()
    configured = bool(s['key'].strip()) and s['provider'] == 'dashscope'
    supported = s['model'] in MODEL_PRICES
    return {'provider': '阿里云百炼 · 北京', 'model': s['model'],
            'configured': configured and supported,
            'message': '密钥已配置，真实调用结果以运行记录为准' if configured and supported
            else '请在本地 .env 填写 DASHSCOPE_API_KEY；检查功能可以先使用'}
