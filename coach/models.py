import json
import logging
import os
import time

os.environ['OTEL_SDK_DISABLED'] = 'true'
for name in ['strands', 'openai', 'httpx', 'httpx2', 'httpcore', 'httpcore2']:
    logging.getLogger(name).setLevel(logging.CRITICAL)

from strands.models.openai import OpenAIModel
from .settings import MODEL_PRICES, settings


class BudgetModel(OpenAIModel):
    """Aliyun's compatible endpoint, with persistent reservations before every request."""
    def __init__(self, store, run_id, on_call=None):
        s = settings()
        if s['provider'] != 'dashscope' or not s['key'].strip():
            raise ValueError('请先在本地 .env 填入百炼北京地域的 DASHSCOPE_API_KEY')
        if s['model'] not in MODEL_PRICES:
            raise ValueError('当前支持的模型：' + '、'.join(MODEL_PRICES))
        self.store, self.run_id, self.limit = store, run_id, s['budget_cny']
        self.prices = MODEL_PRICES[s['model']]
        self.deadline = time.monotonic() + 360
        self.on_call = on_call or (lambda _: None)
        params = {'max_tokens': 2500, 'temperature': 0.15, 'parallel_tool_calls': False}
        if s['model'] == 'qwen3.7-flash':
            # Explicitly disable its default thinking mode for the first repair trial.
            params['extra_body'] = {'enable_thinking': False}
        super().__init__(model_id=s['model'], stream=False,
            client_args={'api_key': s['key'], 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                         'max_retries': 0, 'timeout': 45.0},
            params=params)

    async def stream(self, messages, tool_specs=None, system_prompt=None, *, tool_choice=None, **kwargs):
        if time.monotonic() > self.deadline:
            raise ValueError('代理已达到本次任务时限')
        request = self.format_request(messages, tool_specs, system_prompt, tool_choice)
        # Bytes are a conservative input bound for this text-only, small-file workflow.
        if len(json.dumps(request, ensure_ascii=False).encode()) > 28_000:
            raise ValueError('本次上下文超过首版限制，请缩小问题范围')
        reserve = (32_000 * self.prices[0] + 2500 * self.prices[1]) / 1_000_000
        call = self.store.reserve(self.run_id, self.config['model_id'], reserve, self.limit)
        self.on_call('正在请求模型；已预留本次费用')
        async for event in super().stream(messages, tool_specs, system_prompt, tool_choice=tool_choice, **kwargs):
            usage = event.get('metadata', {}).get('usage')
            if usage:
                self.store.settle(call, usage, *self.prices)
            yield event


def safe_error(exc):
    cause = exc
    for _ in range(5):
        next_cause = getattr(cause, '__cause__', None)
        if not next_cause or next_cause is cause:
            break
        cause = next_cause
    authored = ('本次', '已达到', '代理已达到', '当前支持', '请先在本地')
    if isinstance(cause, ValueError) and str(cause).startswith(authored):
        return str(cause)[:240]
    if isinstance(exc, ValueError) and not getattr(exc, 'response', None):
        # Only explicitly authored application errors are exposed by callers.
        return '本次任务因配置、输入或执行上限停止，请查看进度记录并缩小问题范围'
    status = getattr(cause, 'status_code', None)
    if status in (401, 403):
        return '模型认证或权限被拒绝，请检查百炼北京地域密钥、开通状态和模型权限'
    if status == 429:
        return '模型额度不足或请求被限流；本次已停止，未自动切换其他付费模型'
    if status == 400:
        return '模型未接受请求，请核对模型开通与接口配置'
    if 'Timeout' in type(exc).__name__:
        return '模型或执行器响应超时，本次未采用任何修改'
    return '本次修复未完成，原版本保持不变。查看下方失败检查后，可以缩小问题范围再试。'
