import urllib.request
import urllib.parse
import json
from . import TranslationEngine

class GeminiTranslate(TranslationEngine):
    name = "Gemini"
    has_api_key = True
    max_chars = 4000

    def get_supported_languages(self) -> dict:
        import os
        model = self.config.get("gemini_model", "")
        addon_dir = os.path.dirname(os.path.dirname(__file__))
        languages_file = os.path.join(addon_dir, "languages.json")
        try:
            with open(languages_file, "r", encoding="utf-8") as f:
                langs = json.load(f)
            return langs.get("gemini", {})
        except Exception:
            return {}

    def _read_stream(self, req):
        try:
            with urllib.request.urlopen(req) as response:
                buffer = ""
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    buffer += chunk.decode('utf-8')
                    # Gemini streams a JSON array where each object is prefixed by comma if it's not the first
                    # This is tricky to parse safely as a stream since it's just raw JSON chunks.
                    # We will accumulate and parse complete JSON objects.
                    # For a robust approach, we can just split by "}\n,\r\n{\n" or parse manually.
                    # Alternatively, Gemini returns Server-Sent Events if requested with `alt=sse`
                    pass # Handled below
        except Exception as e:
            raise Exception(f"Gemini Translate error: {str(e)}")

    def _read_sse_stream(self, req):
        try:
            with urllib.request.urlopen(req) as response:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            if 'candidates' in chunk and len(chunk['candidates']) > 0:
                                parts = chunk['candidates'][0].get('content', {}).get('parts', [])
                                if parts and 'text' in parts[0]:
                                    yield parts[0]['text']
                        except Exception:
                            pass
        except Exception as e:
            raise Exception(f"Gemini Translate error: {str(e)}")

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        api_key = self.config.get("gemini_key", "").strip()
        if not api_key:
            raise Exception("Gemini API key not configured.")
            
        model = self.config.get("gemini_model", "gemini-2.5-flash")
        system_prompt = self.config.get("gemini_system_prompt", "You are an expert translator.")
        user_prompt = self.config.get("gemini_user_prompt", "{TEXT}")
        
        langs = self.get_supported_languages()
        source_name = langs.get(source_lang, source_lang)
        target_name = langs.get(target_lang, target_lang)
        
        system_prompt = system_prompt.replace("{SOURCE_LANG}", source_name).replace("{SOURCE_CODE}", source_lang)
        system_prompt = system_prompt.replace("{TARGET_LANG}", target_name).replace("{TARGET_CODE}", target_lang)
        system_prompt = system_prompt.replace("{TEXT}", text)
        
        user_prompt = user_prompt.replace("{SOURCE_LANG}", source_name).replace("{SOURCE_CODE}", source_lang)
        user_prompt = user_prompt.replace("{TARGET_LANG}", target_name).replace("{TARGET_CODE}", target_lang)
        user_prompt = user_prompt.replace("{TEXT}", text)
        
        # Gemini API endpoint
        method = "streamGenerateContent?alt=sse&" if stream else "generateContent?"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}key={api_key}"
        
        data = {
            "contents": [{
                "parts": [{"text": user_prompt}]
            }]
        }
        if system_prompt:
            data["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }
            
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json"
        })
        
        if stream:
            return self._read_sse_stream(req)
            
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
                return ""
        except Exception as e:
            raise Exception(f"Gemini Translate error: {str(e)}")
