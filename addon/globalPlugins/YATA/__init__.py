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
    "save_cache": "boolean(default=True)",
    "separate_numbers": "boolean(default=False)"
}
config.conf.spec["YATA"] = confspec

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "YATA"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toggling = False
        cache.init()
        self.auto_translate = False
        self.auto_translate_apps = {}
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

    def _get_app_name(self):
        try:
            import globalVars
            obj = globalVars.focusObject
            if obj and obj.appModule:
                return obj.appModule.appName
        except Exception:
            pass
        return ""

    def _get_app_setting(self, app, key, default_val):
        if not app: return default_val
        import os, configobj, globalVars
        settings_dir = os.path.join(globalVars.appArgs.configPath, "YATA", "settings")
        filepath = os.path.join(settings_dir, f"{app}.ini")
        if os.path.exists(filepath):
            try:
                conf = configobj.ConfigObj(filepath)
                if key in conf:
                    return conf[key]
            except Exception:
                pass
        return default_val

    def _get_auto_translate_state(self, app):
        if app in getattr(self, 'auto_translate_apps', {}):
            return self.auto_translate_apps[app]
        val = self._get_app_setting(app, "auto_translate", None)
        if val is not None:
            return str(val).lower() == 'true'
        return getattr(self, 'auto_translate', False)

    def get_engine(self, conf_dict=None):
        if conf_dict is None:
            conf_dict = config.conf["YATA"].copy()
        service = conf_dict["service"]
        conf = conf_dict
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

        app = self._get_app_name()

        conf = config.conf["YATA"]
        target_lang = self._get_app_setting(app, "target_lang", conf["target_lang"])
        source_lang = self._get_app_setting(app, "source_lang", conf["source_lang"])
        service = conf["service"]
        stream_ollama = conf.get(f"{service}_stream", True) and service in ("ollama", "openai", "gemini")
        separate_numbers = str(self._get_app_setting(app, "separate_numbers", conf.get("separate_numbers", False))).lower() == 'true'
        
        cached = cache.get_translation(app, target_lang, text)
        
        request_cancel_event = threading.Event()
        self._translation_cancel_events.add(request_cancel_event)

        def speak_chunk(chunk):
            def do_speak():
                if request_cancel_event.is_set(): return
                self.speaking_translation = True
                try:
                    nvda_ui.message(chunk)
                finally:
                    self.speaking_translation = False
            queueHandler.queueFunction(queueHandler.eventQueue, do_speak)

        def get_engine_with_prompts():
            conf_copy = conf.copy()
            system_prompt = self._get_app_setting(app, "system_prompt", conf.get(f"{service}_system_prompt", ""))
            user_prompt = self._get_app_setting(app, "user_prompt", conf.get(f"{service}_user_prompt", ""))
            conf_copy[f"{service}_system_prompt"] = system_prompt
            conf_copy[f"{service}_user_prompt"] = user_prompt
            return self.get_engine(conf_copy)

        def do_translate():
            try:
                engine = get_engine_with_prompts()
                
                # Helper to translate a single string without streaming, ignoring speak
                def translate_single(s):
                    res = engine.translate(s, source_lang, target_lang, stream=False)
                    return res if isinstance(res, str) else "".join(res)
                
                def process_regex_template(template, matches):
                    import string
                    formatter = string.Formatter()
                    final_parts = []
                    for literal_text, field_name, format_spec, conversion in formatter.parse(template):
                        if request_cancel_event.is_set(): return ""
                        if literal_text:
                            final_parts.append(literal_text)
                        if field_name is not None:
                            try:
                                idx = int(field_name[1:]) - 1
                                if 0 <= idx < len(matches):
                                    val = matches[idx]
                                    if field_name.startswith('T'):
                                        # Translate it
                                        val = translate_single(val)
                                    final_parts.append(val)
                            except Exception:
                                pass
                    return "".join(final_parts)
                
                if cached:
                    if cached.get("is_regexp"):
                        final_text = process_regex_template(cached["template"], cached["matches"])
                    else:
                        final_text = cached["template"]
                        
                    if request_cancel_event.is_set(): return
                    if speak: speak_chunk(final_text)
                    if browseable: queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, final_text, "YATA Translation")
                    if copy: api.copyToClip(final_text)
                    return

                # Automatic Number Separation Pre-Processing
                import re
                parts = []
                if separate_numbers:
                    parts = re.split(r'([\d/]+)', text)
                
                if separate_numbers and len(parts) > 1:
                    # We have numbers. Build tokenized string
                    tokenized_str = ""
                    regex_source = "^"
                    match_idx = 1
                    for part in parts:
                        if re.match(r'^[\d/]+$', part):
                            tokenized_str += f"<token{match_idx}>"
                            regex_source += r"([\d/]+)"
                            match_idx += 1
                        else:
                            tokenized_str += part
                            regex_source += re.escape(part)
                    regex_source += "$"
                    
                    # Translate the tokenized string
                    res = engine.translate(tokenized_str, source_lang, target_lang, stream=False)
                    res_str = res if isinstance(res, str) else "".join(res)
                    if request_cancel_event.is_set(): return
                    
                    # Replace <tokenX> with {PX}
                    template = res_str
                    for i in range(1, match_idx):
                        template = template.replace(f"<token{i}>", f"{{P{i}}}")
                        
                    # Save to cache
                    cache.set_translation(app, target_lang, regex_source, template, is_regexp=True)
                    
                    # Now process it like a normal regex hit
                    match = re.search(regex_source, text)
                    if match:
                        final_text = process_regex_template(template, match.groups())
                        if request_cancel_event.is_set(): return
                        if speak: speak_chunk(final_text)
                        if browseable: queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, final_text, "YATA Translation")
                        if copy: api.copyToClip(final_text)
                        return

                # Normal translation
                res = engine.translate(text, source_lang, target_lang, stream=stream_ollama)
                if isinstance(res, str):
                    if request_cancel_event.is_set(): return
                    cache.set_translation(app, target_lang, text, res, is_regexp=False)
                    if speak: speak_chunk(res)
                    if browseable: queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, res, "YATA Translation")
                    if copy: api.copyToClip(res)
                else:
                    full_text = []
                    sentence_buffer = []
                    
                    def emit_buffer():
                        if sentence_buffer:
                            msg = "".join(sentence_buffer).strip()
                            if msg:
                                speak_chunk(msg)
                            sentence_buffer.clear()

                    for chunk in res:
                        if request_cancel_event.is_set():
                            try: res.close()
                            except: pass
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
                        cache.set_translation(app, target_lang, text, final_text, is_regexp=False)
                        if browseable: queueHandler.queueFunction(queueHandler.eventQueue, nvda_ui.browseableMessage, final_text, "YATA Translation")
                        if copy: api.copyToClip(final_text)

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
            app = self._get_app_name()
            if self._get_auto_translate_state(app):
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
        app = self._get_app_name()
        current_state = self._get_auto_translate_state(app)
        new_state = not current_state
        if new_state:
            nvda_ui.message(f"Auto translate on for {app}")
            self.auto_translate_apps[app] = new_state
        else:
            self.auto_translate_apps[app] = new_state
            nvda_ui.message(f"Auto translate off for {app}")

    @scriptHandler.script(description="Open application settings")
    def script_appSettings(self, gesture):
        app = self._get_app_name()
        if not app:
            nvda_ui.message("No application active")
            return
        
        import wx
        def show_dialog():
            import core
            from .ui import YATAAppDialog
            import gui
            gui.mainFrame.prePopup()
            dlg = YATAAppDialog(gui.mainFrame, app)
            dlg.Show()
            gui.mainFrame.postPopup()
            
        wx.CallAfter(show_dialog)

    @scriptHandler.script(description="Open cache editor")
    def script_cacheEditor(self, gesture):
        app = self._get_app_name()
        
        import config
        conf = config.conf["YATA"]
        target_lang = self._get_app_setting(app, "target_lang", conf["target_lang"])

        import wx
        def show_dialog():
            import core
            from .ui import CacheEditorDialog
            import gui
            gui.mainFrame.prePopup()
            dlg = CacheEditorDialog(gui.mainFrame, app, target_lang)
            dlg.Show()
            gui.mainFrame.postPopup()
            
        wx.CallAfter(show_dialog)

    _layer_commands = [
        ("s", "translateSelection", "Translate selection"),
        ("shift+s", "translateSelectionBrowseable", "Translate selection in browseable message"),
        ("t", "translateLast", "Translate last spoken phrase"),
        ("shift+t", "translateLastBrowseable", "Translate last spoken phrase in browseable message"),
        ("c", "translateClipboard", "Translate clipboard"),
        ("shift+c", "translateClipboardBrowseable", "Translate clipboard in browseable message"),
        ("a", "toggleAuto", "Toggle auto translate"),
        ("o", "appSettings", "Open application settings"),
        ("e", "cacheEditor", "Open cache editor"),
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
        "kb:o": "appSettings",
        "kb:e": "cacheEditor",
        "kb:tab": "layerNext",
        "kb:shift+tab": "layerPrev",
        "kb:enter": "layerExecute"
    }
    
    __gestures = {
        "kb:NVDA+shift+t": "layer"
    }
