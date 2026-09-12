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
        for attempt in range(2):
            if time.monotonic() > self.deadline: raise ValueError('代理已达到本次任务时限')
            self.on_call('Requesting the model; reserving this attempt in the persistent budget')
            call = self.store.reserve(self.run_id, self.config['model_id'], reserve, self.limit)
            # The provider is non-streaming. Buffer its small response so a
            # transport retry never delivers half a tool call twice to Strands.
            buffered = []
            try:
                async for event in super().stream(messages, tool_specs, system_prompt, tool_choice=tool_choice, **kwargs):
                    usage = event.get('metadata', {}).get('usage')
                    if usage: self.store.settle(call, usage, *self.prices)
                    buffered.append(event)
            except Exception as exc:
                if attempt == 0 and error_code(exc) in {'connection', 'timeout'}:
                    self.on_call('Transient provider connection failure; retrying once. Unknown cost remains reserved.')
                    continue
                raise
            for event in buffered: yield event
            return


def error_chain(exc):
    chain = []
    while exc is not None and len(chain) < 6 and all(exc is not item for item in chain):
        chain.append(exc)
        exc = getattr(exc, '__cause__', None) or getattr(exc, '__context__', None)
    return chain


def error_code(exc):
    """Classify without persisting exception text, response bodies or credentials."""
    chain = error_chain(exc)
    statuses = {getattr(item, 'status_code', None) for item in chain}
    if statuses & {401, 403}: return 'model_access'
    if 429 in statuses: return 'model_limit'
    if 400 in statuses: return 'model_request'
    if any('timeout' in type(item).__name__.lower() for item in chain): return 'timeout'
    if any('connect' in type(item).__name__.lower() for item in chain): return 'connection'
    return 'task_error'


def safe_error(exc):
    chain = error_chain(exc)
    authored = ('本次', '已达到', '代理已达到', '当前支持', '请先在本地')
    for cause in chain:
        if isinstance(cause, ValueError) and str(cause).startswith(authored):
            return str(cause)[:240]
    code = error_code(exc)
    messages = {
        'model_access': 'The model rejected authentication or access. Check the configured provider key and model access, then retry.',
        'model_limit': 'The provider rejected this request because of quota or rate limits. Check the provider account before retrying.',
        'model_request': 'The provider did not accept this request. Check the configured model and request limits before retrying.',
        'timeout': 'The model or browser timed out. Check the preview and provider connection, then retry. This result cannot approve the change.',
        'connection': 'The provider connection was interrupted. Check the network and retry. No requirements were approved by this failed run.',
    }
    if code in messages: return messages[code]
    if isinstance(exc, ValueError) and not getattr(exc, 'response', None):
        # Only explicitly authored application errors are exposed by callers.
        return '本次任务因配置、输入或执行上限停止，请查看进度记录并缩小问题范围'
    return 'This task could not finish reliably. Review its progress, check the preview and provider connection, then retry or narrow the goal. This result cannot approve the change.'
