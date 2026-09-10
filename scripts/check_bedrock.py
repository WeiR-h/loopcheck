"""Small Strands/Bedrock connectivity check; no network call without --live.

This is setup verification, not the project's bug-fixing agent or evaluation.
Never print credentials, raw provider errors, environment contents, or headers.
"""

import argparse
from contextlib import closing
import json
import logging
import os
import re
from pathlib import Path
import secrets
import sqlite3
import sys
import threading
import time

os.environ["OTEL_SDK_DISABLED"] = "true"
logging.disable(logging.CRITICAL)

from botocore.config import Config
from dotenv import dotenv_values
from strands import Agent, tool
from strands.models import BedrockModel

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "global.openai.gpt-5.6-luna"
REGION = "ap-southeast-2"
INPUT_USD_PER_MILLION = 0.20
OUTPUT_USD_PER_MILLION = 1.20
MAX_CALLS_PER_RUN = 2
MAX_SETUP_CALLS = 10
MAX_OUTPUT_TOKENS = 256


class SetupError(Exception):
    """A safe, user-facing setup error; never include secret input."""


def read_settings(path: Path = ROOT / ".env") -> dict:
    # Disable ${...} interpolation: a token must be preserved verbatim.
    values = dotenv_values(path, encoding="utf-8-sig", interpolate=False)
    key = (values.get("AWS_BEARER_TOKEN_BEDROCK") or "").strip()
    if not key or key == "PASTE_YOUR_BEDROCK_API_KEY_HERE":
        raise SetupError("请在项目 .env 文件的第一项填入 Bedrock API 密钥并保存。")
    if any(char.isspace() for char in key):
        raise SetupError("密钥中含空白字符，请重新完整粘贴到等号右侧的一行。")
    if values.get("AWS_REGION") != REGION or values.get("BEDROCK_MODEL_ID") != MODEL_ID:
        raise SetupError("此测试限定使用悉尼区域和 GPT-5.6 Luna 全球推理，请恢复预填的区域与模型。")
    return {"api_key": key, "region_name": REGION, "model_id": MODEL_ID}


