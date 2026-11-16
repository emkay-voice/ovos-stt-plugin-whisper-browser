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
    "ovos-stt-plugin-whisper-browser": {"model": "onnx-community/whisper-base"}
  }
}
```

`model` is any Whisper model in ONNX for transformers.js:

| model | download | notes |
|---|---|---|
| `onnx-community/whisper-tiny` | ~120 MB | fastest; fine for English |
| `onnx-community/whisper-base` | ~140 MB | default; good English, Danish so-so |
| `onnx-community/whisper-small` | ~420 MB | better for languages other than English, slower |

(The encoder is kept at full precision, since it loses too much at 8 bit;
the decoder is 8-bit.)

On a phone without WebGPU, expect a few seconds per sentence with tiny or
base. Whisper knows about 100 languages; `available_languages` lists them.

## License

Apache-2.0
