from pathlib import Path
import importlib.util
import types
import unittest


MODULE_PATH = (
    Path(__file__).parents[1]
    / "addon"
    / "globalPlugins"
    / "YATA"
    / "speech_filter.py"
)
SPEC = importlib.util.spec_from_file_location("yata_speech_filter", MODULE_PATH)
speech_filter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(speech_filter)


class DummyCommand:
    pass


class SpeechFilterFunctionsTests(unittest.TestCase):
    def test_extract_excludes_nvda_metadata_when_enabled(self):
        sequence = [
            speech_filter.TranslatableString("Save"),
            speech_filter.UntranslatableString("button"),
            DummyCommand(),
            "document text",
        ]

        text, indices = speech_filter.extract_translatable_text(
            sequence, enabled=True
        )

        self.assertEqual("Save document text", text)
        self.assertEqual([0, 3], indices)

    def test_extract_includes_every_string_when_disabled(self):
        sequence = [
            speech_filter.TranslatableString("Save"),
            speech_filter.UntranslatableString("button"),
        ]

        text, indices = speech_filter.extract_translatable_text(
            sequence, enabled=False
        )

        self.assertEqual("Save button", text)
        self.assertEqual([0, 1], indices)

    def test_reconstruction_preserves_metadata_and_speech_commands(self):
        command = DummyCommand()
        sequence = [
            "Save",
            command,
            speech_filter.UntranslatableString("button"),
            "file",
        ]

        result = speech_filter.reconstruct_speech_sequence(
            sequence, [0, 3], "Zapisz plik"
        )

        self.assertEqual("Zapisz plik", result[0])
        self.assertIs(command, result[1])
        self.assertEqual("button", result[2])
        self.assertIsInstance(
            result[2], speech_filter.UntranslatableString
        )
        self.assertEqual("", result[3])


class SmartSpeechFilterHookTests(unittest.TestCase):
    def make_speech_modules(self):
        module = types.SimpleNamespace()
        package = types.SimpleNamespace()

        def get_properties(**kwargs):
            return [kwargs.get("name", ""), "button"]

        def get_format_field(*args, **kwargs):
            return ["heading level 2"]

        def get_control_field(attrs, *args, **kwargs):
            return [attrs["content"], "link"]

        def get_spelling(*args, **kwargs):
            yield "A"

        def get_selection_message(message, text):
            return [message % text]

        def get_speak_message(message):
            return [message]

        def speak_typed(*args, **kwargs):
            self.assertTrue(filter_instance.is_suppressed)

        functions = {
            "getPropertiesSpeech": get_properties,
            "getFormatFieldSpeech": get_format_field,
            "getControlFieldSpeech": get_control_field,
            "getSpellingSpeech": get_spelling,
            "_getSelectionMessageSpeech": get_selection_message,
            "speakTypedCharacters": speak_typed,
        }
        for name, function in functions.items():
            setattr(module, name, function)
            setattr(package, name, function)
        module._getSpeakMessageSpeech = get_speak_message
        module.MAX_LENGTH_FOR_SELECTION_REPORTING = 512

        filter_instance = speech_filter.SmartSpeechFilter(package, module)
        return package, module, filter_instance

    def test_hooks_tag_user_content_and_nvda_metadata(self):
        package, module, filter_instance = self.make_speech_modules()
        original_properties = module.getPropertiesSpeech
        filter_instance.register()
        self.addCleanup(filter_instance.unregister)

        properties = module.getPropertiesSpeech(name="Save")
        control = module.getControlFieldSpeech({"content": "Read me"})
        formatting = module.getFormatFieldSpeech()
        spelling = list(module.getSpellingSpeech("A"))
        selection = module._getSelectionMessageSpeech(
            "selected %s", "document text"
        )

        self.assertIsInstance(
            properties[0], speech_filter.TranslatableString
        )
        self.assertIsInstance(
            properties[1], speech_filter.UntranslatableString
        )
        self.assertIsInstance(control[0], speech_filter.TranslatableString)
        self.assertIsInstance(
            control[1], speech_filter.UntranslatableString
        )
        self.assertIsInstance(
            formatting[0], speech_filter.UntranslatableString
        )
        self.assertIsInstance(
            spelling[0], speech_filter.UntranslatableString
        )
        self.assertIsInstance(
            selection[0], speech_filter.UntranslatableString
        )
        self.assertIsInstance(
            selection[1], speech_filter.TranslatableString
        )

        module.speakTypedCharacters("a")
        filter_instance.unregister()
        self.assertIs(module.getPropertiesSpeech, original_properties)
        self.assertIs(package.getPropertiesSpeech, original_properties)


if __name__ == "__main__":
    unittest.main()
