"""Pruebas de voz aisladas: no requieren Vosk, micrófono ni modelo descargado."""

import json
import sys
import types
import wave

import pytest

from speech import SpeechRecognizer


def test_transcribe_file_with_mock_vosk(monkeypatch, tmp_path):
    class FakeModel:
        def __init__(self, path):
            self.path = path

    class FakeRecognizer:
        def __init__(self, model, rate):
            assert rate == 16000

        def AcceptWaveform(self, data):
            assert data

        def FinalResult(self):
            return json.dumps({"text": "hola arus"})

    monkeypatch.setitem(sys.modules, "vosk", types.SimpleNamespace(
        Model=FakeModel, KaldiRecognizer=FakeRecognizer
    ))
    audio = tmp_path / "test.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 800)

    assert SpeechRecognizer().transcribe_file(str(audio)) == "hola arus"


def test_transcribe_file_rejects_wrong_sample_rate(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "vosk", types.SimpleNamespace(
        Model=lambda path: object(), KaldiRecognizer=lambda model, rate: object()
    ))
    audio = tmp_path / "wrong_rate.wav"
    with wave.open(str(audio), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 20)

    with pytest.raises(ValueError, match="Frecuencia incorrecta"):
        SpeechRecognizer().transcribe_file(str(audio))
