"""ovos-stt-plugin-whisper-browser: Whisper speech recognition on the device itself.

On a device, ovos-stt-plugin-fasterwhisper or -whispercpp run Whisper
with native code, which cannot be installed in Pyodide. This plugin hands
the recording to the host page's Whisper engine instead (in Emkay:
web/whisper.js, transformers.js on onnxruntime-web, in the same Web Worker
as OVOS) and gets the text back. The audio never leaves the device; only
the model is downloaded, once, the first time it is used.

Chosen like any STT plugin (`stt.module`). The model follows the language,
as ovos-tts-plugin-piper's voice does: MODELS has the best one that runs in
a browser for each language that has its own, and every other language
gets the multilingual DEFAULT_MODEL. Config:

- `model`: one Whisper model (Hugging Face, ONNX for transformers.js) for
  every language, instead of MODELS.

Until the model has downloaded, the plugin raises, and the host uses
`stt.fallback_module` meanwhile (Emkay does, as ovos-dinkum-listener does).

A host provides, as a global the worker's Python can reach (`js`):

    emkayWhisper.ready(model) -> Promise<bool>      starts loading; true once loaded
    emkayWhisper.transcribe(pcm16, rate, lang, model) -> Promise<str>
"""
from ovos_plugin_manager.templates.stt import STT
from ovos_utils import classproperty

PLUGIN = "ovos-stt-plugin-whisper-browser"
#: multilingual; for the languages not in MODELS (~140 MB)
DEFAULT_MODEL = "onnx-community/whisper-base"

#: a language's own model where one does better than the multilingual one.
#: English: OpenAI's English-only Whisper, better and faster at the same size.
MODELS = {
    "en": "onnx-community/whisper-base.en",
}


def model_for(lang: str) -> str:
    return MODELS.get((lang or "en").split("-")[0].lower(), DEFAULT_MODEL)

#: the languages Whisper was trained on (its tokenizer's language tokens)
LANGUAGES = {
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs",
    "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu",
    "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka",
    "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml",
    "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt",
    "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw",
    "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo",
    "zh", "yue",
}


class WhisperBrowserSTT(STT):
    """Whisper in the page's worker (Emkay: web/whisper.js)."""

    def __init__(self, config=None):
        super().__init__(config)
        self.model = self.config.get("model")   # None: by language (MODELS)

    def execute(self, audio, language=None):
        import js
        from pyodide.ffi import run_sync, to_js
        lang = (language or self.lang or "en").split("-")[0].lower()
        if lang not in LANGUAGES:
            raise ValueError(f"Whisper does not know the language {language}")
        model = self.model or model_for(lang)
        if not run_sync(js.emkayWhisper.ready(model)):
            # loading now; the host's stt.fallback_module hears this one
            raise RuntimeError(f"the Whisper model {model} is still downloading")
        pcm = audio.get_raw_data(convert_rate=None, convert_width=2)
        text = run_sync(js.emkayWhisper.transcribe(to_js(pcm), audio.sample_rate, lang, model))
        return str(text or "").strip()

    @classproperty
    def available_languages(cls) -> set:
        return set(LANGUAGES)
