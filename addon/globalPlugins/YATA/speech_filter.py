"""Identify user content inside NVDA speech sequences.

The tagging approach is adapted from Polyglot's smart speech filter:
https://github.com/cary-rowen/polyglot
Copyright (C) 2025-2026 cary-rowen, licensed under GPL v3 or later.
"""


class TranslatableString(str):
    """User content which should be sent to the translation engine."""


class UntranslatableString(str):
    """NVDA-generated control, state, or formatting information."""


_TRANSLATABLE_PROPERTY_KEYS = (
    "name",
    "value",
    "description",
    "rowHeaderText",
    "columnHeaderText",
    "placeholder",
    "errorMessage",
)


def _mark_all_untranslatable(sequence):
    return [
        UntranslatableString(item) if isinstance(item, str) else item
        for item in sequence
    ]


def extract_translatable_text(sequence, enabled=True):
    """Return joined user content and its string positions in ``sequence``."""
    pairs = [
        (index, item)
        for index, item in enumerate(sequence)
        if isinstance(item, str)
        and (not enabled or not isinstance(item, UntranslatableString))
        and item.strip()
    ]
    return (
        " ".join(item.strip() for _, item in pairs),
        [index for index, _ in pairs],
    )


def reconstruct_speech_sequence(sequence, translatable_indices, translation):
    """Replace translatable strings while retaining NVDA metadata and commands."""
    reconstructed = list(sequence)
    if not translatable_indices:
        return reconstructed
    reconstructed[translatable_indices[0]] = translation
    for index in translatable_indices[1:]:
        reconstructed[index] = ""
    return reconstructed


class SmartSpeechFilter:
    """Tag strings produced by NVDA's speech formatting helpers."""

    def __init__(self, speech_package, speech_module):
        self._speech_package = speech_package
        self._speech_module = speech_module
        self._patches = []
        self._suppression_depth = 0

    @property
    def is_suppressed(self):
        return self._suppression_depth > 0

    def _patch_aliases(self, name, replacement):
        seen = set()
        for owner in (self._speech_module, self._speech_package):
            if id(owner) in seen or not hasattr(owner, name):
                continue
            seen.add(id(owner))
            original = getattr(owner, name)
            self._patches.append((owner, name, original, replacement))
            setattr(owner, name, replacement)

    def register(self):
        """Install tagging hooks used before the final speech sequence is built."""
        get_properties = self._speech_module.getPropertiesSpeech

        def hooked_get_properties(*args, **kwargs):
            for key in _TRANSLATABLE_PROPERTY_KEYS:
                value = kwargs.get(key)
                if isinstance(value, str) and value.strip():
                    kwargs[key] = TranslatableString(value)
            result = get_properties(*args, **kwargs)
            return [
                item
                if isinstance(item, TranslatableString)
                else UntranslatableString(item)
                if isinstance(item, str)
                else item
                for item in result
            ]

        self._patch_aliases("getPropertiesSpeech", hooked_get_properties)

        if hasattr(self._speech_module, "getFormatFieldSpeech"):
            get_format_field = self._speech_module.getFormatFieldSpeech

            def hooked_get_format_field(*args, **kwargs):
                return _mark_all_untranslatable(get_format_field(*args, **kwargs))

            self._patch_aliases("getFormatFieldSpeech", hooked_get_format_field)

        if hasattr(self._speech_module, "getControlFieldSpeech"):
            get_control_field = self._speech_module.getControlFieldSpeech

            def hooked_get_control_field(*args, **kwargs):
                attrs = kwargs.get("attrs")
                if attrs is None and args:
                    attrs = args[0]
                content = attrs.get("content") if hasattr(attrs, "get") else None
                result = get_control_field(*args, **kwargs)
                tagged = []
                for item in result:
                    if isinstance(item, str) and not isinstance(
                        item, (TranslatableString, UntranslatableString)
                    ):
                        marker = (
                            TranslatableString
                            if content is not None and item == content
                            else UntranslatableString
                        )
                        item = marker(item)
                    tagged.append(item)
                return tagged

            self._patch_aliases("getControlFieldSpeech", hooked_get_control_field)

        if hasattr(self._speech_module, "getSpellingSpeech"):
            get_spelling = self._speech_module.getSpellingSpeech

            def hooked_get_spelling(*args, **kwargs):
                return (
                    UntranslatableString(item) if isinstance(item, str) else item
                    for item in get_spelling(*args, **kwargs)
                )

            self._patch_aliases("getSpellingSpeech", hooked_get_spelling)

        if hasattr(self._speech_module, "_getSelectionMessageSpeech"):
            get_selection_message = self._speech_module._getSelectionMessageSpeech

            def hooked_get_selection_message(message, text):
                prefix, separator, suffix = message.partition("%s")
                if isinstance(text, list):
                    if not separator:
                        return _mark_all_untranslatable(
                            self._speech_module._getSpeakMessageSpeech(message)
                        ) + text
                    result = list(text)
                    if prefix:
                        result.insert(0, UntranslatableString(prefix))
                    if suffix:
                        result.append(UntranslatableString(suffix))
                    return result

                max_length = self._speech_module.MAX_LENGTH_FOR_SELECTION_REPORTING
                if not separator or len(text) >= max_length:
                    return _mark_all_untranslatable(
                        get_selection_message(message, text)
                    )

                result = []
                if prefix:
                    result.append(UntranslatableString(prefix))
                if text:
                    result.append(TranslatableString(text))
                if suffix:
                    result.append(UntranslatableString(suffix))
                return result

            self._patch_aliases(
                "_getSelectionMessageSpeech", hooked_get_selection_message
            )

        if hasattr(self._speech_module, "getIndentationSpeech"):
            get_indentation = self._speech_module.getIndentationSpeech

            def hooked_get_indentation(*args, **kwargs):
                return _mark_all_untranslatable(
                    get_indentation(*args, **kwargs)
                )

            self._patch_aliases("getIndentationSpeech", hooked_get_indentation)

        if hasattr(self._speech_module, "speakTypedCharacters"):
            speak_typed_characters = self._speech_module.speakTypedCharacters

            def hooked_speak_typed_characters(*args, **kwargs):
                self._suppression_depth += 1
                try:
                    return speak_typed_characters(*args, **kwargs)
                finally:
                    self._suppression_depth -= 1

            self._patch_aliases(
                "speakTypedCharacters", hooked_speak_typed_characters
            )

    def unregister(self):
        """Restore every speech helper replaced by :meth:`register`."""
        for owner, name, original, replacement in reversed(self._patches):
            if getattr(owner, name, None) is replacement:
                setattr(owner, name, original)
        self._patches.clear()
