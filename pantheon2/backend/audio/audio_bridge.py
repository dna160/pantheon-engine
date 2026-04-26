"""
Module: audio_bridge.py
Zone: 2 (Live session — no network, no cloud calls)
Input: WebSocket connection from mobile app (React Native BLE → backend)
Output: raw PCM bytes pushed into AudioBuffer
LLM calls: 0
Side effects: Fills AudioBuffer
Latency tolerance: <50ms (BLE target per PRD: <50ms Plaud → phone)

BLE receiver stub for Plaud Note Pro audio stream.
In the system architecture, the React Native mobile app holds the actual
BLE connection to the Plaud Note Pro and pipes raw PCM bytes to this
backend via WebSocket. This module receives those bytes and feeds AudioBuffer.

The actual BLE protocol integration (react-native-ble-plx) lives in
mobile/ble/BLEManager.ts and AudioStreamer.ts.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Optional

import structlog

from backend.audio.audio_buffer import AudioBuffer

logger = structlog.get_logger(__name__)


@dataclass
class AudioBridgeConfig:
    sample_rate: int = 16000       # Hz — Whisper small expects 16kHz
    channels: int = 1              # Mono
    bit_depth: int = 16            # PCM 16-bit
    chunk_size_bytes: int = 1600   # 50ms at 16kHz mono 16-bit = 1600 bytes


class AudioBridge:
    """
    Receives raw PCM bytes from the mobile app WebSocket and pushes
    into AudioBuffer for downstream Stream A and B processing.
    Zone 2 only. No network calls after connection is established.
    """

    def __init__(self, buffer: AudioBuffer, config: Optional[AudioBridgeConfig] = None) -> None:
        self._buffer = buffer
        self._config = config or AudioBridgeConfig()
        self._running = False
        self._bytes_received: int = 0
        self._on_stop: Optional[Callable] = None

    async def start(self) -> None:
        """Mark bridge as active. Called when session GO signal received."""
        self._running = True
        self._bytes_received = 0
        logger.info(
            "audio_bridge.started",
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
        )

    async def stop(self) -> None:
        """Stop the bridge. Called when session ends."""
        self._running = False
        logger.info(
            "audio_bridge.stopped",
            bytes_received=self._bytes_received,
        )

    def receive_bytes(self, raw_bytes: bytes) -> None:
        """
        Called by WebSocket handler when new PCM bytes arrive from mobile.
        Pushes bytes into AudioBuffer synchronously (no await needed —
        AudioBuffer.push is non-blocking).
        """
        if not self._running:
            return
        self._bytes_received += len(raw_bytes)
        self._buffer.push(raw_bytes)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def bytes_received(self) -> int:
        return self._bytes_received
