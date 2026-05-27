import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import llm


class LlmClientTest(unittest.TestCase):
    def test_llm_metadata_hides_api_key(self):
        fake_settings = SimpleNamespace(
            chatbi_llm_provider="deepseek",
            deepseek_api_base_url="https://api.deepseek.com",
            deepseek_api_key="sk-secret",
            deepseek_model="deepseek-v4-flash",
            deepseek_timeout=60,
        )

        with patch.object(llm, "settings", fake_settings):
            metadata = llm.llm_config_metadata()

        self.assertEqual(metadata["provider"], "deepseek")
        self.assertTrue(metadata["deepseek"]["api_key_configured"])
        self.assertNotIn("sk-secret", json.dumps(metadata))

    def test_build_chat_payload(self):
        payload = llm.build_chat_payload("你好", "你是助手", temperature=0.2)

        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["content"], "你好")

    def test_parse_chat_completion_response(self):
        response = {
            "id": "chatcmpl-test",
            "model": "deepseek-v4-flash",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "可以调用。",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
        }

        result = llm.parse_chat_completion_response(response)

        self.assertEqual(result["content"], "可以调用。")
        self.assertEqual(result["model"], "deepseek-v4-flash")
        self.assertEqual(result["usage"]["total_tokens"], 14)


if __name__ == "__main__":
    unittest.main()