def reserve_setup_call(db_path: Path = ROOT / "data" / "setup-usage.sqlite3") -> None:
    """Persist attempts before requests, including failed and interrupted calls."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path, timeout=5)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS setup_calls (id INTEGER PRIMARY KEY, started REAL)")
        db.execute("BEGIN IMMEDIATE")
        used = db.execute("SELECT COUNT(*) FROM setup_calls").fetchone()[0]
        if used >= MAX_SETUP_CALLS:
            raise SetupError("已达到初次配置的 10 次请求上限，请先检查结果与账单，勿重复运行。")
        db.execute("INSERT INTO setup_calls (started) VALUES (?)", (time.time(),))


class LimitedBedrockModel(BedrockModel):
    """Bound Converse requests, including Strands retries and format fallbacks."""

    def __init__(self, settings: dict, reserve=reserve_setup_call):
        # This pinned Strands version uses boto3's environment-based bearer auth.
        # Keep the credential outside model_config, tool inputs and model prompts.
        config = dict(settings)
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = config.pop("api_key")
        super().__init__(
            **config,
            streaming=False,
            max_tokens=MAX_OUTPUT_TOKENS,
            additional_request_fields={"reasoning_effort": "none"},
            boto_client_config=Config(
                connect_timeout=10,
                read_timeout=30,
                retries={"mode": "standard", "total_max_attempts": 1},
            ),
        )
        self.requests_attempted = 0
        self.reserve = reserve
        self._request_lock = threading.Lock()
        original_converse = self.client.converse

        def limited_converse(**request):
            # Guard the actual API method, including SDK-internal fallback calls.
            with self._request_lock:
                if self.requests_attempted >= MAX_CALLS_PER_RUN:
                    raise SetupError("本次已达到 2 次模型请求上限；停止继续调用。")
                if len(json.dumps(request, ensure_ascii=True).encode("utf-8")) > 16_000:
                    raise SetupError("连通测试输入超出限制，已停止调用。")
                self.reserve()
                self.requests_attempted += 1
            return original_converse(**request)

        self.client.converse = limited_converse


def make_probe_agent(model):
    receipt = secrets.token_hex(8)
    observations = []

    @tool
    def read_connection_probe() -> str:
        """Read the runtime connection probe and return its current receipt."""
        observations.append("read_connection_probe")
        return receipt

    agent = Agent(
        model=model,
        tools=[read_connection_probe],
        system_prompt=(
            "This is a connectivity test. Call read_connection_probe exactly once. "
            "Then return only the receipt you received from that tool. "
            "Do not invent a receipt or call any other tool."
        ),
        callback_handler=None,
    )
    return agent, receipt, observations


def safe_error(exc: Exception) -> str:
    if isinstance(exc, SetupError):
        return str(exc)
    code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
    messages = {
        "AccessDeniedException": "访问被拒绝：请检查密钥权限，以及账号对当前模型的访问权限。",
        "ExpiredTokenException": "密钥已过期，请在悉尼区域重新生成短期密钥。",
        "UnrecognizedClientException": "认证失败，请检查是否粘贴了完整的 Bedrock API 密钥。",
        "ValidationException": "请求未被接受，请检查当前账户支持的模型和区域。",
        "ResourceNotFoundException": "当前账户或区域未找到此模型。",
        "ThrottlingException": "请求被限流，请检查该模型的账户配额，勿连续重试。",
        "ServiceQuotaExceededException": "账户配额不足，请先检查 Bedrock 配额。",
        "ServiceUnavailableException": "AWS 服务暂时不可用，本次测试已停止。",
    }
    if code in messages:
        detail = str(getattr(exc, "response", {}).get("Error", {}).get("Message", ""))
        token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "")
        if token:
            detail = detail.replace(token, "[redacted]")
        detail = re.sub(r"(?i)bearer\s+[^\s,\"']+", "Bearer [redacted]", detail)
        detail = re.sub(r"\b\d{12}\b", "[account]", detail)
        return f"{code}: {messages[code]} {detail[:600]}".strip()
    if type(exc).__name__ in {"EndpointConnectionError", "ConnectTimeoutError", "ReadTimeoutError", "SSLError"}:
        return "网络连接或证书验证失败，请检查网络；没有关闭证书验证。"
    return f"测试未完成（{type(exc).__name__}）。未输出原始错误，请由助手继续定位。"


def run_live(settings: dict) -> int:
    report = {
        "test_type": "live_strands_bedrock_connectivity_only",
        "model": MODEL_ID,
        "region": REGION,
        "success": False,
        "started_at_unix": time.time(),
    }
    model = None
    agent = None
    observations = []
    started = time.monotonic()
    try:
        model = LimitedBedrockModel(settings)
        agent, receipt, observations = make_probe_agent(model)
        result = agent("Run the connection probe now.")
        report["success"] = len(observations) == 1 and str(result).strip() == receipt
        report["stop_reason"] = result.stop_reason
        if not report["success"]:
            report["error"] = "模型已响应，但工具调用或结果回传没有通过验证。"
    except Exception as exc:
        report["error"] = safe_error(exc)
    finally:
        report["seconds"] = round(time.monotonic() - started, 2)
        report["requests_attempted"] = model.requests_attempted if model else 0
        report["tool_executions"] = len(observations)
        usage = dict(agent.event_loop_metrics.accumulated_usage) if agent else {}
        report["reported_usage"] = usage
        if usage.get("totalTokens", 0):
            report["estimated_reported_usage_usd"] = round(
                (usage.get("inputTokens", 0) * INPUT_USD_PER_MILLION
                 + usage.get("outputTokens", 0) * OUTPUT_USD_PER_MILLION) / 1_000_000,
                8,
            )
        else:
            report["estimated_reported_usage_usd"] = None
        report["billing_note"] = "仅估算已收到的用量；失败或中断请求可能产生未返回用量的费用，以 AWS 账单为准。"
        data_dir = ROOT / "data"
        data_dir.mkdir(exist_ok=True)
        (data_dir / "bedrock-check.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        history = data_dir / "checks"
        history.mkdir(exist_ok=True)
        (history / f"{time.time_ns()}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print("通过：Strands → Bedrock → 本地工具 → 模型回传结果。" if report["success"] else report["error"])
    print(f"请求次数：{report['requests_attempted']}；工具执行次数：{report['tool_executions']}。")
    print("用量记录已保存到 data/bedrock-check.json；其中不含密钥。")
    return 0 if report["success"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="本地 AWS Bedrock 配置检查")
    parser.add_argument("--live", action="store_true", help="进行少量真实付费模型调用")
    args = parser.parse_args()
    try:
        settings = read_settings()
    except SetupError as exc:
        print(str(exc))
        return 2
    print(f"区域：{REGION}；模型：{MODEL_ID}；密钥：已填写（内容隐藏）。")
    if not args.live:
        print("本地格式检查完成；尚未验证凭证是否有效，未发送模型请求。")
        return 0
    return run_live(settings)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
