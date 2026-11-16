# ovos-stt-plugin-whisper-browser

An [OpenVoiceOS](https://openvoiceos.org) speech-to-text plugin that runs
OpenAI's **Whisper** on the device itself, in the browser. The recording
never leaves the device: only the model is downloaded, once, the first time
it is used.

It was made for [Emkay](https://github.com/emkay-voice/emkay), OpenVoiceOS in
the browser (Pyodide), as its offline speech recognition. It takes the place
of [ovos-stt-plugin-fasterwhisper](https://github.com/OpenVoiceOS/ovos-stt-plugin-fasterwhisper)
and whispercpp, whose native code cannot be installed in a browser.

## How it works

The plugin hands the recording to the host page's Whisper engine and gets
the text back. In Emkay that is
[`web/whisper.js`](https://github.com/emkay-voice/emkay/blob/main/web/whisper.js),
in the same Web Worker as OVOS:

- [transformers.js](https://github.com/huggingface/transformers.js)
  (Apache-2.0), which does what a device's Whisper plugin does: log-mel
  features, the encoder, decoding with Whisper's tokenizer
- onnxruntime-web, on WebGPU where the browser has it, else WebAssembly
- the model, in ONNX from [onnx-community](https://huggingface.co/onnx-community)
  on Hugging Face, kept in the browser's cache after the first download

Until the model has downloaded, the plugin raises, and the host transcribes
with `stt.fallback_module` meanwhile (Emkay does, as ovos-dinkum-listener
does), so the first question is never lost.

A host provides, as a global the worker's Python can reach (`js`):

```js
emkayWhisper.ready(model)                        // Promise<bool>: starts loading; true once loaded
emkayWhisper.transcribe(pcm16, rate, lang, model) // Promise<string>
```

## Configuration

```json
{
  "stt": {
    "module": "ovos-stt-plugin-whisper-browser",
    "fallback_module": "ovos-stt-plugin-server",
    "ovos-stt-plugin-whisper-browser": {}
  }
}
```

While the model downloads the first time, the plugin fails so
`fallback_module` hears you. With `"wait_for_download": true` it waits for the
model instead; for when there is no network to fall back on (Emkay's "local
only" mode sets it).

The model follows the language, as Piper's voice does: a language with a
model of its own that does better uses that one (`MODELS`), every other
language the multilingual `onnx-community/whisper-base`.

| language | model | download |
|---|---|---|
| English | `onnx-community/whisper-base.en` (English-only: better and faster) | ~140 MB |
| Danish | `emkay-voice/roest-wav2vec2-315m-onnx` ([Røst](https://huggingface.co/CoRal-project/roest-v3-wav2vec2-315m) from CoRal, trained on Danish speech) | ~320 MB |
| others | `onnx-community/whisper-base` | ~140 MB |

Whisper learned the big languages from tens of thousands of hours each, but
a small language from a few hundred, and a model small enough for a phone
does not learn a language well from that: whisper-base gets about two
Danish words in three wrong. Many countries have trained models of their
own on national data, and those can do much better. Danish uses Røst, which
is not Whisper but a wav2vec2 model; the host runs it the same way. The
tests behind the choice, and how to add a language with a national model,
are in [emkay-voice/stt-models](https://github.com/emkay-voice/stt-models).

Røst's license (adapted from OpenRAIL-M) allows commercial use but forbids
using it for speech synthesis and biometric identification.

`model` in the config sets one model for every language instead, any
speech recognition model in ONNX for transformers.js, for instance
`onnx-community/whisper-tiny` (~65 MB, faster, less accurate) or
`onnx-community/whisper-small` (~510 MB, more accurate, slow without WebGPU).

(The encoder is kept at full precision, since it loses too much at 8 bit;
the decoder is 8-bit.)

On a phone without WebGPU, expect a few seconds per sentence with tiny or
base. Whisper knows about 100 languages; `available_languages` lists them.

## License

Apache-2.0
