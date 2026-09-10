import importlib.util
from pathlib import Path
import os
import sys
import types
import unittest
from unittest import mock


SETTINGS_PATH = (
    Path(__file__).parents[1]
    / "addon"
    / "globalPlugins"
    / "YATA"
    / "settings.py"
)
CONFIG_PATH = r"C:\nvda-config"
GLOBAL_FILEPATH = os.path.join(CONFIG_PATH, "yatta", "settings", "global.ini")


class FakeConfigObj(dict):
    files = {}

    def __init__(self, infile=None, encoding=None):
        if isinstance(infile, (str, Path)):
            super().__init__(self.files.get(str(infile), {}))
            self.filename = str(infile)
        else:
            super().__init__(infile or {})
            self.filename = None

    def write(self):
        self.files[self.filename] = dict(self)


class FailingConfigObj(FakeConfigObj):
    def write(self):
        raise OSError("write failed")


fake_configobj = types.ModuleType("configobj")
fake_configobj.ConfigObj = FakeConfigObj
sys.modules.setdefault("configobj", fake_configobj)
spec = importlib.util.spec_from_file_location("yatta_settings", SETTINGS_PATH)
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)


class FakeNVDAConfig:
    def __init__(self, base_config):
        self.profiles = [base_config]
        self.spec = {"YATTA": {"old": "spec"}}
        self.save_count = 0

    def save(self):
        self.save_count += 1


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message, *args):
        self.messages.append(message % args)


class GlobalSettingsTests(unittest.TestCase):
    def setUp(self):
        FakeConfigObj.files.clear()

    def test_migrates_legacy_section_and_removes_it_from_nvda_config(self):
        FakeConfigObj.files[GLOBAL_FILEPATH] = {
            "service": "google",
            "openai_key": "existing-key",
        }
        legacy = {
            "service": "openai",
            "openai_key": "migrated-key",
            "save_cache": "False",
            "future_setting": "preserved",
        }
        nvda_config = FakeNVDAConfig({"YATTA": legacy})
        logger = FakeLogger()

        with mock.patch.object(settings.os, "makedirs"), mock.patch.object(
            settings.os.path,
            "exists",
            side_effect=lambda path: path in FakeConfigObj.files,
        ):
            result = settings.initialize(
                nvda_config,
                CONFIG_PATH,
                "pl",
                logger,
                FakeConfigObj,
            )

        self.assertEqual("openai", result["service"])
        self.assertEqual("migrated-key", result["openai_key"])
        self.assertFalse(result["save_cache"])
        self.assertEqual("preserved", result["future_setting"])
        self.assertNotIn("YATTA", nvda_config.profiles[0])
        self.assertNotIn("YATTA", nvda_config.spec)
        self.assertEqual(1, nvda_config.save_count)
        self.assertEqual("False", FakeConfigObj.files[GLOBAL_FILEPATH]["save_cache"])
        self.assertIn(GLOBAL_FILEPATH, logger.messages[0])

    def test_failed_migration_write_keeps_legacy_section(self):
        legacy = {"service": "openai"}
        nvda_config = FakeNVDAConfig({"YATTA": legacy})
        logger = FakeLogger()

        with mock.patch.object(settings.os, "makedirs"), mock.patch.object(
            settings.os.path,
            "exists",
            return_value=False,
        ):
            with self.assertRaises(OSError):
                settings.initialize(
                    nvda_config,
                    CONFIG_PATH,
                    "en",
                    logger,
                    FailingConfigObj,
                )

        self.assertIn("YATTA", nvda_config.profiles[0])
        self.assertEqual(0, nvda_config.save_count)
        self.assertEqual([], logger.messages)

    def test_loads_existing_global_file_without_touching_nvda_config(self):
        FakeConfigObj.files[GLOBAL_FILEPATH] = {
            "service": "gemini",
            "gemini_stream": "False",
            "target_lang": "de",
        }
        nvda_config = FakeNVDAConfig({})

        with mock.patch.object(settings.os, "makedirs"), mock.patch.object(
            settings.os.path,
            "exists",
            side_effect=lambda path: path in FakeConfigObj.files,
        ):
            result = settings.initialize(
                nvda_config,
                CONFIG_PATH,
                "pl",
                FakeLogger(),
                FakeConfigObj,
            )

        self.assertEqual("gemini", result["service"])
        self.assertFalse(result["gemini_stream"])
        self.assertEqual("de", result["target_lang"])
        self.assertEqual(0, nvda_config.save_count)

    def test_first_run_creates_global_file_with_localized_target_default(self):
        nvda_config = FakeNVDAConfig({})
        with mock.patch.object(settings.os, "makedirs"), mock.patch.object(
            settings.os.path,
            "exists",
            return_value=False,
        ):
            result = settings.initialize(
                nvda_config,
                CONFIG_PATH,
                "pl",
                FakeLogger(),
                FakeConfigObj,
            )

        self.assertEqual("pl", result["target_lang"])
        self.assertEqual("pl", FakeConfigObj.files[GLOBAL_FILEPATH]["target_lang"])
        self.assertEqual(0, nvda_config.save_count)

    def test_save_writes_changes_to_global_file(self):
        with mock.patch.object(settings.os, "makedirs"), mock.patch.object(
            settings.os.path,
            "exists",
            return_value=False,
        ):
            settings.initialize(
                FakeNVDAConfig({}),
                CONFIG_PATH,
                "en",
                FakeLogger(),
                FakeConfigObj,
            )
        settings.get_global_config()["target_lang"] = "de"

        settings.save(FakeConfigObj)

        self.assertEqual("de", FakeConfigObj.files[GLOBAL_FILEPATH]["target_lang"])


if __name__ == "__main__":
    unittest.main()
