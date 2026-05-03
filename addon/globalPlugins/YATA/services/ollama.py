import urllib.request
import urllib.parse
import json
from . import TranslationEngine

class OllamaTranslate(TranslationEngine):
    name = "Ollama"

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
            yield f"Ollama Translate error: {str(e)}"

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False):
        address = self.config.get("ollama_address", "http://localhost:11434").rstrip("/")
        model = self.config.get("ollama_model", "gemma:2b")
        system_prompt = self.config.get("ollama_system_prompt", "You are an expert translator. Translate the given text to the target language.")
        
        full_system_prompt = f"{system_prompt}\nTarget language: {target_lang}"
        if source_lang and source_lang != "auto":
            full_system_prompt += f"\nSource language: {source_lang}"
            
        url = f"{address}/api/generate"
        data = {
            "model": model,
            "system": full_system_prompt,
            "prompt": text,
            "stream": stream
        }
        
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
