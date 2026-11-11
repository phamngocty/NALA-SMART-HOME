import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main_ws_server

class TestVoiceFlowRegression(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_ws = AsyncMock()
        self.mock_ws.send_json = AsyncMock()
        self.mock_ws.send_bytes = AsyncMock()
        self.sample_audio = b"\x00\x01" * 3200

    async def _run_voice_command(self, recognized_text: str):
        self.mock_ws.reset_mock()
        with patch.object(main_ws_server.audio_pipeline, "pcm_to_text", new_callable=AsyncMock) as mock_stt, \
             patch.object(main_ws_server.audio_pipeline, "text_to_pcm", new_callable=AsyncMock) as mock_tts:

            mock_stt.return_value = recognized_text
            mock_tts.return_value = b"\x00\x01" * 1600

            await main_ws_server.handle_ai_voice_flow("TEST_DEV", self.mock_ws, self.sample_audio, client_format="pcm")

            sent_payloads = [call.args[0] for call in self.mock_ws.send_json.call_args_list]
            error_payloads = [
                p for p in sent_payloads 
                if isinstance(p, dict) and p.get("type") == "ai_state" and p.get("payload", {}).get("text") == "Lỗi xử lý âm thanh."
            ]
            self.assertEqual(len(error_payloads), 0, f"Command '{recognized_text}' raised 'Lỗi xử lý âm thanh.': {error_payloads}")
            return sent_payloads

    async def test_direct_smart_home_command(self):
        """Test direct smart home command."""
        payloads = await self._run_voice_command("Bật đèn phòng khách")
        self.assertTrue(any(p.get("type") == "ai_state" for p in payloads))

    async def test_indirect_intent_command(self):
        """Test indirect intent (Nóng quá)."""
        payloads = await self._run_voice_command("Phòng này nóng quá")
        self.assertTrue(any(p.get("type") == "ai_state" for p in payloads))

    async def test_intercom_hangup_command(self):
        """Test voice hangup (Cúp máy)."""
        # Set up an active intercom session for TEST_DEV
        main_ws_server.intercom.start_handsfree_call("TEST_DEV", "TARGET_DEV")
        payloads = await self._run_voice_command("Cúp máy đi")
        self.assertTrue(any(p.get("type") == "intercom_hangup" or p.get("payload", {}).get("state") == "idle" for p in payloads))

    async def test_intercom_call_command(self):
        """Test voice call to another room."""
        # Add target device to intercom
        mock_target_ws = AsyncMock()
        main_ws_server.intercom.register("TARGET_DEV", mock_target_ws, meta={"name": "Phòng ngủ"})
        payloads = await self._run_voice_command("Gọi cho phòng ngủ")
        self.assertTrue(any(p.get("type") == "intercom_call_started" or p.get("type") == "ai_state" for p in payloads))

if __name__ == "__main__":
    unittest.main()
