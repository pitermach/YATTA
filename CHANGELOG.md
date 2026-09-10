# Changelog

## 2.1

- Move all YATTA settings into their own configuration file to prevent them from leaking into NVDA's log in certain situations
- Hide API keys in YATTA settings
- Add braille messages for entering and exiting the YATTA command layer
- Add a layer help command telling users about the ability to tab through all available commands

This version was made in large part thanks to suggestions made by @tspivey.

## 2.0.1

- Increased the Ollama request timeout to 30 seconds.

## 2.0

- Added the enabled-by-default “Don’t translate NVDA messages, such as control information” setting. Automatic translation now preserves NVDA-generated control roles, states, position, and formatting information.
- Increased the Ollama request timeout to 20 seconds and added a “Loading model” announcement when a local model is still loading.
- Fixed OpenAI translations failing when text contains characters outside Latin-1.
