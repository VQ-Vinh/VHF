from __future__ import annotations


class AudioError(Exception):
    """Base audio exception."""


class AudioDeviceNotFoundError(AudioError):
    """No suitable audio input device found."""


class AudioStreamError(AudioError):
    """Error opening or running audio stream."""
