"""
NALA SMART HOME - STT & TTS PIPELINE
Communicates with local Faster-Whisper GPU container and Piper TTS service on PC NAS.
"""

import io
import wave
import logging
import aiohttp

logger = logging.getLogger("AudioPipeline")

class AudioPipeline:
    def __init__(self, stt_url: str, tts_url: str):
        self.stt_url = stt_url
        self.tts_url = tts_url

    async def pcm_to_text(self, pcm_data: bytes) -> str:
        """Chuyển đổi Raw PCM 16kHz 16-bit Mono sang Text qua Faster-Whisper (GTX 1080 Ti)."""
        # Đóng gói PCM thô thành file WAV chuẩn trong bộ nhớ
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2) # 16-bit
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm_data)
        wav_buffer.seek(0)

        data = aiohttp.FormData()
        data.add_field('file', wav_buffer, filename='speech.wav', content_type='audio/wav')
        data.add_field('language', 'vi')

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.stt_url, data=data, timeout=aiohttp.ClientTimeout(total=4)) as response:
                    if response.status == 200:
                        res = await response.json()
                        text = res.get("text", "").strip()
                        logger.info("STT Result: '%s'", text)
                        return text
                    else:
                        logger.error("STT service error %d: %s", response.status, await response.text())
        except Exception as e:
            logger.error("Failed to connect to Faster-Whisper STT service: %s", e)
        return ""

    async def text_to_pcm(self, text: str) -> bytes:
        """Tạo audio giọng nói tiếng Việt từ văn bản bằng Piper TTS."""
        if not text:
            return b""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"text": text}
                async with session.get(self.tts_url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        # Piper xuất file WAV, ta tách lấy raw PCM
                        wav_bytes = await response.read()
                        with wave.open(io.BytesIO(wav_bytes), 'rb') as wav_file:
                            return wav_file.readframes(wav_file.getnframes())
        except Exception as e:
            logger.error("Failed to generate speech with Piper TTS: %s", e)
        return b""
