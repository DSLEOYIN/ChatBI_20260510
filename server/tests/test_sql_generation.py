import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import llm


class SqlGenerationTest(unittest.TestCase):
    def test_build_sql_generation_prompt_excludes_result_rows(self):
        catalog = {
            "assets": [
                {
                    "table": "v_dm_sal_stock_dly",
                    "name": "库存日表",
                    "fields": [
                        {"name": "area_name", "cn_name": "区域"},
                        {"name": "model_name", "cn_name": "车型"},
                        {"name": "stock_qty", "cn_name": "库存"},
                    ],
                }
            ],
            "metric_definitions": [
                {"name": "库存周转天数", "formula": "库存 / 近30天日均终端销量"},
            ],
        }

        prompt = llm.build_sql_generation_prompt(
            question="查询中东公司 GS8 库存",
            catalog=catalog,
            sample_rows=[{"stock_qty": 1280}],
        )

        self.assertIn("v_dm_sal_stock_dly", prompt)
        self.assertIn("stock_qty", prompt)
        self.assertIn("库存周转天数", prompt)
        self.assertIn("如果用户问题包含明确实体值，WHERE 条件必须保留原始字面量", prompt)
        self.assertIn("中东公司", prompt)
        self.assertNotIn("1280", prompt)
        self.assertNotIn("sample_rows", prompt)

    def test_extract_sql_from_completion_handles_code_fence(self):
        content = """
        下面是 SQL：

        ```sql
        SELECT area_name, model_name
        FROM v_dm_sal_stock_dly
        WHERE area_name = '中东公司';
        ```
        """

        sql = llm.extract_sql_from_completion(content)

        self.assertEqual(
            sql,
            "SELECT area_name, model_name\nFROM v_dm_sal_stock_dly\nWHERE area_name = '中东公司';",
        )

    def test_generate_sql_validates_deepseek_output(self):
        fake_settings = SimpleNamespace(
            chatbi_llm_provider="deepseek",
            deepseek_api_base_url="https://api.deepseek.com",
            deepseek_api_key="sk-secret",
            deepseek_model="deepseek-v4-flash",
            deepseek_timeout=60,
        )
        fake_completion = {
            "provider": "deepseek",
            "id": "chatcmpl-test",
            "model": "deepseek-v4-flash",
            "content": "DELETE FROM v_dm_sal_stock_dly;",
            "finish_reason": "stop",
            "usage": {},
        }

        with patch.object(llm, "settings", fake_settings), patch.object(llm, "chat_completion", return_value=fake_completion):
            result = llm.generate_sql_from_question("删除库存表", catalog={"assets": [], "metric_definitions": []})

        self.assertEqual(result["provider"], "deepseek")
        self.assertFalse(result["validation"].valid)
        self.assertIn("DELETE FROM", result["sql"])
        serializable = {**result, "validation": result["validation"].model_dump()}
        self.assertNotIn("sk-secret", json.dumps(serializable, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
