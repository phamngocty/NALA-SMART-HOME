"""
NALA SMART HOME - AI AGENT ROUTER
Coordinates Gemini API and DeepSeek API with Home Assistant Tool Calling.
Handles natural language intent and smart home control.
"""

import os
import json
import logging
from typing import Dict, Any
import httpx
from google import genai
from google.genai import types

logger = logging.getLogger("AIRouter")

SYSTEM_PROMPT = """Bạn là Nala - Trợ lý giọng nói và quản gia AI của hệ thống NALA Smart Home.
Nhiệm vụ của bạn là:
1. Trả lời ngắn gọn, thân thiện, tự nhiên bằng tiếng Việt (tối đa 1-2 câu để phát loa không bị dài dòng).
2. Khi người dùng yêu cầu điều khiển thiết bị (bật/tắt đèn, quạt, máy lạnh, chuyển cảnh...), hãy gọi tool/function tương ứng.
"""

class AIAgentRouter:
    def __init__(self, gemini_api_key: str, deepseek_api_key: str, ha_bridge):
        self.gemini_key = gemini_api_key
        self.deepseek_key = deepseek_api_key
        self.ha_bridge = ha_bridge

        self.client_gemini = None
        if self.gemini_key and self.gemini_key != "your_gemini_api_key_here":
            self.client_gemini = genai.Client(api_key=self.gemini_key)

    async def process_intent(self, user_text: str, model_preference: str = "gemini") -> str:
        """Xử lý yêu cầu người dùng, ưu tiên xử lý intent nhà thông minh trực tiếp."""
        lower_text = user_text.lower().strip()

        # Kiểm tra Rule-based nhanh cho các lệnh bật tắt cơ bản (<50ms)
        if "bật đèn" in lower_text:
            await self.ha_bridge.call_service("light", "turn_on", "light.all_lights")
            return "Đã bật đèn cho bạn."
        elif "tắt đèn" in lower_text:
            await self.ha_bridge.call_service("light", "turn_off", "light.all_lights")
            return "Đã tắt tất cả đèn."

        # Nếu là câu hỏi mở hoặc giao tiếp, định tuyến sang Gemini hoặc DeepSeek
        if model_preference == "deepseek" and self.deepseek_key and self.deepseek_key != "your_deepseek_api_key_here":
            return await self._call_deepseek(user_text)
        elif self.client_gemini:
            return await self._call_gemini(user_text)
        else:
            return f"Tôi đã nghe: '{user_text}', nhưng chưa có API key AI để xử lý câu hỏi này."

    async def _call_gemini(self, text: str) -> str:
        try:
            response = self.client_gemini.models.generate_content(
                model='gemini-2.5-flash',
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                    max_output_tokens=150,
                ),
            )
            return response.text.strip()
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return "Xin lỗi, hiện tại tôi không thể kết nối tới Gemini."

    async def _call_deepseek(self, text: str) -> str:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.deepseek_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "max_tokens": 150
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error("DeepSeek API status %d: %s", res.status_code, res.text)
        except Exception as e:
            logger.error("DeepSeek call error: %s", e)
        return "Xin lỗi, tôi gặp lỗi khi liên lạc với DeepSeek."
