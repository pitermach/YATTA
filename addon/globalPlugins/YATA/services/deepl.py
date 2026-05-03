import urllib.request
import urllib.parse
import json
from . import TranslationEngine

class DeepLTranslate(TranslationEngine):
    name = "DeepL"
    has_api_key = True

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            raise Exception("DeepL API key not configured.")
            
        is_free_api = api_key.endswith(":fx")
        if is_free_api:
            url = "https://api-free.deepl.com/v2/translate"
        else:
            url = "https://api.deepl.com/v2/translate"
            
        data = {
            "text": [text],
            "target_lang": target_lang.upper()
        }
        
        if source_lang and source_lang != "auto":
            data["source_lang"] = source_lang.upper()
            
        body = json.dumps(data).encode('utf-8')
        headers = {
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/json"
        }
        
        req = urllib.request.Request(url, data=body, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                translated_text = result["translations"][0]["text"]
                if stream:
                    return iter([translated_text])
                else:
                    return translated_text
        except Exception as e:
            raise Exception(f"DeepL Translate error: {str(e)}")
