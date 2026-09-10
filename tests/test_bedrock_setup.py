import test_support  # isolate storage before importing any application module
"""Offline integration checks: fake AWS responses, real Strands tool execution."""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "bedrock_setup", Path(__file__).resolve().parents[1] / "scripts" / "check_bedrock.py"
)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def test_secret_preserved_without_interpolation_and_not_in_config(self):
        with tempfile.TemporaryDirectory() as directory:
            env = Path(directory) / ".env"
            env.write_text(
                "AWS_BEARER_TOKEN_BEDROCK=test-${literal}-secret\n"
                f"AWS_REGION={setup.REGION}\nBEDROCK_MODEL_ID={setup.MODEL_ID}\n",
                encoding="utf-8-sig",
            )
            settings = setup.read_settings(env)
            self.assertEqual(settings["api_key"], "test-${literal}-secret")
        fake = SimpleNamespace(meta=SimpleNamespace(region_name=setup.REGION), converse=lambda **_: {})
        with patch("boto3.Session.client", return_value=fake):
            model = setup.LimitedBedrockModel(settings, reserve=lambda: None)
        self.assertNotIn("api_key", model.config)
        self.assertNotIn("test-${literal}-secret", json.dumps(model.config))

    def test_missing_key_never_opens_aws_client(self):
        with tempfile.TemporaryDirectory() as directory, patch("boto3.Session.client") as client:
            env = Path(directory) / ".env"
            env.write_text("AWS_BEARER_TOKEN_BEDROCK=PASTE_YOUR_BEDROCK_API_KEY_HERE\n")
            with self.assertRaises(setup.SetupError):
                setup.read_settings(env)
            client.assert_not_called()

    def test_strands_roundtrip_and_request_limit(self):
        requests = []
        reservations = []

        def converse(**request):
            requests.append(request)
            if len(requests) == 1:
                content = [{"toolUse": {"toolUseId": "probe1", "name": "read_connection_probe", "input": {}}}]
                stop = "tool_use"
            else:
                receipt = next(
                    block["toolResult"]["content"][0]["text"]
                    for message in request["messages"]
                    for block in message["content"]
                    if "toolResult" in block
                )
                content = [{"text": receipt}]
                stop = "end_turn"
            return {
                "output": {"message": {"role": "assistant", "content": content}},
                "stopReason": stop,
                "usage": {"inputTokens": 30, "outputTokens": 20, "totalTokens": 50},
                "metrics": {"latencyMs": 1},
            }

        fake = SimpleNamespace(meta=SimpleNamespace(region_name=setup.REGION), converse=converse)
        settings = {"api_key": "offline-test-secret", "region_name": setup.REGION, "model_id": setup.MODEL_ID}
        with patch("boto3.Session.client", return_value=fake):
            model = setup.LimitedBedrockModel(settings, reserve=lambda: reservations.append(1))
            agent, receipt, observations = setup.make_probe_agent(model)
            result = agent("Run the connection probe now.")
        self.assertEqual(str(result).strip(), receipt)
        self.assertEqual(observations, ["read_connection_probe"])
        self.assertEqual(len(requests), 2)
        self.assertEqual(len(reservations), 2)
        self.assertEqual(agent.event_loop_metrics.accumulated_usage["totalTokens"], 100)
        self.assertEqual(requests[0]["modelId"], setup.MODEL_ID)
        self.assertEqual(requests[0]["inferenceConfig"]["maxTokens"], 256)
        self.assertNotIn("offline-test-secret", json.dumps(requests))
        with self.assertRaises(setup.SetupError):
            model.client.converse(modelId=setup.MODEL_ID, messages=[])
        self.assertEqual(len(requests), 2)

    def test_failed_attempts_still_consume_persistent_quota(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "attempts.sqlite3"
            for _ in range(setup.MAX_SETUP_CALLS):
                setup.reserve_setup_call(db)
            with self.assertRaises(setup.SetupError):
                setup.reserve_setup_call(db)

    def test_raw_error_details_never_displayed(self):
        self.assertNotIn("dummy-secret", setup.safe_error(RuntimeError("dummy-secret")))


if __name__ == "__main__":
    unittest.main()
