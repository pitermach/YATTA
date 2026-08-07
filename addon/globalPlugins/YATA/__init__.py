import config
import ui as nvda_ui
import threading
import addonHandler
import os
import re
import time
import tones
import string
import textInfos
import wx
import core
import gui
import queue
import configobj
import globalVars
from .ui import YATTAAppDialog, CacheEditorDialog

addonHandler.initTranslation()
import globalPluginHandler
import scriptHandler
import api
import speech
import queueHandler
import logHandler
from . import ui
from .services.google import GoogleTranslate
from .services.bing import BingTranslate
from .services.deepl import DeepLTranslate
from .services.ollama import OllamaTranslate
from .services.openai import OpenAITranslate
from .services.gemini import GeminiTranslate
from .speech_filter import (
    SmartSpeechFilter,
    extract_translatable_text,
    reconstruct_speech_sequence,
)


NUM_REGEX = re.compile(r'(-?\d+(?:[.,/]\d+)*)')
TOKEN_REGEX = re.compile(r"<token\d+>")
SENTENCE_BREAKS_RE = re.compile(r'[.,!?;:\n،؛؟　-〿︐-︰！-｠]')

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
    "ollama_model": "string(default='translategemma:4b')",
    "ollama_system_prompt": "string(default='')",
    "ollama_user_prompt": "string(default='You are a professional {SOURCE_LANG} ({SOURCE_CODE}) to {TARGET_LANG} ({TARGET_CODE}) translator. Your goal is to accurately convey the meaning and nuances of the original {SOURCE_LANG} text while adhering to {TARGET_LANG} grammar, vocabulary, and cultural sensitivities.\nProduce only the {TARGET_LANG} translation, without any additional explanations or commentary. The text may contain placeholders like <token0>, it is essential they are reproduced exactly in the translation if they appear in the source text. Please translate the following {SOURCE_LANG} text into {TARGET_LANG}:\n\n{TEXT}')",
    "ollama_stream": "boolean(default=True)",
    "openai_key": "string(default='')",
    "openai_address": "string(default='https://api.openai.com/v1')",
    "openai_model": "string(default='gpt-5.4-mini')",
    "openai_system_prompt": "string(default='You are an expert translator. Translate the given text to the target language.')",
    "openai_user_prompt": "string(default='{TEXT}')",
    "openai_stream": "boolean(default=True)",
    "gemini_key": "string(default='')",
    "gemini_model": "string(default='gemini-3.5-flash')",
    "gemini_system_prompt": "string(default='You are an expert translator. Translate the given text to the target language.')",
    "gemini_user_prompt": "string(default='{TEXT}')",
    "gemini_stream": "boolean(default=True)",
    "save_cache": "boolean(default=True)",
    "separate_numbers": "boolean(default=False)",
    "filter_nvda_messages": "boolean(default=True)",
    "play_sound": "boolean(default=True)",
    "auto_swap": "boolean(default=False)"
}
config.conf.spec["YATTA"] = confspec

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = "YATTA"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toggling = False
        cache.init()
        self.auto_translate = False
        self.auto_translate_apps = {}
        gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(ui.YATTASettingsPanel)
        
        self.speaking_translation = False
        self._original_speak = speechModule.speak
        speechModule.speak = self._hook_speak
        self._smart_speech_filter = SmartSpeechFilter(speech, speechModule)
        self._smart_speech_filter.register()

        self._translation_cancel_events = set()
        
        self._trigger_translation_cancel_func = self._trigger_translation_cancel

        self._trigger_translation_cancel_func = self._trigger_translation_cancel

        try:
            speechModule.speechCanceled.register(self._hook_cancelSpeech)
            logHandler.log.debug("YATTA: Registered speech.speechCanceled extension point")
        except Exception as e:
            logHandler.log.warning(f"YATTA: Failed to register speech.speechCanceled: {e}")
            
        self.last_spoken_text = ""
        
        self._translation_queue = queue.Queue()
        self._translation_worker_thread = threading.Thread(target=self._translation_worker, daemon=True)
        self._translation_worker_thread.start()

    def _translation_worker(self):
        while True:
            job = self._translation_queue.get()
            if job is None:
                break
            try:
                job()
            except Exception as e:
                logHandler.log.error(f"YATTA: Background translation failed: {e}")
            finally:
                self._translation_queue.task_done()

    def terminate(self):
        cache.save()
        try:
            gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(ui.YATTASettingsPanel)
        except Exception:
            pass
        self._smart_speech_filter.unregister()
        speechModule.speak = self._original_speak
        
        try:
            speechModule.speechCanceled.unregister(self._hook_cancelSpeech)
        except Exception as e:
            logHandler.log.warning(f"YATTA: Failed to unregister speech.speechCanceled: {e}")

    def _get_app_name(self):
        try:
            obj = globalVars.focusObject
            if obj and obj.appModule:
                return obj.appModule.appName
        except Exception:
            pass
        return ""

    def _get_app_setting(self, app, key, default_val):
        if not app: return default_val
        settings_dir = os.path.join(globalVars.appArgs.configPath, "YATTA", "settings")
        filepath = os.path.join(settings_dir, f"{app}.ini")
        if os.path.exists(filepath):
            try:
                conf = configobj.ConfigObj(filepath)
                if key in conf:
                    return conf[key]
            except Exception:
                pass
        return default_val

    def _get_play_sound_state(self, app):
        conf = config.conf["YATTA"]
        if not app:
            return conf.get("play_sound", True)
        
        filepath = os.path.join(globalVars.appArgs.configPath, "YATTA", "settings", f"{app}.ini")
        if os.path.exists(filepath):
            app_conf = configobj.ConfigObj(filepath)
            if "play_sound" in app_conf:
                return app_conf["play_sound"].lower() == 'true'
        return conf.get("play_sound", True)

    def _get_auto_translate_state(self, app):
        if app in getattr(self, 'auto_translate_apps', {}):
            return self.auto_translate_apps[app]
        val = self._get_app_setting(app, "auto_translate", None)
        if val is not None:
            return str(val).lower() == 'true'
        return getattr(self, 'auto_translate', False)

    def get_engine(self, conf_dict=None):
        if conf_dict is None:
            conf_dict = config.conf["YATTA"].copy()
        service = conf_dict["service"]
        conf = conf_dict
        if service == "bing":
            return BingTranslate(conf.copy())
        elif service == "deepl":
            return DeepLTranslate(conf.copy())
        elif service == "ollama":
            return OllamaTranslate(conf.copy())
        elif service == "openai":
            return OpenAITranslate(conf.copy())
        elif service == "gemini":
            return GeminiTranslate(conf.copy())
        else:
            return GoogleTranslate(conf.copy())

    def translate_text(self, text, speak=True, browseable=False, on_complete=None):
        if not text or not text.strip():
            return False
            
        stripped = text.strip()
        if len(stripped) <= 1:
            return False
        if NUM_REGEX.fullmatch(stripped):
            return False

        if browseable:
            self.is_long_operation = True

        app = self._get_app_name()

        conf = config.conf["YATTA"]
        target_lang = self._get_app_setting(app, "target_lang", conf["target_lang"])
        source_lang = self._get_app_setting(app, "source_lang", conf["source_lang"])
        auto_swap = str(self._get_app_setting(app, "auto_swap", conf.get("auto_swap", False))).lower() == 'true'
        service = conf["service"]
        stream_ollama = conf.get(f"{service}_stream", True) and service in ("ollama", "openai", "gemini")
        separate_numbers = str(self._get_app_setting(app, "separate_numbers", conf.get("separate_numbers", False))).lower() == 'true'
        
        cached = cache.get_translation(app, target_lang, text)
        
        last_activity_time = [time.time()]
        translation_done = [False]
        request_cancel_event = threading.Event()
        self._translation_cancel_events.add(request_cancel_event)

        def speak_chunk(chunk):
            last_activity_time[0] = time.time()
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

        def split_into_chunks(text, max_chars):
            import re
            pattern = r'([.,!?;:\n،؛؟　-〿︐-︰！-｠]+)'
            parts = re.split(pattern, text)
            
            chunks = []
            current_chunk = ""
            
            for i in range(0, len(parts), 2):
                chunk_part = parts[i]
                delim = parts[i+1] if i + 1 < len(parts) else ""
                
                piece = chunk_part + delim
                
                if len(current_chunk) + len(piece) <= max_chars:
                    current_chunk += piece
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    if len(piece) > max_chars:
                        for j in range(0, len(piece), max_chars):
                            sub_piece = piece[j:j+max_chars]
                            if len(sub_piece) == max_chars:
                                chunks.append(sub_piece)
                                current_chunk = ""
                            else:
                                current_chunk = sub_piece
                    else:
                        current_chunk = piece
                        
            if current_chunk:
                chunks.append(current_chunk)
                
            return chunks

        def do_translate():
            def beep_loop():
                while not translation_done[0] and not request_cancel_event.is_set():
                    if time.time() - last_activity_time[0] >= 2.0:
                        tones.beep(2000, 10)
                        last_activity_time[0] = time.time()
                    time.sleep(0.1)

            if self._get_play_sound_state(app):
                threading.Thread(target=beep_loop, daemon=True).start()

            try:
                lang_state = [source_lang, target_lang]
                engine = get_engine_with_prompts()
                
                def translate_single(s):
                    cached_s = cache.get_translation(app, lang_state[1], s)
                    if cached_s:
                        if cached_s.get("is_regexp"):
                            return process_regex_template(cached_s["template"], cached_s["matches"])
                        return cached_s["template"]
                        
                    res = engine.translate(s, lang_state[0], lang_state[1], stream=False)
                    res_str = res if isinstance(res, str) else "".join(res)
                    res_str = TOKEN_REGEX.sub("", res_str)
                    cache.set_translation(app, lang_state[1], s, res_str, is_regexp=False)
                    return res_str
                
                def process_regex_template(template, matches):
                    import re
                    parts = re.split(r'({[PT]\d+})', template)
                    final_parts = []
                    for part in parts:
                        if request_cancel_event.is_set(): return ""
                        m = re.fullmatch(r'{([PT])(\d+)}', part)
                        if m:
                            prefix = m.group(1)
                            try:
                                idx = int(m.group(2)) - 1
                                if 0 <= idx < len(matches):
                                    val = matches[idx]
                                    if prefix == 'T':
                                        val = translate_single(val)
                                    final_parts.append(val)
                                else:
                                    final_parts.append(part)
                            except Exception:
                                final_parts.append(part)
                        else:
                            final_parts.append(part)
                    return "".join(final_parts)
                
                def process_text_chunk(text_chunk):
                    cached = cache.get_translation(app, lang_state[1], text_chunk)
                    if cached:
                        if cached.get("is_regexp"):
                            final_text = process_regex_template(cached["template"], cached["matches"])
                        else:
                            final_text = cached["template"]
                            
                        if request_cancel_event.is_set(): return "" ""
                        if speak: speak_chunk(final_text)
                        # browseable moved to end
                        return final_text

                    # Automatic Number Separation Pre-Processing
                    parts = []
                    if separate_numbers:
                        parts = NUM_REGEX.split(text_chunk)
                    
                    if separate_numbers and len(parts) > 1:
                        # We have numbers. Build tokenized string
                        tokenized_str = ""
                        regex_source = "^"
                        match_idx = 1
                        for part in parts:
                            if NUM_REGEX.fullmatch(part):
                                tokenized_str += f"<token{match_idx}>"
                                regex_source += r"(-?\d+(?:[.,/]\d+)*)"
                                match_idx += 1
                            else:
                                tokenized_str += part
                                regex_source += re.escape(part).replace(r"\ ", " ")
                        regex_source += "$"
                        
                        # Translate the tokenized string
                        actual_source = "auto" if (auto_swap and getattr(engine, 'supports_language_detection', False)) else lang_state[0]
                        res = engine.translate(tokenized_str, actual_source, lang_state[1], stream=False)
                        if auto_swap and lang_state[0] != "auto" and getattr(engine, 'supports_language_detection', False):
                            detected = getattr(engine, 'last_detected_language', None)
                            if detected:
                                det_base = detected.split('-')[0].lower()
                                tgt_base = lang_state[1].split('-')[0].lower()
                                if det_base == tgt_base:
                                    lang_state[0], lang_state[1] = lang_state[1], lang_state[0]
                                    res = engine.translate(tokenized_str, lang_state[0], lang_state[1], stream=False)

                        res_str = res if isinstance(res, str) else "".join(res)
                        if request_cancel_event.is_set(): return "" ""
                        
                        # Replace <tokenX> with {PX}
                        template = res_str
                        missing_values_indices = []
                        for i in range(1, match_idx):
                            if f"<token{i}>" not in template:
                                missing_values_indices.append(i - 1)
                            template = template.replace(f"<token{i}>", f"{{P{i}}}")
                            
                        # Save to cache if no unused values
                        if not missing_values_indices:
                            cache.set_translation(app, lang_state[1], regex_source, template, is_regexp=True)
                        
                        # Now process it like a normal regex hit
                        match = re.search(regex_source, text_chunk)
                        if match:
                            final_text = process_regex_template(template, match.groups())
                            if request_cancel_event.is_set(): return ""
                            if speak: speak_chunk(final_text)
                            # browseable moved to end
                            if missing_values_indices and speak:
                                tones.beep(1500, 50)
                                missing_strs = [match.groups()[idx] for idx in missing_values_indices]
                                speak_chunk(_("Warning, unused values: ") + ", ".join(missing_strs))
                            return final_text

                    # Normal translation
                    actual_source = "auto" if (auto_swap and getattr(engine, 'supports_language_detection', False)) else lang_state[0]
                    res = engine.translate(text_chunk, actual_source, lang_state[1], stream=stream_ollama)
                    if auto_swap and lang_state[0] != "auto" and getattr(engine, 'supports_language_detection', False):
                        detected = getattr(engine, 'last_detected_language', None)
                        if detected:
                            det_base = detected.split('-')[0].lower()
                            tgt_base = lang_state[1].split('-')[0].lower()
                            if det_base == tgt_base:
                                # Swap languages and re-run
                                lang_state[0], lang_state[1] = lang_state[1], lang_state[0]
                                res = engine.translate(text_chunk, lang_state[0], lang_state[1], stream=stream_ollama)

                    if isinstance(res, str):
                        res = TOKEN_REGEX.sub("", res)
                        if request_cancel_event.is_set(): return ""
                        cache.set_translation(app, lang_state[1], text_chunk, res, is_regexp=False)
                        if speak: speak_chunk(res)
                        return res
                    else:
                        full_text = []
                        sentence_buffer = []
                        
                        def emit_buffer():
                            if sentence_buffer:
                                msg = "".join(sentence_buffer).strip()
                                msg = TOKEN_REGEX.sub("", msg)
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
                                if SENTENCE_BREAKS_RE.search(chunk):
                                    emit_buffer()
                        
                        if speak:
                            emit_buffer()
                        
                        final_text = "".join(full_text)
                        final_text = TOKEN_REGEX.sub("", final_text)
                        if not request_cancel_event.is_set():
                            cache.set_translation(app, lang_state[1], text_chunk, final_text, is_regexp=False)
                            return final_text

                # Chunk and process
                if len(text) > getattr(engine, 'max_chars', 4000):
                    chunks = split_into_chunks(text, getattr(engine, 'max_chars', 4000))
                else:
                    chunks = [text]
                    
                is_first = True
                full_translated_text = []
                for c in chunks:
                    if request_cancel_event.is_set(): break
                    if not is_first and getattr(engine, 'requires_sleep', True):
                        for _delay_idx in range(10):
                            if request_cancel_event.is_set(): break
                            time.sleep(0.1)
                    if request_cancel_event.is_set(): break
                    
                    chunk_res = process_text_chunk(c)
                    if chunk_res:
                        full_translated_text.append(chunk_res)
                    is_first = False

                if full_translated_text:
                    combined_text = "".join(full_translated_text)
                    if on_complete:
                        queueHandler.queueFunction(
                            queueHandler.eventQueue, on_complete, combined_text
                        )
                    if browseable:
                        queueHandler.queueFunction(
                            queueHandler.eventQueue,
                            nvda_ui.browseableMessage,
                            combined_text,
                            "YATTA Translation",
                        )

            except Exception as e:
                if not request_cancel_event.is_set():
                    queueHandler.queueFunction(queueHandler.eventQueue, speak_chunk, f"Error: {e}")
            finally:
                translation_done[0] = True
                self._translation_cancel_events.discard(request_cancel_event)
                if browseable:
                    self.is_long_operation = False

        self._translation_queue.put(do_translate)
        return True

    def _hook_speak(self, speechSequence, *args, **kwargs):
        filter_enabled = config.conf["YATTA"].get("filter_nvda_messages", True)
        if self.speaking_translation or (
            filter_enabled and self._smart_speech_filter.is_suppressed
        ):
            self._original_speak(speechSequence, *args, **kwargs)
            return

        text, translatable_indices = extract_translatable_text(
            speechSequence, enabled=filter_enabled
        )
        if text:
            self.last_spoken_text = text
            app = self._get_app_name()
            if self._get_auto_translate_state(app):
                original_sequence = list(speechSequence)

                def speak_reconstructed(translation):
                    reconstructed = reconstruct_speech_sequence(
                        original_sequence, translatable_indices, translation
                    )
                    self.speaking_translation = True
                    try:
                        self._original_speak(reconstructed, *args, **kwargs)
                    finally:
                        self.speaking_translation = False

                if self.translate_text(
                    text, speak=False, on_complete=speak_reconstructed
                ):
                    return
        self._original_speak(speechSequence, *args, **kwargs)

    def _trigger_translation_cancel(self):
        logHandler.log.debug("YATTA: _trigger_translation_cancel called")
        for ev in list(self._translation_cancel_events):
            ev.set()
        self._translation_cancel_events.clear()

    def _hook_cancelSpeech(self, *args, **kwargs):
        logHandler.log.debug("YATTA: _hook_cancelSpeech triggered")
        if getattr(self, 'is_long_operation', False):
            return
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
        
    @scriptHandler.script(description=_("Translation Layer (Press S, T, C, or A)"))
    def script_layer(self, gesture):
        if self.toggling:
            tones.beep(120, 100)
            return
        self.bindGestures(self.__layerGestures)
        self.toggling = True
        self._layer_index = -1
        tones.beep(200, 10)
        
    @scriptHandler.script(description=_("Translate selection"))
    def script_translateSelection(self, gesture):
        obj = api.getCaretObject()
        try:
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and not info.isCollapsed:
                text = info.text
                self.translate_text(text, speak=True)
            else:
                nvda_ui.message(_("No selection"))
        except Exception:
            nvda_ui.message(_("No selection"))

    @scriptHandler.script(description=_("Translate selection in browseable message"))
    def script_translateSelectionBrowseable(self, gesture):
        obj = api.getCaretObject()
        try:
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            if info and not info.isCollapsed:
                text = info.text
                self.translate_text(text, speak=False, browseable=True)
            else:
                nvda_ui.message(_("No selection"))
        except Exception:
            nvda_ui.message(_("No selection"))

    @scriptHandler.script(description=_("Translate last spoken phrase"))
    def script_translateLast(self, gesture):
        if self.last_spoken_text:
            self.translate_text(self.last_spoken_text, speak=True)
        else:
            nvda_ui.message(_("No last phrase found"))

    @scriptHandler.script(description=_("Translate last spoken phrase in browseable message"))
    def script_translateLastBrowseable(self, gesture):
        if self.last_spoken_text:
            self.translate_text(self.last_spoken_text, speak=False, browseable=True)
        else:
            nvda_ui.message(_("No last phrase found"))

    @scriptHandler.script(description=_("Translate clipboard"))
    def script_translateClipboard(self, gesture):
        text = api.getClipData()
        if text and isinstance(text, str) and not text.isspace():
            self.translate_text(text, speak=True)
        else:
            nvda_ui.message(_("No text on clipboard"))

    @scriptHandler.script(description=_("Translate clipboard in browseable message"))
    def script_translateClipboardBrowseable(self, gesture):
        text = api.getClipData()
        if text and isinstance(text, str) and not text.isspace():
            self.translate_text(text, speak=False, browseable=True)
        else:
            nvda_ui.message(_("No text on clipboard"))

    @scriptHandler.script(description=_("Toggle auto translate"))
    def script_toggleAuto(self, gesture):
        app = self._get_app_name()
        current_state = self._get_auto_translate_state(app)
        new_state = not current_state
        if new_state:
            nvda_ui.message(_("Auto translate on for {app}").format(app=app))
            self.auto_translate_apps[app] = new_state
        else:
            self.auto_translate_apps[app] = new_state
            nvda_ui.message(_("Auto translate off for {app}").format(app=app))

    @scriptHandler.script(description=_("Open application settings"))
    def script_appSettings(self, gesture):
        app = self._get_app_name()
        if not app:
            nvda_ui.message(_("No application active"))
            return
        
        def show_dialog():
            gui.mainFrame.prePopup()
            dlg = YATTAAppDialog(gui.mainFrame, app)
            dlg.Show()
            gui.mainFrame.postPopup()
            
        wx.CallAfter(show_dialog)

    @scriptHandler.script(description=_("Open cache editor"))
    def script_cacheEditor(self, gesture):
        app = self._get_app_name()
        
        conf = config.conf["YATTA"]
        target_lang = self._get_app_setting(app, "target_lang", conf["target_lang"])

        def show_dialog():
            gui.mainFrame.prePopup()
            dlg = CacheEditorDialog(gui.mainFrame, app, target_lang)
            dlg.Show()
            gui.mainFrame.postPopup()
            
        wx.CallAfter(show_dialog)


    @scriptHandler.script(description=_("Swap source and target languages"))
    def script_swapLanguages(self, gesture):
        app = self._get_app_name()
        
        conf = config.conf["YATTA"]
        target_lang = self._get_app_setting(app, "target_lang", conf["target_lang"])
        source_lang = self._get_app_setting(app, "source_lang", conf["source_lang"])
        
        if source_lang == "auto":
            nvda_ui.message(_("Unable to swap from auto detect!"))
            return
            
        new_source = target_lang
        new_target = source_lang
        
        # Check if app-specific settings exist
        if app:
            settings_dir = os.path.join(globalVars.appArgs.configPath, "YATTA", "settings")
            app_filepath = os.path.join(settings_dir, f"{app}.ini")
            if os.path.exists(app_filepath):
                try:
                    import configobj
                    app_conf = configobj.ConfigObj(app_filepath)
                    app_conf["source_lang"] = new_source
                    app_conf["target_lang"] = new_target
                    app_conf.write()
                    nvda_ui.message(_("Translating from {src} to {tgt} in {app}").format(src=new_source, tgt=new_target, app=app))
                    return
                except Exception as e:
                    logHandler.log.error(f"YATTA: failed to swap languages for app {app}: {e}")
        
        # Fallback to global config
        conf["source_lang"] = new_source
        conf["target_lang"] = new_target
        nvda_ui.message(_("Translating from {src} to {tgt}").format(src=new_source, tgt=new_target))

    _layer_commands = [
        ("s", "translateSelection", _("Translate selection")),
        ("shift+s", "translateSelectionBrowseable", _("Translate selection in browseable message")),
        ("t", "translateLast", _("Translate last spoken phrase")),
        ("shift+t", "translateLastBrowseable", _("Translate last spoken phrase in browseable message")),
        ("c", "translateClipboard", _("Translate clipboard")),
        ("shift+c", "translateClipboardBrowseable", _("Translate clipboard in browseable message")),
        ("a", "toggleAuto", _("Toggle auto translate")),
        ("o", "appSettings", _("Open application settings")),
        ("e", "cacheEditor", _("Open cache editor")),
        ("w", "swapLanguages", _("Swap source and target languages")),
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
        "kb:w": "swapLanguages",
        "kb:tab": "layerNext",
        "kb:shift+tab": "layerPrev",
        "kb:enter": "layerExecute"
    }
    
    __gestures = {
        "kb:NVDA+shift+t": "layer"
    }
