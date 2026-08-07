import ast
from pathlib import Path
import re
import threading
import time
import types
import unittest


PLUGIN_PATH = (
    Path(__file__).parents[1]
    / "addon"
    / "globalPlugins"
    / "YATA"
    / "__init__.py"
)


def load_translate_text(namespace):
    """Load the real method without importing NVDA-only modules."""
    tree = ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))
    plugin_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "GlobalPlugin"
    )
    method = next(
        node
        for node in plugin_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "translate_text"
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[method], type_ignores=[])
    )
    exec(compile(module, str(PLUGIN_PATH), "exec"), namespace)
    return namespace["translate_text"]


class ImmediateQueueHandler:
    eventQueue = object()

    @staticmethod
    def queueFunction(event_queue, function, *args):
        function(*args)


class ImmediateJobQueue:
    def put(self, job):
        job()


class FakeCache:
    def __init__(self):
        self.saved = []

    def get_translation(self, app, language, text):
        return None

    def set_translation(
        self, app, language, source, translation, is_regexp=False
    ):
        self.saved.append(
            (app, language, source, translation, is_regexp)
        )


class MissingTokenEngine:
    max_chars = 4000
    requires_sleep = False
    supports_language_detection = False

    def translate(self, text, source_lang, target_lang, stream=False):
        self.request_text = text
        return "Falchion <token1>, physical curved sword"


class UnusedTokenWarningTests(unittest.TestCase):
    def test_auto_translation_announces_missing_number_token(self):
        messages = []
        beeps = []
        completed = []
        fake_cache = FakeCache()
        engine = MissingTokenEngine()
        config = types.SimpleNamespace(
            conf={
                "YATTA": {
                    "service": "test",
                    "source_lang": "ja",
                    "target_lang": "en",
                    "auto_swap": False,
                    "separate_numbers": True,
                    "test_stream": False,
                    "play_sound": False,
                }
            }
        )
        tones = types.SimpleNamespace(
            beep=lambda frequency, duration: beeps.append(
                (frequency, duration)
            )
        )
        nvda_ui = types.SimpleNamespace(message=messages.append)
        namespace = {
            "NUM_REGEX": re.compile(r"(-?\d+(?:[.,/]\d+)*)"),
            "TOKEN_REGEX": re.compile(r"<token\d+>"),
            "SENTENCE_BREAKS_RE": re.compile(r"[.,!?;:\n]"),
            "cache": fake_cache,
            "config": config,
            "nvda_ui": nvda_ui,
            "queueHandler": ImmediateQueueHandler,
            "re": re,
            "threading": threading,
            "time": time,
            "tones": tones,
            "_": lambda text: text,
        }

        class Plugin:
            translate_text = load_translate_text(namespace)

            def __init__(self):
                self._translation_cancel_events = set()
                self._translation_queue = ImmediateJobQueue()
                self.speaking_translation = False
                self.is_long_operation = False

            def _get_app_name(self):
                return "testApp"

            def _get_app_setting(self, app, key, default):
                return default

            def _get_play_sound_state(self, app):
                return False

            def get_engine(self, conf_dict=None):
                return engine

        plugin = Plugin()
        source = "ファルシオン           2000、 物理23　曲刀"

        started = plugin.translate_text(
            source,
            speak=False,
            on_complete=completed.append,
        )

        self.assertTrue(started)
        self.assertIn("<token1>", engine.request_text)
        self.assertIn("<token2>", engine.request_text)
        self.assertEqual(
            ["Falchion 2000, physical curved sword"], completed
        )
        self.assertEqual([(1500, 50)], beeps)
        self.assertEqual(["Warning, unused values: 23"], messages)
        self.assertEqual([], fake_cache.saved)


if __name__ == "__main__":
    unittest.main()
