import urllib.request
import urllib.parse
import json
import threading
from . import TranslationEngine

OLLAMA_REQUEST_TIMEOUT = 30
OLLAMA_STATUS_CHECK_DELAY = 1
OLLAMA_STATUS_REQUEST_TIMEOUT = 2


class OllamaTranslate(TranslationEngine):
    name = "Ollama"
    has_api_key = False
    max_chars = 4000
    requires_sleep = False

    def __init__(self, config):
        super().__init__(config)
        self.status_callback = None

    def _is_cloud_request(self, address, model):
        hostname = (urllib.parse.urlparse(address).hostname or "").lower()
        return (
            hostname == "ollama.com"
            or hostname.endswith(".ollama.com")
            or model.lower().endswith("-cloud")
        )

    def _model_is_running(self, address, model):
        req = urllib.request.Request(f"{address}/api/ps")
        with urllib.request.urlopen(
            req, timeout=OLLAMA_STATUS_REQUEST_TIMEOUT
        ) as response:
            result = json.loads(response.read().decode("utf-8"))

        selected_model = model.lower()
        if selected_model.endswith(":latest"):
            selected_model = selected_model[:-len(":latest")]

        for running_model in result.get("models", []):
            for key in ("name", "model"):
                running_name = str(running_model.get(key, "")).lower()
                if running_name.endswith(":latest"):
                    running_name = running_name[:-len(":latest")]
                if running_name == selected_model:
                    return True
        return False

    def _notify_status(self, status):
        if self.status_callback:
            try:
                self.status_callback(status)
            except Exception:
                pass

    def _open_generate_response(self, req, address, model):
        if self._is_cloud_request(address, model):
            return urllib.request.urlopen(req, timeout=OLLAMA_REQUEST_TIMEOUT)

        condition = threading.Condition()
        state = {
            "cancelled": False,
            "done": False,
            "outcome": None,
        }

        def open_request():
            try:
                outcome = (
                    True,
                    urllib.request.urlopen(req, timeout=OLLAMA_REQUEST_TIMEOUT),
                )
            except Exception as e:
                outcome = (False, e)

            close_response = None
            with condition:
                if state["cancelled"]:
                    if outcome[0]:
                        close_response = outcome[1]
                else:
                    state["outcome"] = outcome
                    state["done"] = True
                    condition.notify_all()
            if close_response is not None:
                close_response.close()

        def take_outcome(timeout=None):
            with condition:
                if not state["done"]:
                    condition.wait_for(lambda: state["done"], timeout)
                if not state["done"]:
                    return None
                outcome = state["outcome"]
                state["outcome"] = None
                return outcome

        def take_outcome_or_cancel():
            with condition:
                if state["done"]:
                    outcome = state["outcome"]
                    state["outcome"] = None
                    return outcome
                state["cancelled"] = True
                return None

        threading.Thread(target=open_request, daemon=True).start()
        outcome = take_outcome(OLLAMA_STATUS_CHECK_DELAY)

        if outcome is None:
            try:
                model_is_running = self._model_is_running(address, model)
            except Exception as status_error:
                outcome = take_outcome_or_cancel()
                if outcome is None:
                    raise Exception(
                        f"Ollama status check failed: {status_error}"
                    ) from status_error
            else:
                outcome = take_outcome(0)
                if outcome is None:
                    if not model_is_running:
                        self._notify_status("loading_model")
                    outcome = take_outcome()

        succeeded, result = outcome
        if not succeeded:
            raise result
        return result

    def _read_stream(self, req):
        try:
            address = self.config.get(
                "ollama_address", "http://localhost:11434"
            ).rstrip("/")
            model = self.config.get("ollama_model", "gemma:2b")
            with self._open_generate_response(req, address, model) as response:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    chunk = json.loads(line.decode('utf-8'))
                    if 'response' in chunk:
                        yield chunk['response']
                    if chunk.get('done', False):
                        break
        except Exception as e:
            raise Exception(f"Ollama Translate error: {str(e)}")

    def get_supported_languages(self) -> dict:
        import os
        model = self.config.get("ollama_model", "")
        if not model:
            return {}
            
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        languages_file = os.path.join(addon_dir, "languages.json")
        try:
            with open(languages_file, "r", encoding="utf-8") as f:
                langs = json.load(f)
                
            for k in langs:
                if k.lower() in model.lower():
                    return langs[k]
            return {}
        except Exception:
            return {}

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        address = self.config.get("ollama_address", "http://localhost:11434").rstrip("/")
        model = self.config.get("ollama_model", "gemma:2b")
        
        system_prompt = self.config.get("ollama_system_prompt", "You are an expert translator. Translate the given text to the target language.")
        user_prompt = self.config.get("ollama_user_prompt", "{TEXT}")
        
        langs = self.get_supported_languages()
        source_name = langs.get(source_lang, source_lang)
        target_name = langs.get(target_lang, target_lang)
        
        system_prompt = system_prompt.replace("{SOURCE_LANG}", source_name).replace("{SOURCE_CODE}", source_lang)
        system_prompt = system_prompt.replace("{TARGET_LANG}", target_name).replace("{TARGET_CODE}", target_lang)
        system_prompt = system_prompt.replace("{TEXT}", text)
        
        user_prompt = user_prompt.replace("{SOURCE_LANG}", source_name).replace("{SOURCE_CODE}", source_lang)
        user_prompt = user_prompt.replace("{TARGET_LANG}", target_name).replace("{TARGET_CODE}", target_lang)
        user_prompt = user_prompt.replace("{TEXT}", text)
        
        if not system_prompt:
            full_system_prompt = None
        else:
            full_system_prompt = system_prompt
            
        url = f"{address}/api/generate"
        data = {
            "model": model,
            "prompt": user_prompt,
            "stream": stream
        }
        if full_system_prompt is not None:
            data["system"] = full_system_prompt
        
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        
        if stream:
            return self._read_stream(req)
            
        try:
            with self._open_generate_response(req, address, model) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '')
        except Exception as e:
            raise Exception(f"Ollama Translate error: {str(e)}")
