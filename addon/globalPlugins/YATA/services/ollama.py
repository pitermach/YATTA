import urllib.request
import urllib.parse
import json
from . import TranslationEngine

class OllamaTranslate(TranslationEngine):
    name = "Ollama"
    has_api_key = False
    max_chars = 4000
    requires_sleep = False

    def _read_stream(self, req):
        try:
            with urllib.request.urlopen(req) as response:
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
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '')
        except Exception as e:
            raise Exception(f"Ollama Translate error: {str(e)}")
