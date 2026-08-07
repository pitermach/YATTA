# Changelog

## 2.0

- Added the enabled-by-default “Don’t translate NVDA messages, such as control information” setting. Automatic translation now preserves NVDA-generated control roles, states, position, and formatting information.
- Increased the Ollama request timeout to 20 seconds and added a “Loading model” announcement when a local model is still loading.
- Fixed OpenAI translations failing when text contains characters outside Latin-1.
