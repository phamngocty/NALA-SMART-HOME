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

    async def prewarm_common_cache(self):
        """Khởi tạo trước các mẫu âm thanh phản xạ tức thì (<1ms) vào RAM."""
        common_phrases = ["Dạ,", "Vâng ạ,", "Đã bật.", "Đã tắt.", "Đã tắt toàn bộ thiết bị."]
        for v in ["vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural"]:
            for phrase in common_phrases:
                try:
                    await self.text_to_pcm(phrase, voice=v)
                except Exception:
                    pass
        logger.info("⚡ Prewarmed %d instant audio phrases in RAM cache.", len(self._pcm_cache))

    async def groq_whisper_stt(self, wav_bytes: bytes, api_key: str, model: str = "whisper-large-v3-turbo") -> str:
        """Nhận diện giọng nói tiếng Việt siêu tốc qua Groq Cloud LPU Whisper (~0.15s, miễn phí 2000 req/ngày)."""
        if not api_key:
            return ""
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(wav_bytes), filename='speech.wav', content_type='audio/wav')
        data.add_field('model', model or 'whisper-large-v3-turbo')
        data.add_field('language', 'vi')
        data.add_field('response_format', 'json')
        data.add_field('temperature', '0.0')

        t0 = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=6)) as response:
                    if response.status == 200:
                        res = await response.json()
                        text = res.get("text", "").strip()
                        elapsed = time.time() - t0
                        logger.info("⚡ Groq Cloud Whisper STT (%s): '%s' (in %.3fs)", model, text, elapsed)
                        return text
                    else:
                        err_body = await response.text()
                        logger.warning("Groq Whisper STT API error %d: %s", response.status, err_body)
        except Exception as e:
            logger.warning("Groq Whisper STT request failed: %s", e)
        return ""

    async def pcm_to_text(self, pcm_data: bytes, groq_api_key: Optional[str] = None, stt_provider: str = "auto", groq_model: str = "whisper-large-v3-turbo") -> str:
        """Chuyển đổi Raw PCM 16kHz 16-bit Mono sang Text.
        Tự động ưu tiên Groq Cloud LPU Whisper (~0.15s, 0% GPU) và fallback Faster-Whisper Local GPU.
        """
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
        wav_bytes = wav_buffer.getvalue()

        # 1. Thử qua Groq Cloud Whisper nếu provider là 'groq' hoặc 'auto' (khi có api_key)
        if stt_provider in ("groq", "auto") and groq_api_key:
            groq_text = await self.groq_whisper_stt(wav_bytes, groq_api_key, model=groq_model)
            if groq_text:
                return groq_text
            if stt_provider == "groq":
                logger.warning("Groq STT failed and provider set to groq. Falling back to local Faster-Whisper.")

        # 2. Faster-Whisper Local GPU (http://localhost:8095)
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(wav_bytes), filename='speech.wav', content_type='audio/wav')
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
        # Sanitize text for TTS (prevent SSML / XML parser crashes)
        import re
        if clean_text.startswith("{") or ('"error"' in clean_text and '"code"' in clean_text):
            clean_text = "Hệ thống AI phản hồi lỗi, vui lòng kiểm tra lại API key hoặc model."
        else:
            # Loại bỏ ngoặc kép, dấu gạch chéo, backtick, markdown, SSML tags có thể phá vỡ parser
            clean_text = re.sub(r'["\'*`#_{}\[\]<>/\\~^|]', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            # Rút ngắn nếu quá dài
            if len(clean_text) > 350:
                clean_text = clean_text[:350]

        selected_voice = voice or self.default_voice

        cache_key = f"{selected_voice}:{clean_text}"
        if cache_key in self._pcm_cache:
            logger.info("Using cached TTS PCM for '%s'", clean_text)
            return self._pcm_cache[cache_key]

        # 1. Thử qua Edge-TTS Neural với danh sách giọng ưu tiên (giọng chọn -> tự động fallback sang NamMinh ổn định 100%)
        candidate_voices = [selected_voice]
        if selected_voice != "vi-VN-NamMinhNeural":
            candidate_voices.append("vi-VN-NamMinhNeural")

        for cur_voice in candidate_voices:
            for attempt in range(2):
                try:
                    t0 = time.time()
                    comm = edge_tts.Communicate(clean_text, cur_voice)
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
                            logger.info("Edge-TTS (%s) synthesized %d bytes PCM in %.2fs", cur_voice, len(pcm_out), elapsed)
                            if len(self._pcm_cache) < 100:
                                self._pcm_cache[cache_key] = pcm_out
                            return pcm_out
                        else:
                            logger.error("FFmpeg conversion failed: %s", err.decode('utf-8', errors='replace'))
                except Exception as e:
                    logger.warning("Edge-TTS voice %s (attempt %d) failed (%s)", cur_voice, attempt + 1, e)
                    if attempt == 0:
                        await asyncio.sleep(0.2)

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
