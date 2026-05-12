import json
import os
import globalVars
import threading
import re

_cache_lock = threading.RLock()
_cache = {}
_cache_dir = ""

def init():
    global _cache_dir, _cache
    _cache_dir = os.path.join(globalVars.appArgs.configPath, "YATA", "cache")
    if not os.path.exists(_cache_dir):
        try:
            os.makedirs(_cache_dir)
        except Exception:
            pass
            
    if os.path.exists(_cache_dir):
        for filename in os.listdir(_cache_dir):
            if filename.endswith(".json"):
                app_name = filename[:-5]
                filepath = os.path.join(_cache_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            valid = True
                            for lang, entries in data.items():
                                if not isinstance(entries, list):
                                    valid = False
                                    break
                            if valid:
                                _cache[app_name] = data
                except Exception:
                    pass

def save():
    import config
    global_save = config.conf["YATA"].get("save_cache", True)
    
    def should_save(app):
        import os, configobj, globalVars
        settings_dir = os.path.join(globalVars.appArgs.configPath, "YATA", "settings")
        filepath = os.path.join(settings_dir, f"{app}.ini")
        if os.path.exists(filepath):
            try:
                conf = configobj.ConfigObj(filepath)
                if "save_cache" in conf:
                    return conf["save_cache"].lower() == 'true'
            except Exception:
                pass
        return global_save

    with _cache_lock:
        if not os.path.exists(_cache_dir):
            try:
                os.makedirs(_cache_dir)
            except Exception:
                return
                
        for app_name, data in _cache.items():
            if not should_save(app_name):
                continue
            filepath = os.path.join(_cache_dir, f"{app_name}.json")
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

def get_translation(app_name: str, target_lang: str, text: str):
    if not app_name:
        app_name = "default"
    with _cache_lock:
        app_cache = _cache.get(app_name, {})
        lang_cache = app_cache.get(target_lang, [])
        for entry in lang_cache:
            if not isinstance(entry, dict):
                continue
            if entry.get("is_regexp"):
                source = entry.get("source", "")
                try:
                    match = re.search(source, text)
                    if match:
                        return {"template": entry.get("translation", ""), "matches": match.groups(), "is_regexp": True}
                except Exception:
                    pass
            else:
                if entry.get("source") == text:
                    return {"template": entry.get("translation", ""), "is_regexp": False}
        return None

def set_translation(app_name: str, target_lang: str, source: str, translation: str, is_regexp: bool = False):
    if not app_name:
        app_name = "default"
    with _cache_lock:
        if app_name not in _cache:
            _cache[app_name] = {}
        if target_lang not in _cache[app_name]:
            _cache[app_name][target_lang] = []
        
        lang_cache = _cache[app_name][target_lang]
        for entry in lang_cache:
            if entry.get("source") == source and entry.get("is_regexp") == is_regexp:
                entry["translation"] = translation
                return
        
        lang_cache.append({
            "source": source,
            "translation": translation,
            "is_regexp": is_regexp
        })

def delete_translation(app_name: str, target_lang: str, source: str, is_regexp: bool):
    if not app_name:
        app_name = "default"
    with _cache_lock:
        app_cache = _cache.get(app_name, {})
        lang_cache = app_cache.get(target_lang, [])
        
        for i, entry in enumerate(lang_cache):
            if entry.get("source") == source and entry.get("is_regexp") == is_regexp:
                del lang_cache[i]
                return

def get_cache_entries(app_name: str, target_lang: str):
    if not app_name:
        app_name = "default"
    with _cache_lock:
        return _cache.get(app_name, {}).get(target_lang, []).copy()

def clear_app_cache(app_name: str):
    if not app_name:
        app_name = "default"
    with _cache_lock:
        if app_name in _cache:
            del _cache[app_name]
        filepath = os.path.join(_cache_dir, f"{app_name}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass
