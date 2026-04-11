import config
import globalPluginHandler
import scriptHandler
import api
import ui as nvda_ui
import speech
import queueHandler
import threading
from . import ui
from . import cache
from .services.google import GoogleTranslate
from .services.bing import BingTranslate
from .services.deepl import DeepLTranslate
from .services.ollama import OllamaTranslate

confspec = {
    "service": "string(default='google')",
    "source_lang": "string(default='auto')",
    "target_lang": "string(default='en')",
    "deepl_key": "string(default='')",
    "ollama_address": "string(default='http://localhost:11434')",
    "ollama_model": "string(default='gemma:2b')",
    "ollama_system_prompt": "string(default='You are an expert translator. Translate the given text to the target language.')",
    "ollama_stream": "boolean(default=True)"
}
config.conf.spec["ultimateTranslate"] = confspec

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "Ultimate Translate"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toggling = False
        cache.init()
        self.auto_translate = False
        import gui
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(ui.UltimateTranslateSettingsPanel)
        
        self._original_speak = speech.speak
        speech.speak = self._hook_speak
        self.last_spoken_text = ""

    def terminate(self):
        cache.save()
        import gui
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(ui.UltimateTranslateSettingsPanel)
        except Exception:
            pass
        speech.speak = self._original_speak

    def get_engine(self):
        conf = config.conf["ultimateTranslate"]
        service = conf["service"]
        if service == "bing":
            return BingTranslate(conf.copy())
        elif service == "deepl":
            return DeepLTranslate(conf.copy())
        elif service == "ollama":
            return OllamaTranslate(conf.copy())
        else:
            return GoogleTranslate(conf.copy())

    def translate_text(self, text, speak=True, copy=False):
        if not text or not text.strip():
            return
            
        app = ""
        try:
            obj = api.getForegroundObject()
            if obj and obj.appModule:
                app = obj.appModule.appModuleName
        except Exception:
            pass

        conf = config.conf["ultimateTranslate"]
        target_lang = conf["target_lang"]
        source_lang = conf["source_lang"]
        stream_ollama = conf.get("ollama_stream", True) and conf["service"] == "ollama"
        
        cached = cache.get_translation(app, target_lang, text)
        if cached:
            if speak:
                nvda_ui.message(cached)
            if copy:
                api.copyToClip(cached)
            return
            
        def do_translate():
            engine = self.get_engine()
            try:
                res = engine.translate(text, source_lang, target_lang, stream=stream_ollama)
                if isinstance(res, str):
                    cache.set_translation(app, target_lang, text, res)
                    if speak:
                        queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.message, res)
                    if copy:
                        api.copyToClip(res)
                else:
                    full_text = []
                    for chunk in res:
                        full_text.append(chunk)
                        if speak:
                             queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.message, chunk)
                    
                    final_text = "".join(full_text)
                    cache.set_translation(app, target_lang, text, final_text)
                    if copy:
                        api.copyToClip(final_text)

            except Exception as e:
                queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.message, f"Error: {e}")

        threading.Thread(target=do_translate).start()

    def _hook_speak(self, speechSequence, *args, **kwargs):
        texts = [x for x in speechSequence if isinstance(x, str)]
        if texts:
            text = " ".join(texts)
            self.last_spoken_text = text
            if self.auto_translate:
                self.translate_text(text, speak=True, copy=False)
                return
        self._original_speak(speechSequence, *args, **kwargs)

    def bindGestures(self, gestures):
        super().bindGestures(gestures)

    def getScript(self, gesture):
        if not self.toggling:
            return super().getScript(gesture)
        script = super().getScript(gesture)
        if not script:
            self.toggling = False
            self.clearGestureBindings()
            self.bindGestures(self.__gestures)
            import tones
            tones.beep(120, 100)
            return None
        
        def wrapped_script(g):
            try:
                script(g)
            finally:
                self.toggling = False
                self.clearGestureBindings()
                self.bindGestures(self.__gestures)
        return wrapped_script
        
    @scriptHandler.script(description="Translation Layer (Press S, T, C, or A)")
    def script_layer(self, gesture):
        if self.toggling:
            import tones
            tones.beep(120, 100)
            return
        self.bindGestures(self.__layerGestures)
        self.toggling = True
        import tones
        tones.beep(200, 10)
        
    @scriptHandler.script(description="Translate selection")
    def script_translateSelection(self, gesture):
        obj = api.getCaretObject()
        try:
            import textInfos
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and not info.isCollapsed:
                text = info.text
                self.translate_text(text, speak=True, copy=False)
            else:
                nvda_ui.message("No selection")
        except Exception:
            nvda_ui.message("No selection")

    @scriptHandler.script(description="Translate last spoken phrase")
    def script_translateLast(self, gesture):
        if self.last_spoken_text:
            self.translate_text(self.last_spoken_text, speak=True, copy=False)
        else:
            nvda_ui.message("No last phrase found")

    @scriptHandler.script(description="Translate clipboard")
    def script_translateClipboard(self, gesture):
        text = api.getClipData()
        if text and isinstance(text, str) and not text.isspace():
            self.translate_text(text, speak=True, copy=False)
        else:
            nvda_ui.message("No text on clipboard")

    @scriptHandler.script(description="Toggle auto translate")
    def script_toggleAuto(self, gesture):
        self.auto_translate = not self.auto_translate
        nvda_ui.message("Auto translate on" if self.auto_translate else "Auto translate off")

    __layerGestures = {
        "kb:s": "translateSelection",
        "kb:t": "translateLast",
        "kb:c": "translateClipboard",
        "kb:a": "toggleAuto",
    }
    
    __gestures = {
        "kb:NVDA+shift+t": "layer"
    }
