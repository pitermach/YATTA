You will be developing an NVDA addon used for text translation. Your primary reference should be the NVDA addon development guide. 
https://github.com/nvdaaddons/DevGuide/wiki/NVDA-Add-on-Development-Guide
There are also existing addons you can look at for implementation examples of services:
- Advanced translate supports the most services
https://github.com/hxebolax/TranslateAdvanced
- Instant translate uses a good system for layered commands
https://github.com/nvdaaddons/instantTranslate
- NVDA translate, good use of automatic translation and cache
https://github.com/yplassiard/nvda-translate

The addon should have the following features:
- Supports multiple services to handle translation: LLM-based - Ollama, as well as traditional - Google translate, deepL and bing.
- Have the translation functions and each service in a separate include so that new services can be added easily in the future and the translation functions can be reused by different features. Make services modular so that they can have their own settings if necessary. Broadly there will be two kinds of potential translation engines - traditional which support a preset list of languages, and LLM-based which work on a system prompt to specify the language and send the text through the user prompt.
Support the following functions:
- Translate last spoken phrase
- Translate selection
- Translate Clipboard
- automatically Translate any spoken text before NVDA speaks it.
- Translation cache, separate for each application so that any text which was already cached doesn't have to be translated again.

For settings, the addon should add its own panel to NVDA's settings dialog with the following fields:
- Service selection
- Settings appropriate for each service:
	- For Ollama, field to specify address, defaulting to localhost, model selection, field for the system prompt, whether responses should be streamed.
	- For traditional services, Combo boxes for source and target language (defaulting to auto-detect for source), and if a service requires it, a field for an API key.

All keyboard shortcuts for the addon should be contained in a separate layer, accessed with an input gesture defaulting to NVDA+Shift+T. Look at the instant translate addon to see how this layer should work:

- S: translate selection
- T: Translate last phrase
- C: Translate clipboard
- A: toggle automatic translation

The addon will be stored in a git repository which you can initialize, so commit any changes you make, but don't push them yet.

