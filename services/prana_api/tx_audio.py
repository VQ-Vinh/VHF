from __future__ import annotations

import io
import wave

from google.cloud import texttospeech


VOICE_BY_LANGUAGE = {
    "vi": ("vi-VN", "vi-VN-Standard-A"),
    "en": ("en-US", "en-US-Standard-C"),
    "zh": ("cmn-CN", "cmn-CN-Standard-A"),
    "ja": ("ja-JP", "ja-JP-Standard-A"),
    "ko": ("ko-KR", "ko-KR-Standard-A"),
}
MAX_TX_OUTPUT_SECONDS = 120.0


def _pcm_from_wav(data: bytes) -> tuple[bytes, int, int, int]:
    with wave.open(io.BytesIO(data), "rb") as source:
        if source.getsampwidth() != 2:
            raise ValueError("TTS WAV must use 16-bit PCM")
        return (
            source.readframes(source.getnframes()),
            source.getframerate(),
            source.getnchannels(),
            source.getsampwidth(),
        )


def append_over(main_wav: bytes, over_wav: bytes, silence_ms: int = 300) -> bytes:
    main_pcm, rate, channels, width = _pcm_from_wav(main_wav)
    over_pcm, over_rate, over_channels, over_width = _pcm_from_wav(over_wav)
    if (rate, channels, width) != (over_rate, over_channels, over_width):
        raise ValueError("TTS clips must have identical PCM formats")
    silence = bytes(int(rate * silence_ms / 1000) * channels * width)
    target = io.BytesIO()
    with wave.open(target, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(width)
        output.setframerate(rate)
        output.writeframes(main_pcm + silence + over_pcm)
    return target.getvalue()


def wav_duration_seconds(data: bytes) -> float:
    with wave.open(io.BytesIO(data), "rb") as source:
        rate = source.getframerate()
        if rate <= 0:
            raise ValueError("TX WAV has an invalid sample rate")
        return source.getnframes() / rate


class CloudTxSynthesizer:
    def __init__(self, project: str = ""):
        self.client = texttospeech.TextToSpeechClient()

    def _synthesize(self, text: str, language: str) -> bytes:
        locale, voice_name = VOICE_BY_LANGUAGE[language]
        response = self.client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code=locale,
                name=voice_name,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24_000,
            ),
        )
        return response.audio_content

    def synthesize_with_over(self, text: str, target_language: str) -> bytes:
        return append_over(
            self._synthesize(text, target_language),
            self._synthesize("Over", "en"),
        )
