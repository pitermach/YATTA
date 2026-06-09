# YATTA (Yet Another Text Translation Addon)


- Author: Piotr Machacz
- Compatibility: NVDA 2025.3 or higher
- Download: [Stable Version](https://github.com/pitermach/YATTA/releases/download/v1.0/YATTA-1.0.nvda-addon)


YATTA is a translation add-on for NVDA that’s optimized for translating programs and games on the fly. Some of its features include:


- Support for a number of translation services. Both traditional – Google Translate, Bing, DeepL, as well as LLM-based – Ollama, OpenAI, Gemini can be used. Using a combination of Ollama and a model like translategemma can provide very high quality translations completely offline.
- Translate the last spoken phrase, text selection in any app or webpage, or the clipboard. The translation can either be spoken or put in a virtual buffer for easier navigation.
- Automatic translation of anything spoken by NVDA, enabled per-app.
- A dynamic caching system with support for regular expressions, allowing you to translate strings like “You have obtained 30 gold” only once. Numbers can automatically be saved as regular expressions in the cache
- Per-application options to customize language, LLM prompts, caching and other settings


## Quick Start


YATTA can be installed either by opening the nvda-addon file from a file manager or using the “Install from external source” button in the Add-on store. It’s ready for use immediately after installation. By default, Google translate will be used and the text will be translated into NVDA’s language.


To start using YATTA, you need to remember just one shortcut – NVDA+Shift+T. Pressing it will let you perform any of the available translation actions by typing its letter. For example, pressing T will translate the last thing NVDA said. At any time after pressing this shortcut you can review all of the available commands by pressing tab. Pressing enter on a command will activate it. Pressing any other key will exit the command layer.


To change things like the service being used or translation languages, open NVDA’s settings and locate the YATTA category. It’s also possible to change certain options just for a particular application. You will find more information about all available settings below.


## Available commands


All of the commands available in the NVDA+Shift+T layer can also have dedicated shortcuts assigned to them through NVDA’s input gestures dialog.


Press T to translate the last spoken phrase, S to translate the selected text in a document or web page, or C to translate the clipboard. Pressing any of the above commands with shift will cause the translation to be displayed in a virtual buffer instead of being spoken out-loud.


Press A to toggle automatic translation. When this option is on, YATTA will automatically translate anything NVDA says. Note that this will introduce some latency between when you press a key and NVDA starting to speak, since YATTA has to wait for the translation to complete. Any spoken text is cached in memory, so if NVDA says the same text again reaction time should be much faster. This setting is saved only for the focused application. This means that if you need to do something in another program and switch away, translation will pause and resume automatically as soon as you come back.


Pressing W will swap the source and target languages. This command will only work if the source language is not set to auto-detect. If you have configured specific settings for the focused program (more on this later), the swap will be performed for that program, otherwise the global setting will be changed.


Pressing O will open app-specific settings for the focused program, while pressing E will open the Cache Editor. Both of these features will be explained in their own sections.


## Settings


The global options for YATTA can be changed in NVDA’s settings dialog in the YATTA category. Some services will require more configuration than others. The dialog will only show you settings appropriate for the translation service you selected.


- Translation Service – select the service used for translation
- Source Language, Target Language – select what languages to translate between. Pressing either button will display a dialog allowing you to select the language by either typing it in or selecting it from the list with arrow keys. For conventional translation services, the list of languages is obtained from their servers and you can only select a supported language. For LLMs, if a translation-specific model is being used like translategemma, the list will contain all of the languages listed as officially supported
- API Key – for services that require one, such as DeepL, OpenAI and Gemini
- Address/Base URL (for Ollama) – by default will connect to Ollama running on the same computer as NVDA.
- Model – for LLM-based services. You can either type in a model name manually or use the “Select Model...” button to choose from a list
- System Prompt, User Prompt – the prompts sent to LLM services. If a model has a recommended default prompt, IE translategemma, you can use the “load default Prompts” button to automatically insert it into the fields. While entering a prompt, you can use the following variables which will be substituted during translation:

  - \{SOURCE\_LANG\} – source language name in English (IE Japanese)
  - \{SOURCE\_CODE\} – language code of the source language (IE ja)
  - \{TARGET\_LANG\}, \{TARGET\_CODE\} – same as above, but for the target language
  - \{TEXT\} – the text to be translated

- Stream responses – if this is checked, responses from LLM services will be read out as they come in, rather than waiting for the complete translation. Leaving this option checked is highly recommended as it greatly improves responsiveness.
- Save cache to disk – when this is checked, the translation cache is saved to disk when NVDA exits. Turning this off will still keep translations in memory but not save them to disk. This setting can be overridden on a per-app basis, IE to save cache only in specific programs.

- Separate numbers when translating – if this is checked, any text containing numbers is automatically saved in the cache as a regular expression with placeholders for each number.

- Automatically Swap languages if text is already in Target language – this option is only available when a conventional service is being used and the source language is not auto-detect. If the translation service detects that the text is already in the target language, the translation is silently performed again with the languages swapped. Note that performing translations this way takes longer and requires accessing the service twice, so if you find you want to do a lot of swapped translations it’s better to do this manually by pressing W from the layer. The language detection may also be less accurate with shorter texts.

- Play sound during longer operations – if a translation is taking longer and this is checked, a click is played every 2 seconds to let you know YATTA is still working on the translation



In addition to the global options, some settings can be changed for a specific application by pressing O from the command layer. These settings include the translation language, prompts, cache saving, automatic number splitting and more. The dialog also has a Reset button which allows you to restore the settings for a program to the global defaults.


## Translation Cache


YATTA keeps a cache of every translated phrase. The cache is saved separately for each language and each program. There are two kinds of cache entries. The majority of cache entries just map a specific phrase to its translation in a given language. This will be most of the cache entries that will be created by YATTA.


In addition, a cache entry can be added as a regular expression. This is useful in a situation where a piece of text comes up very often, but with slight changes. For example, messages like “You made it to level 4 and scored 42000 points” can be saved once, marking the numbers as a capture group. The translation service will then see the text as “You made it to level \<token1\> and scored \<token2\> points. When YATTA sees those tokens in the translations it knows where to put the numbers. From then on, even if the level or number of points changes in that message, YATTA won’t have to translate it again. Because strings with changing numbers come up very often, especially in games, YATTA includes the automatic split numbers when translating feature which will detect and save text like this as regular expressions. However, the caching feature can be further customized by adding or editing entries manually. You can do so from the cache editor, accessed by pressing E from the command layer.


To illustrate using all the capabilities, let’s use an example from the popular game Crazy party when it presents the statistics of an opponent.


the azure viper, ""poison"" type, with 20 health points and 40 cards in their deck.


The automatic number detection would already create an entry that would match an azure viper with any amount of health and cards, but it’s possible to modify the entry so that it can match for any opponent, wile translating their name and type separately. To do this you can either press the Add or Edit button in the cache editor. The Edit Entry dialog is very simple and only has 3 fields – edit boxes for the source text and translation, and a checkbox marking the entry as a regular expression.


In our example, the source text might look like the following:

```

^(.+), ("".+"" type), with (-?\\d+(?:\[.,/\]\\d+)*) health points and (-?\\d+(?:\[.,/\]\\d+)*) cards in their deck\.$

```


Then, when entering the translation result you can use the entered groups in one of 2 ways. If you type \{T1\}, \{T2\}, \{T3\}… that text will be translated separately and the translation will be inserted in the place of the token. If you enter \{P4\}, \{P5\}, \{P6\}… the text will be inserted without translating, which is especially useful for numbers.


An example translation into Polish would look like this:


```

{T1}, {T2}, {P3} punktów życia i {P4} kart w swojej talii.

```


When Yatta encounters this string, it will first separately translate and cache the name of the enemy, then its type, and when reading the text it will use those translations and insert whatever numbers it finds for the health points to read you the translation.


## Additional notes



If you decide to use local ollama models, translategemma from google is a great starting point. If you have a GPU with 12 GB of vram, you can use the 12b variant which will take about 8 GB of memory and provide decent results. For GPU’s with less RAM or if you find the translation is too slow, the 4b version will take about 3 GB of memory while still providing a very accurate translation. To download either of these models, after installing ollama open a command prompt and enter the following:

```

ollama pull translategemma:12b

```

Substituting 12b for 4b if that’s the version you want to download. Additionally, making some adjustments in Ollama’s settings can improve performance. In particular using the minimum context size of 4096 will speed up processing and reduce memory usage. YATTA does not keep conversation context and splits longer translations every 4000 characters, so a large context is not needed.


While Google provides a list of supported languages for translategemma and recommends providing both a source and target language in the prompt, in practice it’s possible to not specify a source language instead telling the model to “auto detect”, and get a good result, or specify a target language that’s not officially supported. That being said, specifying both source and target languages can greatly improve accuracy, not just for language models. Using app-specific options works great for this purpose.


Using translategemma models has one disadvantage compared to a service like DeepL or cloud models, it has a habit of omitting tokens when translating dynamic strings. It’s a good idea to modify your default prompt to underscore that these tokens should be preserved, which will help but is not a silver bullet. The default YATTA prompt for Ollama, separate from the one provided by Google, already tries to do this. If a token does get omitted, YATTA will warn you about this, read the missing value and not save the translation to cache. If you find this is happening often for a given usecase, specify a source language, try using a different service, making more dynamic cache entries, or turning off number splitting.


Lastly, on the topic of number splitting, it’s a feature best used in specific apps or games. For general purpose translation of texts like social media posts, it’s better to send the text with all numbers intact to the service to preserve formatting of things like dates.

## Contributing

If you found a bug, want to suggest a feature or want to translate YATTA into your own language, you are more than welcome to do so. The best way to do this is by opening a github issue.

For development and translation, a subset of the [NVDA addon template](https://github.com/nvaccess/AddonTemplate) is used. To build the addon package or generate the .pot file for translation, you need to have python, scons, gettext and the markdown python package. the python dependencies such as scons and markdown can be installed through uv, while gettext can be downloaded easily using winget.



## Credits

YATTA would not have been possible if not for the NVDA addons that came before and inspired various aspects of its design. These include JGT (aka the japanese games translator), [Instant Translate](https://github.com/nvdaaddons/instantTranslate) and [NVDA Translate](https://github.com/yplassiard/nvda-translate)

I would also like to thank my testers - Oriol Gomez and Talon, who have both provided invaluable feedback during development of this add-on.

## Disclaimers


- While YATTA does not collect any information on its own, any text you translate is sent to the translation service you selected. Be mindful of the privacy policy of the service you are using and do not translate any sensitive information.

- Neither YATTA nor the service providers can guarantee the accuracy of a translation. LLM’s can hallucinate and even conventional services can provide incorrect translations. If you are translating sensitive information, consult a professional translator.

- Large Language Models, specifically Google Gemini, were used to aid in development of this add-on.
