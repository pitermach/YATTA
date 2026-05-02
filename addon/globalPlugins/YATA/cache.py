import json
import os
import globalVars
import threading

_cache_lock = threading.RLock()
_cache = {}
_cache_file = ""

def init():
    global _cache_file, _cache
    _cache_file = os.path.join(globalVars.appArgs.configPath, "YATA_cache.json")
    if os.path.exists(_cache_file):
        try:
            with open(_cache_file, "r", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    else:
        _cache = {}

def save():
    with _cache_lock:
        try:
            with open(_cache_file, "w", encoding="utf-8") as f:
                json.dump(_cache, f, ensure_ascii=False)
        except Exception:
            pass

def get_translation(app_name: str, target_lang: str, text: str):
    """
    Look up translation in cache.
    """
    with _cache_lock:
        return _cache.get(app_name, {}).get(target_lang, {}).get(text, None)

def set_translation(app_name: str, target_lang: str, text: str, translation: str):
    with _cache_lock:
        if app_name not in _cache:
            _cache[app_name] = {}
        if target_lang not in _cache[app_name]:
            _cache[app_name][target_lang] = {}
        _cache[app_name][target_lang][text] = translation
