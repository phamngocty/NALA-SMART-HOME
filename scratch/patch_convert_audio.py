import re

with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    code = f.read()

old_convert = """def convert_audio_to_pcm16k(audio_bytes: bytes) -> Optional[bytes]:
    \"\"\"Chuyển đổi mọi định dạng âm thanh (WebM, OGG, MP3, WAV, AAC...) sang 16kHz 16-bit Mono Linear PCM qua ffmpeg.\"\"\"
    if not audio_bytes:
        return None
    import subprocess
    try:
        proc = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(input=audio_bytes, timeout=8)
        if proc.returncode == 0 and out and len(out) > 0:
            return out
        else:
            logger.warning("[FFMPEG] Convert warning: %s", err.decode(errors='ignore') if err else "empty output")
    except Exception as e:
        logger.error("[FFMPEG] Exception during convert: %s", e)
    return None"""

new_convert = """def convert_audio_to_pcm16k(audio_bytes: bytes) -> Optional[bytes]:
    \"\"\"Chuyển đổi mọi định dạng âm thanh (WebM, OGG, MP3, WAV, AAC, raw PCM) sang 16kHz 16-bit Mono Linear PCM.\"\"\"
    if not audio_bytes or len(audio_bytes) < 4:
        return None

    # 1. Fast path: Nếu là chuẩn file WAV 16kHz mono 16-bit
    if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:12]:
        try:
            import io, wave
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == 16000:
                    return wf.readframes(wf.getnframes())
        except Exception:
            pass

    # 2. Sử dụng ffmpeg chuyển đổi tự động (hỗ trợ WebM, OGG, MP3, WAV đa kênh/tần số khác)
    import subprocess
    try:
        proc = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(input=audio_bytes, timeout=8)
        if proc.returncode == 0 and out and len(out) > 0:
            return out
    except Exception as e:
        logger.warning("[FFMPEG] Convert warning: %s", e)

    # 3. Fallback: Nếu là raw PCM s16le không header
    if len(audio_bytes) % 2 == 0 and len(audio_bytes) >= 8000:
        return audio_bytes

    return None"""

assert old_convert in code, "old_convert not found in main_ws_server.py"
code = code.replace(old_convert, new_convert, 1)

with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully patched convert_audio_to_pcm16k in main_ws_server.py!")
