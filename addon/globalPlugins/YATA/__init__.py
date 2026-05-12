import config
import globalPluginHandler
import scriptHandler
import api
import ui as nvda_ui
import speech
import queueHandler
import threading
import logHandler
from . import ui
from . import cache
from .services.google import GoogleTranslate
from .services.bing import BingTranslate
from .services.deepl import DeepLTranslate
from .services.ollama import OllamaTranslate

try:
    from speech import speech as speechModule
except ImportError:
    speechModule = speech

import languageHandler
try:
    _default_lang = languageHandler.getLanguage().replace('_', '-')
    _default_lang = _default_lang.split('-')[0] # Get base language code like 'en', 'es', etc.
except Exception:
    _default_lang = 'en'

confspec = {
    "service": "string(default='google')",
    "source_lang": "string(default='auto')",
    "target_lang": f"string(default='{_default_lang}')",
    "deepl_key": "string(default='')",
    "ollama_address": "string(default='http://localhost:11434')",
    "ollama_model": "string(default='gemma:2b')",
    "ollama_system_prompt": "string(default='You are an expert translator. Translate the given text to the target language.')",
    "ollama_user_prompt": "string(default='{TEXT}')",
    "ollama_stream": "boolean(default=True)",
    "openai_key": "string(default='')",
    "openai_address": "string(default='https://api.openai.com/v1')",
    "openai_model": "string(default='gpt-4o-mini')",
    "openai_system_prompt": "string(default='You are an expert translator. Translate the given text to the target language.')",
    "openai_user_prompt": "string(default='{TEXT}')",
    "openai_stream": "boolean(default=True)",
    "gemini_key": "string(default='')",
    "gemini_model": "string(default='gemini-2.5-flash')",
    "gemini_system_prompt": "string(default='You are an expert translator. Translate the given text to the target language.')",
    "gemini_user_prompt": "string(default='{TEXT}')",
    "gemini_stream": "boolean(default=True)",
    "save_cache": "boolean(default=True)"
}
config.conf.spec["YATA"] = confspec

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "YATA"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toggling = False
        cache.init()
        self.auto_translate = False
        import gui
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(ui.YATASettingsPanel)
        
        self.speaking_translation = False
        self._original_speak = speechModule.speak
        speechModule.speak = self._hook_speak

        self._translation_cancel_events = set()
        
        self._trigger_translation_cancel_func = self._trigger_translation_cancel

        self._trigger_translation_cancel_func = self._trigger_translation_cancel

        try:
            speechModule.speechCanceled.register(self._hook_cancelSpeech)
            logHandler.log.debug("YATA: Registered speech.speechCanceled extension point")
        except Exception as e:
            logHandler.log.warning(f"YATA: Failed to register speech.speechCanceled: {e}")
            
        self.last_spoken_text = ""

    def terminate(self):
        if config.conf["YATA"].get("save_cache", True):
            cache.save()
        import gui
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(ui.YATASettingsPanel)
        except Exception:
            pass
        speechModule.speak = self._original_speak
        
        try:
            speechModule.speechCanceled.unregister(self._hook_cancelSpeech)
        except Exception as e:
            logHandler.log.warning(f"YATA: Failed to unregister speech.speechCanceled: {e}")

    def get_engine(self):
        conf = config.conf["YATA"]
        service = conf["service"]
        if service == "bing":
            return BingTranslate(conf.copy())
        elif service == "deepl":
            return DeepLTranslate(conf.copy())
        elif service == "ollama":
            from .services.ollama import OllamaTranslate
            return OllamaTranslate(conf.copy())
        elif service == "openai":
            from .services.openai import OpenAITranslate
            return OpenAITranslate(conf.copy())
        elif service == "gemini":
            from .services.gemini import GeminiTranslate
            return GeminiTranslate(conf.copy())
        else:
            return GoogleTranslate(conf.copy())

    def translate_text(self, text, speak=True, copy=False, browseable=False):
        if not text or not text.strip():
            return
            
        stripped = text.strip()
        if len(stripped) <= 1:
            return
        if stripped.isdigit():
            return

        app = ""
        try:
            import globalVars
            obj = globalVars.focusObject
            if obj and obj.appModule:
                app = obj.appModule.appName
        except Exception:
            pass

        conf = config.conf["YATA"]
        target_lang = conf["target_lang"]
        source_lang = conf["source_lang"]
        service = conf["service"]
        stream_ollama = conf.get(f"{service}_stream", True) and service in ("ollama", "openai", "gemini")
        
        cached = cache.get_translation(app, target_lang, text)
        
        request_cancel_event = threading.Event()
        self._translation_cancel_events.add(request_cancel_event)

        def speak_chunk(chunk):
            logHandler.log.debug(f"YATA speak_chunk evaluating: {chunk!r}, canceled: {request_cancel_event.is_set()}")
            if request_cancel_event.is_set():
                logHandler.log.debug("YATA speak_chunk canceled, returning.")
                return
            self.speaking_translation = True
            try:
                logHandler.log.debug(f"YATA calling nvda_ui.message for: {chunk!r}")
                nvda_ui.message(chunk)
            finally:
                self.speaking_translation = False

        if cached:
            if speak:
                speak_chunk(cached)
            if browseable:
                queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, cached, "YATA Translation")
            if copy:
                api.copyToClip(cached)
            self._translation_cancel_events.discard(request_cancel_event)
            return

        def do_translate():
            logHandler.log.debug(f"YATA do_translate started for text: {text!r}")
            try:
                engine = self.get_engine()
                try:
                    res = engine.translate(text, source_lang, target_lang, stream=stream_ollama)
                    if isinstance(res, str):
                        if request_cancel_event.is_set():
                            return
                        cache.set_translation(app, target_lang, text, res)
                        if speak:
                            queueHandler.queueFunction(queueHandler.eventQueue, speak_chunk, res)
                        if browseable:
                            queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, res, "YATA Translation")
                        if copy:
                            api.copyToClip(res)
                    else:
                        full_text = []
                        sentence_buffer = []
                        
                        def emit_buffer():
                            if sentence_buffer:
                                msg = "".join(sentence_buffer).strip()
                                logHandler.log.debug(f"YATA emit_buffer called with msg: {msg!r}")
                                if msg:
                                    queueHandler.queueFunction(queueHandler.eventQueue, speak_chunk, msg)
                                sentence_buffer.clear()

                        logHandler.log.debug("YATA entering streaming chunk loop")
                        for chunk in res:
                            logHandler.log.debug(f"YATA yielded chunk: {chunk!r}")
                            if request_cancel_event.is_set():
                                logHandler.log.debug("YATA chunk loop break: cancel event is set")
                                try:
                                    res.close()
                                except Exception:
                                    pass
                                break
                            full_text.append(chunk)
                            if speak:
                                sentence_buffer.append(chunk)
                                if any(c in chunk for c in ['.', '?', '!', '。', '？', '！', '\n']):
                                    emit_buffer()
                        
                        if speak:
                            emit_buffer()
                        
                        final_text = "".join(full_text)
                        if not request_cancel_event.is_set():
                            cache.set_translation(app, target_lang, text, final_text)
                            if browseable:
                                queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, final_text, "YATA Translation")
                            if copy:
                                api.copyToClip(final_text)

                except Exception as e:
                    if not request_cancel_event.is_set():
                        queueHandler.queueFunction(queueHandler.eventQueue, speak_chunk, f"Error: {e}")
            finally:
                self._translation_cancel_events.discard(request_cancel_event)

        threading.Thread(target=do_translate).start()

    def _hook_speak(self, speechSequence, *args, **kwargs):
        if self.speaking_translation:
            self._original_speak(speechSequence, *args, **kwargs)
            return

        texts = [x for x in speechSequence if isinstance(x, str)]
        if texts:
            text = " ".join(texts)
            self.last_spoken_text = text
            if self.auto_translate:
                self.translate_text(text, speak=True, copy=False)
                return
        self._original_speak(speechSequence, *args, **kwargs)

    def _trigger_translation_cancel(self):
        logHandler.log.debug("YATA: _trigger_translation_cancel called")
        for ev in list(self._translation_cancel_events):
            ev.set()
        self._translation_cancel_events.clear()

    def _hook_cancelSpeech(self, *args, **kwargs):
        logHandler.log.debug("YATA: _hook_cancelSpeech triggered")
        self._trigger_translation_cancel()

    def bindGestures(self, gestures):
        super().bindGestures(gestures)

    def getScript(self, gesture):
        if not self.toggling:
            return super().getScript(gesture)
        script = super().getScript(gesture)
        if not script:
            def dummy_script(g):
                self.toggling = False
                self.clearGestureBindings()
                self.bindGestures(self.__gestures)
                import tones
                tones.beep(120, 100)
            return dummy_script
        
        def wrapped_script(g):
            try:
                script(g)
            finally:
                if script.__name__ not in ("script_layerNext", "script_layerPrev"):
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
        self._layer_index = 0
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

    @scriptHandler.script(description="Translate selection in browseable message")
    def script_translateSelectionBrowseable(self, gesture):
        obj = api.getCaretObject()
        try:
            import textInfos
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and not info.isCollapsed:
                text = info.text
                self.translate_text(text, speak=False, copy=False, browseable=True)
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

    @scriptHandler.script(description="Translate last spoken phrase in browseable message")
    def script_translateLastBrowseable(self, gesture):
        if self.last_spoken_text:
            self.translate_text(self.last_spoken_text, speak=False, copy=False, browseable=True)
        else:
            nvda_ui.message("No last phrase found")

    @scriptHandler.script(description="Translate clipboard")
    def script_translateClipboard(self, gesture):
        text = api.getClipData()
        if text and isinstance(text, str) and not text.isspace():
            self.translate_text(text, speak=True, copy=False)
        else:
            nvda_ui.message("No text on clipboard")

    @scriptHandler.script(description="Translate clipboard in browseable message")
    def script_translateClipboardBrowseable(self, gesture):
        text = api.getClipData()
        if text and isinstance(text, str) and not text.isspace():
            self.translate_text(text, speak=False, copy=False, browseable=True)
        else:
            nvda_ui.message("No text on clipboard")

    @scriptHandler.script(description="Toggle auto translate")
    def script_toggleAuto(self, gesture):
        if not self.auto_translate: nvda_ui.message("Auto translate on")
        self.auto_translate = not self.auto_translate
        if not self.auto_translate: nvda_ui.message("Auto translate off")

    _layer_commands = [
        ("s", "translateSelection", "Translate selection"),
        ("shift+s", "translateSelectionBrowseable", "Translate selection in browseable message"),
        ("t", "translateLast", "Translate last spoken phrase"),
        ("shift+t", "translateLastBrowseable", "Translate last spoken phrase in browseable message"),
        ("c", "translateClipboard", "Translate clipboard"),
        ("shift+c", "translateClipboardBrowseable", "Translate clipboard in browseable message"),
        ("a", "toggleAuto", "Toggle auto translate"),
    ]

    @scriptHandler.script()
    def script_layerNext(self, gesture):
        self._layer_index = (self._layer_index + 1) % len(self._layer_commands)
        self._announce_layer_command()
        
    @scriptHandler.script()
    def script_layerPrev(self, gesture):
        self._layer_index = (self._layer_index - 1) % len(self._layer_commands)
        self._announce_layer_command()
        
    def _announce_layer_command(self):
        cmd = self._layer_commands[self._layer_index]
        nvda_ui.message(f"{cmd[2]}, {cmd[0]}")
        
    @scriptHandler.script()
    def script_layerExecute(self, gesture):
        cmd = self._layer_commands[self._layer_index]
        script_name = f"script_{cmd[1]}"
        getattr(self, script_name)(gesture)

    __layerGestures = {
        "kb:s": "translateSelection",
        "kb:shift+s": "translateSelectionBrowseable",
        "kb:t": "translateLast",
        "kb:shift+t": "translateLastBrowseable",
        "kb:c": "translateClipboard",
        "kb:shift+c": "translateClipboardBrowseable",
        "kb:a": "toggleAuto",
        "kb:tab": "layerNext",
        "kb:shift+tab": "layerPrev",
        "kb:enter": "layerExecute"
    }
    
    __gestures = {
        "kb:NVDA+shift+t": "layer"
    }
