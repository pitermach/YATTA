import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


SERVICES_DIR = (
    Path(__file__).parents[1] / "addon" / "globalPlugins" / "YATA" / "services"
)


def load_ollama_module():
    """Load the service without importing NVDA-only YATA dependencies."""
    package_name = "yata_ollama_services_under_test"
    package_spec = importlib.util.spec_from_file_location(
        package_name,
        SERVICES_DIR / "__init__.py",
        submodule_search_locations=[str(SERVICES_DIR)],
    )
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)

    module_name = f"{package_name}.ollama"
    module_spec = importlib.util.spec_from_file_location(
        module_name, SERVICES_DIR / "ollama.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


ollama_service = load_ollama_module()


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


class OllamaTranslateTests(unittest.TestCase):
    def make_engine(self):
        return ollama_service.OllamaTranslate(
            {
                "ollama_address": "http://localhost:11434",
                "ollama_model": "test-model",
                "ollama_system_prompt": "",
                "ollama_user_prompt": "{TEXT}",
            }
        )

    def test_non_streaming_request_uses_twenty_second_timeout(self):
        response = FakeResponse(
            body=json.dumps({"response": "translated"}).encode("utf-8")
        )

        with patch.object(
            ollama_service.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            result = self.make_engine().translate("text", stream=False)

        self.assertEqual("translated", result)
        self.assertEqual(20, urlopen.call_args.kwargs["timeout"])

    def test_streaming_request_uses_twenty_second_timeout(self):
        response = FakeResponse(
            lines=(
                b'{"response":"translated","done":false}\n',
                b'{"done":true}\n',
            )
        )

        with patch.object(
            ollama_service.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            chunks = list(self.make_engine().translate("text", stream=True))

        self.assertEqual(["translated"], chunks)
        self.assertEqual(20, urlopen.call_args.kwargs["timeout"])


if __name__ == "__main__":
    unittest.main()
