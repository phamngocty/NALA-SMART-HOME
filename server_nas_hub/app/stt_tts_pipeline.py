"""
NALA SMART HOME - STT & TTS PIPELINE
Integrates Faster-Whisper GPU (GTX 1660 Ti) STT and Edge-TTS / Piper Neural Vietnamese TTS.
Converts between ESP32 16kHz 16-bit Mono PCM audio and natural text.
"""

import io
import os
import wave
import time
import logging
import asyncio
import subprocess
from typing import Optional, Dict
import aiohttp
import edge_tts

logger = logging.getLogger("AudioPipeline")

class AudioPipeline:
    def __init__(self, stt_url: Optional[str] = None, tts_url: Optional[str] = None):
        self.stt_url = stt_url or os.getenv("STT_SERVICE_URL", "http://127.0.0.1:8095/v1/audio/transcriptions")
        self.tts_url = tts_url or os.getenv("TTS_SERVICE_URL", "http://localhost:5000/api/tts")
        self.default_voice = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")
        
        # In-memory audio cache for common prompt confirmations (<1ms latency)
        self._pcm_cache: Dict[str, bytes] = {}

    async def pcm_to_text(self, pcm_data: bytes) -> str:
        """Chuyển đổi Raw PCM 16kHz 16-bit Mono sang Text qua Faster-Whisper GPU."""
        if not pcm_data or len(pcm_data) < 3200:  # < 100ms
            logger.warning("PCM data too short (%d bytes), skipping STT", len(pcm_data) if pcm_data else 0)
            return ""

        # Đóng gói PCM thô thành file WAV chuẩn trong bộ nhớ
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)
        wav_buffer.seek(0)

        data = aiohttp.FormData()
        data.add_field('file', wav_buffer, filename='speech.wav', content_type='audio/wav')
        data.add_field('model', 'Systran/faster-whisper-large-v3')
        data.add_field('language', 'vi')
        data.add_field('response_format', 'json')

        t0 = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.stt_url, data=data, timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status == 200:
                        res = await response.json()
                        text = res.get("text", "").strip()
                        elapsed = time.time() - t0
                        logger.info("Faster-Whisper GPU STT: '%s' (in %.2fs)", text, elapsed)
                        return text
                    else:
                        logger.error("STT service error %d: %s", response.status, await response.text())
        except Exception as e:
            logger.error("Failed to connect to Faster-Whisper STT (%s): %s", self.stt_url, e)
        return ""

    async def text_to_pcm(self, text: str, voice: Optional[str] = None) -> bytes:
        """Tạo audio giọng nói tiếng Việt từ văn bản bằng Edge-TTS chất lượng cao."""
        if not text or not text.strip():
            return b""

        clean_text = text.strip()
        selected_voice = voice or self.default_voice

        cache_key = f"{selected_voice}:{clean_text}"
        if cache_key in self._pcm_cache:
            logger.info("Using cached TTS PCM for '%s'", clean_text)
            return self._pcm_cache[cache_key]

        # 1. Thử qua Edge-TTS Neural
        try:
            t0 = time.time()
            comm = edge_tts.Communicate(clean_text, selected_voice)
            mp3_buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    mp3_buf.extend(chunk["data"])

            if mp3_buf:
                # Chuyển đổi MP3 sang Raw PCM 16kHz 16-bit Mono qua FFmpeg
                proc = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
                    "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000", "pipe:1",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                pcm_out, err = await proc.communicate(input=bytes(mp3_buf))
                if proc.returncode == 0 and pcm_out:
                    elapsed = time.time() - t0
                    logger.info("Edge-TTS synthesized %d bytes PCM (in %.2fs)", len(pcm_out), elapsed)
                    if len(self._pcm_cache) < 100:
                        self._pcm_cache[cache_key] = pcm_out
                    return pcm_out
                else:
                    logger.error("FFmpeg conversion failed: %s", err.decode('utf-8', errors='replace'))
        except Exception as e:
            logger.warning("Edge-TTS failed (%s), attempting fallback...", e)

        # 2. Fallback sang Piper TTS nếu có cấu hình
        if self.tts_url:
            try:
                async with aiohttp.ClientSession() as session:
                    params = {"text": clean_text}
                    async with session.get(self.tts_url, params=params, timeout=aiohttp.ClientTimeout(total=4)) as response:
                        if response.status == 200:
                            wav_bytes = await response.read()
                            with wave.open(io.BytesIO(wav_bytes), 'rb') as wav_file:
                                return wav_file.readframes(wav_file.getnframes())
            except Exception as e:
                logger.error("Piper TTS fallback also failed: %s", e)

        return b""
