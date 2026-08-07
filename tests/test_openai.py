import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


SERVICES_DIR = (
    Path(__file__).parents[1] / "addon" / "globalPlugins" / "YATA" / "services"
)


def load_openai_module():
    """Load the service without importing NVDA-only YATA dependencies."""
    package_name = "yata_services_under_test"
    package_spec = importlib.util.spec_from_file_location(
        package_name,
        SERVICES_DIR / "__init__.py",
        submodule_search_locations=[str(SERVICES_DIR)],
    )
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)

    module_name = f"{package_name}.openai"
    module_spec = importlib.util.spec_from_file_location(
        module_name, SERVICES_DIR / "openai.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


openai_service = load_openai_module()


class FakeResponse:
    def __init__(self, body=b"", lines=()):
        self.body = body
        self.lines = iter(lines)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body

    def readline(self):
        return next(self.lines, b"")


class OpenAITranslateTests(unittest.TestCase):
    def make_engine(self, **overrides):
        config = {
            "openai_key": "sk-test",
            "openai_address": "https://api.openai.com/v1",
            "openai_model": "test-model",
            "openai_system_prompt": "",
            "openai_user_prompt": "Translate: {TEXT}",
        }
        config.update(overrides)
        return openai_service.OpenAITranslate(config)

    def test_unicode_text_is_sent_as_utf8_json(self):
        response_body = json.dumps(
            {"choices": [{"message": {"content": "translated"}}]}
        ).encode("utf-8")
        response = FakeResponse(body=response_body)

        with patch.object(
            openai_service.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            result = self.make_engine().translate("zaścianka — 東京")

        self.assertEqual("translated", result)
        request = urlopen.call_args.args[0]
        self.assertEqual(
            "application/json; charset=utf-8", request.get_header("Content-type")
        )
        self.assertIn("zaścianka — 東京", request.data.decode("utf-8"))
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            "Translate: zaścianka — 東京", payload["messages"][0]["content"]
        )

    def test_unicode_text_is_sent_when_streaming(self):
        response = FakeResponse(
            lines=(
                'data: {"choices":[{"delta":{"content":"tłumaczenie"}}]}\n'.encode(
                    "utf-8"
                ),
                b"data: [DONE]\n",
            )
        )

        with patch.object(
            openai_service.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            chunks = list(self.make_engine().translate("zaś", stream=True))

        self.assertEqual(["tłumaczenie"], chunks)
        request = urlopen.call_args.args[0]
        self.assertIn("zaś", request.data.decode("utf-8"))

    def test_non_ascii_api_key_has_an_actionable_error(self):
        engine = self.make_engine(openai_key="sk-test-zaś")

        with patch.object(openai_service.urllib.request, "urlopen") as urlopen:
            with self.assertRaisesRegex(Exception, "copy and paste the API key again"):
                engine.translate("ordinary text")

        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
