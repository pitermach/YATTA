import urllib.request
import urllib.parse
import json
from . import TranslationEngine

class GoogleTranslate(TranslationEngine):
    name = "Google Translate (Free)"
    supports_language_detection = True

    def get_supported_languages(self) -> dict:
        url = "https://translate.googleapis.com/translate_a/l?client=gtx"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('tl', {})
        except Exception:
            return {}

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": source_lang,
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        query_string = urllib.parse.urlencode(params).encode('utf-8')
        
        req = urllib.request.Request(url, data=query_string, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/x-www-form-urlencoded"
        })
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if len(result) > 2 and result[2]:
                    self.last_detected_language = result[2]
                translated_text = "".join([sentence[0] for sentence in result[0] if sentence[0]])
                if stream:
                    return iter([translated_text])
                else:
                    return translated_text
        except Exception as e:
            raise Exception(f"Google Translate error: {str(e)}")
