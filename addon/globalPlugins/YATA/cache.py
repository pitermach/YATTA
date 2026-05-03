import json
import os
import globalVars
import threading

_cache_lock = threading.RLock()
_cache = {}
_cache_dir = ""

def init():
    global _cache_dir, _cache
    _cache_dir = os.path.join(globalVars.appArgs.configPath, "YATA_cache")
    if not os.path.exists(_cache_dir):
        try:
            os.makedirs(_cache_dir)
        except Exception:
            pass
            
    # Load all json files into memory
    if os.path.exists(_cache_dir):
        for filename in os.listdir(_cache_dir):
            if filename.endswith(".json"):
                app_name = filename[:-5]
                filepath = os.path.join(_cache_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        _cache[app_name] = json.load(f)
                except Exception:
                    pass

    # Migrate legacy cache
    legacy_file = os.path.join(globalVars.appArgs.configPath, "YATA_cache.json")
    if os.path.exists(legacy_file):
        try:
            with open(legacy_file, "r", encoding="utf-8") as f:
                legacy_cache = json.load(f)
                for app_name, data in legacy_cache.items():
                    if app_name not in _cache:
                        _cache[app_name] = data
                    else:
                        _cache[app_name].update(data)
            try:
                os.rename(legacy_file, legacy_file + ".bak")
            except Exception:
                pass
        except Exception:
            pass

def save():
    with _cache_lock:
        if not os.path.exists(_cache_dir):
            try:
                os.makedirs(_cache_dir)
            except Exception:
                return
                
        for app_name, data in _cache.items():
            filepath = os.path.join(_cache_dir, f"{app_name}.json")
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

def get_translation(app_name: str, target_lang: str, text: str):
    """
    Look up translation in cache.
    """
    if not app_name:
        app_name = "default"
    with _cache_lock:
        return _cache.get(app_name, {}).get(target_lang, {}).get(text, None)

def set_translation(app_name: str, target_lang: str, text: str, translation: str):
    if not app_name:
        app_name = "default"
    with _cache_lock:
        if app_name not in _cache:
            _cache[app_name] = {}
        if target_lang not in _cache[app_name]:
            _cache[app_name][target_lang] = {}
        _cache[app_name][target_lang][text] = translation
