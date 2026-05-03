import urllib.request
import urllib.parse
import json
import base64
from datetime import datetime
from . import TranslationEngine

class BingTranslate(TranslationEngine):
    name = "Bing Translate (Free Edge)"
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.endpoint = 'https://api-edge.cognitive.microsofttranslator.com/translate'
        self.access_info = None

    def _parse_jwt(self, token):
        parts = token.split(".")
        if len(parts) <= 1:
            raise Exception('Invalid Token.')
        base64_url = parts[1]
        base64_url = base64_url.replace('-', '+').replace('_', '/')
        # padding
        padding = len(base64_url) % 4
        if padding > 0:
            base64_url += '=' * (4 - padding)
        json_payload = base64.b64decode(base64_url).decode('utf-8')
        parsed = json.loads(json_payload)
        expired_date = datetime.fromtimestamp(parsed['exp'])
        return {'Token': token, 'Expire': expired_date}

    def _get_app_key(self):
        if not self.access_info or datetime.now() > self.access_info['Expire']:
            auth_url = 'https://edge.microsoft.com/translate/auth'
            req = urllib.request.Request(auth_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
            })
            with urllib.request.urlopen(req) as response:
                app_key = response.read().decode('utf-8').strip()
                self.access_info = self._parse_jwt(app_key)
        return self.access_info['Token']

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        try:
            query = {
                'to': target_lang,
                'api-version': '3.0',
            }
            if source_lang and source_lang != "auto":
                query['from'] = source_lang
                
            full_url = f'{self.endpoint}?{urllib.parse.urlencode(query)}'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self._get_app_key()}',
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            body = json.dumps([{'text': text}]).encode('utf-8')
            
            req = urllib.request.Request(full_url, data=body, headers=headers)
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                translated_text = result[0]['translations'][0]['text']
                if stream:
                    return iter([translated_text])
                else:
                    return translated_text
        except Exception as e:
            raise Exception(f"Bing Translate error: {str(e)}")
