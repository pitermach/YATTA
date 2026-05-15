import urllib.request
import urllib.parse
import json
from . import TranslationEngine

class OpenAITranslate(TranslationEngine):
    name = "OpenAI"
    has_api_key = True

    def get_supported_languages(self) -> dict:
        import os
        model = self.config.get("openai_model", "")
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        languages_file = os.path.join(addon_dir, "languages.json")
        try:
            with open(languages_file, "r", encoding="utf-8") as f:
                langs = json.load(f)
            return langs.get("gpt", {})
        except Exception:
            return {}

    def _read_stream(self, req):
        try:
            with urllib.request.urlopen(req) as response:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0]['delta']
                            if 'content' in delta:
                                yield delta['content']
                        except Exception:
                            pass
        except Exception as e:
            raise Exception(f"OpenAI Translate error: {str(e)}")

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        api_key = self.config.get("openai_key", "").strip()
        if not api_key:
            raise Exception("OpenAI API key not configured.")
            
        address = self.config.get("openai_address", "https://api.openai.com/v1").rstrip("/")
        model = self.config.get("openai_model", "gpt-5.4-mini")
        system_prompt = self.config.get("openai_system_prompt", "You are an expert translator.")
        user_prompt = self.config.get("openai_user_prompt", "{TEXT}")
        
        langs = self.get_supported_languages()
        source_name = langs.get(source_lang, source_lang)
        target_name = langs.get(target_lang, target_lang)
        
        system_prompt = system_prompt.replace("{SOURCE_LANG}", source_name).replace("{SOURCE_CODE}", source_lang)
        system_prompt = system_prompt.replace("{TARGET_LANG}", target_name).replace("{TARGET_CODE}", target_lang)
        system_prompt = system_prompt.replace("{TEXT}", text)
        
        user_prompt = user_prompt.replace("{SOURCE_LANG}", source_name).replace("{SOURCE_CODE}", source_lang)
        user_prompt = user_prompt.replace("{TARGET_LANG}", target_name).replace("{TARGET_CODE}", target_lang)
        user_prompt = user_prompt.replace("{TEXT}", text)
        
        url = f"{address}/chat/completions"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})
        
        data = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        })
        
        if stream:
            return self._read_stream(req)
            
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except Exception as e:
            raise Exception(f"OpenAI Translate error: {str(e)}")
