import os

import configobj


LEGACY_SECTION = "YATTA"
BOOLEAN_KEYS = {
    "ollama_stream",
    "openai_stream",
    "gemini_stream",
    "save_cache",
    "separate_numbers",
    "filter_nvda_messages",
    "play_sound",
    "auto_swap",
}

DEFAULTS = {
    "service": "google",
    "source_lang": "auto",
    "target_lang": "en",
    "deepl_key": "",
    "ollama_address": "http://localhost:11434",
    "ollama_model": "translategemma:4b",
    "ollama_system_prompt": "",
    "ollama_user_prompt": "You are a professional {SOURCE_LANG} ({SOURCE_CODE}) to {TARGET_LANG} ({TARGET_CODE}) translator. Your goal is to accurately convey the meaning and nuances of the original {SOURCE_LANG} text while adhering to {TARGET_LANG} grammar, vocabulary, and cultural sensitivities.\nProduce only the {TARGET_LANG} translation, without any additional explanations or commentary. The text may contain placeholders like <token0>, it is essential they are reproduced exactly in the translation if they appear in the source text. Please translate the following {SOURCE_LANG} text into {TARGET_LANG}:\n\n{TEXT}",
    "ollama_stream": True,
    "openai_key": "",
    "openai_address": "https://api.openai.com/v1",
    "openai_model": "gpt-5.4-mini",
    "openai_system_prompt": "You are an expert translator. Translate the given text to the target language.",
    "openai_user_prompt": "{TEXT}",
    "openai_stream": True,
    "gemini_key": "",
    "gemini_model": "gemini-3.5-flash",
    "gemini_system_prompt": "You are an expert translator. Translate the given text to the target language.",
    "gemini_user_prompt": "{TEXT}",
    "gemini_stream": True,
    "save_cache": True,
    "separate_numbers": False,
    "filter_nvda_messages": True,
    "play_sound": True,
    "auto_swap": False,
}

_global_config = None
_global_config_path = None


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _normalize(values, default_target_lang):
    result = DEFAULTS.copy()
    result["target_lang"] = default_target_lang
    result.update(values)
    for key in BOOLEAN_KEYS:
        result[key] = _as_bool(result[key])
    return result


def _write(filepath, values, config_factory=None):
    if config_factory is None:
        config_factory = configobj.ConfigObj
    output = config_factory(encoding="UTF-8")
    output.filename = filepath
    for key, value in values.items():
        output[key] = str(value) if isinstance(value, bool) else value
    output.write()


def initialize(nvda_config, config_path, default_target_lang, logger, config_factory=None):
    """Load global settings and migrate the legacy NVDA config section."""
    global _global_config, _global_config_path

    if config_factory is None:
        config_factory = configobj.ConfigObj
    settings_dir = os.path.join(config_path, "yatta", "settings")
    filepath = os.path.join(settings_dir, "global.ini")
    os.makedirs(settings_dir, exist_ok=True)

    file_exists = os.path.exists(filepath)
    stored = config_factory(filepath, encoding="UTF-8") if file_exists else {}
    values = dict(stored)
    base_config = nvda_config.profiles[0]

    if LEGACY_SECTION in base_config:
        values.update(dict(base_config[LEGACY_SECTION]))
        migrated = _normalize(values, default_target_lang)
        _write(filepath, migrated, config_factory)
        del base_config[LEGACY_SECTION]
        nvda_config.spec.pop(LEGACY_SECTION, None)
        nvda_config.save()
        logger.info(
            "YATTA: Migrated global settings from nvda.ini to %s",
            filepath,
        )
    elif not file_exists:
        _write(filepath, _normalize(values, default_target_lang), config_factory)

    _global_config_path = filepath
    _global_config = _normalize(values, default_target_lang)
    return _global_config


def get_global_config():
    if _global_config is None:
        raise RuntimeError("YATTA global settings have not been initialized")
    return _global_config


def save(config_factory=None):
    if _global_config is None or _global_config_path is None:
        raise RuntimeError("YATTA global settings have not been initialized")
    _write(_global_config_path, _global_config, config_factory)
