"""The plugin against a pretend host page (no browser needed)."""
import sys
import types

import pytest
from ovos_plugin_manager.utils.audio import AudioData

import ovos_stt_plugin_whisper_browser as plugin


class Host:
    """What the page provides as `emkayWhisper`, synchronous here."""

    def __init__(self, ready=True, text=" Hvad er klokken?"):
        self._ready, self._text = ready, text
        self.calls = []

    def ready(self, model):
        self.calls.append(("ready", model))
        return self._ready

    def transcribe(self, pcm, rate, lang, model):
        self.calls.append(("transcribe", len(pcm), rate, lang, model))
        return self._text


@pytest.fixture
def host(monkeypatch):
    h = Host()
    monkeypatch.setitem(sys.modules, "js", types.SimpleNamespace(emkayWhisper=h))
    ffi = types.SimpleNamespace(run_sync=lambda x: x, to_js=lambda b: b)
    monkeypatch.setitem(sys.modules, "pyodide", types.SimpleNamespace(ffi=ffi))
    monkeypatch.setitem(sys.modules, "pyodide.ffi", ffi)
    return h


def audio(seconds=1.0, rate=16000):
    return AudioData(b"\x00\x00" * int(rate * seconds), rate, 2)


def test_transcribes_with_the_language_and_default_model(host):
    stt = plugin.WhisperBrowserSTT({})
    assert stt.execute(audio(), "nl-NL") == "Hvad er klokken?"
    assert host.calls[-1] == ("transcribe", 32000, 16000, "nl", plugin.DEFAULT_MODEL)


def test_a_language_with_its_own_model(host):
    plugin.WhisperBrowserSTT({}).execute(audio(), "en-US")
    assert host.calls[-1][-1] == plugin.MODELS["en"]


def test_the_model_comes_from_config(host):
    stt = plugin.WhisperBrowserSTT({"model": "onnx-community/whisper-tiny"})
    stt.execute(audio(), "en-US")
    assert host.calls[-1][-1] == "onnx-community/whisper-tiny"


def test_raises_while_the_model_downloads(host):
    host._ready = False
    with pytest.raises(RuntimeError):
        plugin.WhisperBrowserSTT({}).execute(audio(), "en-US")
    assert not any(c[0] == "transcribe" for c in host.calls)


def test_unknown_language(host):
    with pytest.raises(ValueError):
        plugin.WhisperBrowserSTT({}).execute(audio(), "xx-XX")


def test_languages():
    assert {"da", "en", "de", "fr", "nl"} <= plugin.WhisperBrowserSTT.available_languages
