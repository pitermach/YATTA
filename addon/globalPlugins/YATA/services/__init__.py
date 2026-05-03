import typing

class TranslationEngine:
    """
    Base class for translation services.
    """
    name = "Base"
    has_api_key = False
    
    def __init__(self, config: dict):
        """
        Initialize the engine with configuration parameters.
        """
        self.config = config

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "en", stream: bool = False) -> typing.Union[str, typing.Iterator[str]]:
        """
        Translate text from source_lang to target_lang.
        If stream is True, returns an iterator yielding chunks of string as they arrive.
        """
        raise NotImplementedError("Translation engine must implement `translate`.")
        
    def get_supported_languages(self) -> dict:
        """
        Returns a dictionary of supported languages: { "code": "Language Name" }
        """
        return {}
