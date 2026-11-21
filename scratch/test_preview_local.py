import asyncio
import edge_tts

async def test_preview():
    comm = edge_tts.Communicate("Xin chào! Mình là Nala, trợ lý nhà thông minh của bạn.", "vi-VN-HoaiMyNeural", rate="+10%", pitch="+15Hz")
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    print(f"Generated preview audio: {len(buf)} bytes MP3")

asyncio.run(test_preview())
