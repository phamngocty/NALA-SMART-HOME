import sys
import time
import asyncio
import edge_tts

sys.stdout.reconfigure(encoding='utf-8')

sentence_short = "Chào bạn, mình là Nala quản gia AI của bạn đây."
paragraph_long = "Chào bạn! Mình là Nala, quản gia AI của nhà bạn đây! Mình có thể bật tắt đèn, quạt, điều chỉnh máy lạnh, kích hoạt các kịch bản như xem phim hay đi ngủ, và tắt toàn bộ thiết bị khi bạn ra ngoài. Cứ ra lệnh thoải mái nhé!"

async def measure(text, label):
    t0 = time.time()
    comm = edge_tts.Communicate(text, "vi-VN-NamMinhNeural")
    audio = b""
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    dur = time.time() - t0
    print(f"[{label}] Text len: {len(text)} chars ({len(text.split())} words) -> Audio: {len(audio)} bytes in {dur*1000:.0f}ms")

async def main():
    print("Testing Edge-TTS sentence chunk vs full paragraph latency...")
    await measure(sentence_short, "CÂU 1 (CHUNK)")
    await measure(paragraph_long, "CẢ ĐOẠN (FULL)")

asyncio.run(main())
