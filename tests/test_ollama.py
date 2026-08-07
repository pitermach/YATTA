import importlib.util
import json
from pathlib import Path
import sys
import threading
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
        self.closed = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body

    def readline(self):
        return next(self.lines, b"")

    def close(self):
        self.closed.set()


class OllamaTranslateTests(unittest.TestCase):
    def make_engine(self, **overrides):
        config = {
            "ollama_address": "http://localhost:11434",
            "ollama_model": "test-model",
            "ollama_system_prompt": "",
            "ollama_user_prompt": "{TEXT}",
        }
        config.update(overrides)
        return ollama_service.OllamaTranslate(config)

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

    def test_slow_unloaded_model_announces_loading(self):
        generate_response = FakeResponse(
            body=json.dumps({"response": "translated"}).encode("utf-8")
        )
        release_generate = threading.Event()
        requested_urls = []

        def open_request(req, timeout):
            requested_urls.append(req.full_url)
            if req.full_url.endswith("/api/ps"):
                return FakeResponse(body=b'{"models": []}')
            release_generate.wait(1)
            return generate_response

        statuses = []
        engine = self.make_engine()

        def receive_status(status):
            statuses.append(status)
            release_generate.set()

        engine.status_callback = receive_status
        with patch.object(
            ollama_service, "OLLAMA_STATUS_CHECK_DELAY", 0.01
        ), patch.object(
            ollama_service.urllib.request,
            "urlopen",
            side_effect=open_request,
        ):
            result = engine.translate("text", stream=False)

        self.assertEqual("translated", result)
        self.assertEqual(["loading_model"], statuses)
        self.assertIn("http://localhost:11434/api/ps", requested_urls)

    def test_slow_running_model_does_not_announce_loading(self):
        generate_response = FakeResponse(
            body=json.dumps({"response": "translated"}).encode("utf-8")
        )
        release_generate = threading.Event()

        def open_request(req, timeout):
            if req.full_url.endswith("/api/ps"):
                release_generate.set()
                return FakeResponse(
                    body=b'{"models": [{"name": "test-model:latest"}]}'
                )
            release_generate.wait(1)
            return generate_response

        statuses = []
        engine = self.make_engine()
        engine.status_callback = statuses.append
        with patch.object(
            ollama_service, "OLLAMA_STATUS_CHECK_DELAY", 0.01
        ), patch.object(
            ollama_service.urllib.request,
            "urlopen",
            side_effect=open_request,
        ):
            result = engine.translate("text", stream=False)

        self.assertEqual("translated", result)
        self.assertEqual([], statuses)

    def test_status_failure_cancels_pending_translation(self):
        generate_response = FakeResponse(
            body=json.dumps({"response": "too late"}).encode("utf-8")
        )
        release_generate = threading.Event()

        def open_request(req, timeout):
            if req.full_url.endswith("/api/ps"):
                raise OSError("server unavailable")
            release_generate.wait(1)
            return generate_response

        try:
            with patch.object(
                ollama_service, "OLLAMA_STATUS_CHECK_DELAY", 0.01
            ), patch.object(
                ollama_service.urllib.request,
                "urlopen",
                side_effect=open_request,
            ):
                with self.assertRaisesRegex(
                    Exception, "Ollama status check failed: server unavailable"
                ):
                    self.make_engine().translate("text", stream=False)
        finally:
            release_generate.set()

        self.assertTrue(generate_response.closed.wait(1))

    def test_status_failure_after_translation_response_is_ignored(self):
        generate_response = FakeResponse(
            body=json.dumps({"response": "translated"}).encode("utf-8")
        )
        release_generate = threading.Event()
        generate_returned = threading.Event()

        def open_request(req, timeout):
            if req.full_url.endswith("/api/ps"):
                release_generate.set()
                generate_returned.wait(1)
                raise OSError("late status failure")
            release_generate.wait(1)
            generate_returned.set()
            return generate_response

        with patch.object(
            ollama_service, "OLLAMA_STATUS_CHECK_DELAY", 0.01
        ), patch.object(
            ollama_service.urllib.request,
            "urlopen",
            side_effect=open_request,
        ):
            result = self.make_engine().translate("text", stream=False)

        self.assertEqual("translated", result)

    def test_cloud_models_skip_local_loading_probe(self):
        response = FakeResponse(
            body=json.dumps({"response": "translated"}).encode("utf-8")
        )
        engine = self.make_engine(ollama_model="gpt-oss:120b-cloud")

        with patch.object(
            ollama_service.urllib.request, "urlopen", return_value=response
        ) as urlopen:
            result = engine.translate("text", stream=False)

        self.assertEqual("translated", result)
        self.assertEqual(1, urlopen.call_count)
        self.assertTrue(
            engine._is_cloud_request("https://ollama.com", "gpt-oss:120b")
        )


if __name__ == "__main__":
    unittest.main()
