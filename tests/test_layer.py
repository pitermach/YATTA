import ast
from pathlib import Path
import types
import unittest


PLUGIN_PATH = (
    Path(__file__).parents[1]
    / "addon"
    / "globalPlugins"
    / "YATA"
    / "__init__.py"
)


def get_plugin_class():
    tree = ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "GlobalPlugin"
    )


def load_methods(names, namespace):
    plugin_class = get_plugin_class()
    methods = []
    for node in plugin_class.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            node.decorator_list = []
            methods.append(node)
    module = ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[]))
    exec(compile(module, str(PLUGIN_PATH), "exec"), namespace)
    return {name: namespace[name] for name in names}


class LayerTests(unittest.TestCase):
    def make_plugin(self):
        self.messages = []
        self.braille_messages = []
        self.beeps = []
        namespace = {
            "nvda_ui": types.SimpleNamespace(message=self.messages.append),
            "braille": types.SimpleNamespace(
                handler=types.SimpleNamespace(
                    message=self.braille_messages.append,
                ),
            ),
            "tones": types.SimpleNamespace(
                beep=lambda frequency, duration: self.beeps.append(
                    (frequency, duration)
                )
            ),
            "_": lambda text: text,
        }
        methods = load_methods(
            {
                "_report_invalid_layer_command",
                "script_layer",
                "script_layerHelp",
            },
            namespace,
        )

        class Plugin:
            _report_invalid_layer_command = methods[
                "_report_invalid_layer_command"
            ]
            script_layer = methods["script_layer"]
            script_layerHelp = methods["script_layerHelp"]

            def __init__(self):
                self.toggling = False
                self.bound_gestures = []
                self.__dict__["__layerGestures"] = {"kb:h": "layerHelp"}

            def bindGestures(self, gestures):
                self.bound_gestures.append(gestures)

        return Plugin()

    def test_entering_layer_announces_prompt_in_braille_only(self):
        plugin = self.make_plugin()

        plugin.script_layer(None)

        self.assertTrue(plugin.toggling)
        self.assertEqual([(200, 10)], self.beeps)
        self.assertEqual([], self.messages)
        self.assertEqual(
            ["YATTA, enter a command"],
            self.braille_messages,
        )
        self.assertEqual([{"kb:h": "layerHelp"}], plugin.bound_gestures)

    def test_layer_error_announces_invalid_command(self):
        plugin = self.make_plugin()
        plugin.toggling = True

        plugin.script_layer(None)

        self.assertEqual([(120, 100)], self.beeps)
        self.assertEqual([], self.messages)
        self.assertEqual(["Invalid command"], self.braille_messages)

    def test_help_announces_instructions_without_exiting_layer(self):
        plugin = self.make_plugin()
        plugin.toggling = True

        plugin.script_layerHelp(None)

        self.assertTrue(plugin.toggling)
        self.assertEqual([], self.braille_messages)
        self.assertEqual(
            [
                "Press tab to go through all available commands. "
                "Press Enter to activate the selected command."
            ],
            self.messages,
        )

    def test_help_is_hidden_and_has_all_layer_bindings(self):
        plugin_class = get_plugin_class()
        help_method = next(
            node
            for node in plugin_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "script_layerHelp"
        )
        decorator = help_method.decorator_list[0]
        self.assertIsInstance(decorator, ast.Call)
        self.assertEqual([], decorator.args)
        self.assertEqual([], decorator.keywords)

        gesture_assignment = next(
            node
            for node in plugin_class.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "__layerGestures"
                for target in node.targets
            )
        )
        gestures = ast.literal_eval(gesture_assignment.value)
        self.assertEqual("layerHelp", gestures["kb:h"])
        self.assertEqual("layerHelp", gestures["kb:shift+/"])
        self.assertEqual("layerHelp", gestures["kb:f1"])

        get_script = next(
            node
            for node in plugin_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "getScript"
        )
        self.assertIn("script_layerHelp", ast.unparse(get_script))
        self.assertIn("_report_invalid_layer_command", ast.unparse(get_script))


if __name__ == "__main__":
    unittest.main()
