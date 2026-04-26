"""
Module: audio_buffer.py
Zone: 2 (Live session — no network, no cloud calls)
Input: raw bytes from BLE stream
Output: AudioChunk objects routed to Stream A (transcript) or Stream B (paralinguistic)
LLM calls: 0
Side effects: None
Latency tolerance: <5ms per chunk (50ms chunk size target)

50ms chunk buffering. Receives raw PCM bytes from audio_bridge and yields
AudioChunk objects tagged with stream identity. Both streams consume the
same raw bytes independently.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncIterator


class AudioStream(str, Enum):
    A = "A"  # Transcript (verbal) — feeds transcription_engine
    B = "B"  # Paralinguistic (how it's said) — feeds audio_signal_processor


@dataclass
class AudioChunk:
    raw_bytes: bytes
    timestamp: datetime
    stream: AudioStream
    chunk_index: int
    duration_ms: float = 50.0


class AudioBuffer:
    """
    50ms chunk buffer. Receives raw PCM bytes and fans out to Stream A and B.
    Both streams receive the same bytes — processing diverges downstream.
    Zone 2 only. No network calls.
    """

    CHUNK_DURATION_MS: float = 50.0

    def __init__(self) -> None:
        self._queue_a: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=200)
        self._queue_b: asyncio.Queue[AudioChunk] = asyncio.Queue(maxsize=200)
        self._chunk_index: int = 0

    def push(self, raw_bytes: bytes) -> None:
        """
        Push raw PCM bytes into the buffer.
        Creates one AudioChunk per call and fans to both queues.
        Drops oldest chunk if either queue is full (never blocks Zone 2 loop).
        """
        ts = datetime.now(timezone.utc)
        chunk_a = AudioChunk(
            raw_bytes=raw_bytes,
            timestamp=ts,
            stream=AudioStream.A,
            chunk_index=self._chunk_index,
        )
        chunk_b = AudioChunk(
            raw_bytes=raw_bytes,
            timestamp=ts,
            stream=AudioStream.B,
            chunk_index=self._chunk_index,
        )
        self._chunk_index += 1

        # Non-blocking puts — drop if full rather than stalling the audio loop
        try:
            self._queue_a.put_nowait(chunk_a)
        except asyncio.QueueFull:
            try:
                self._queue_a.get_nowait()  # drop oldest
            except asyncio.QueueEmpty:
                pass
            self._queue_a.put_nowait(chunk_a)

        try:
            self._queue_b.put_nowait(chunk_b)
        except asyncio.QueueFull:
            try:
                self._queue_b.get_nowait()
            except asyncio.QueueEmpty:
                pass
            self._queue_b.put_nowait(chunk_b)

    async def get_stream_a(self) -> AudioChunk:
        """Awaitable get for Stream A (transcript consumer)."""
        return await self._queue_a.get()

    async def get_stream_b(self) -> AudioChunk:
        """Awaitable get for Stream B (paralinguistic consumer)."""
        return await self._queue_b.get()

    def qsize_a(self) -> int:
        return self._queue_a.qsize()

    def qsize_b(self) -> int:
        return self._queue_b.qsize()
