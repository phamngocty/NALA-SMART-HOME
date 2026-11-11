"""
Unit and Integration Tests for Nala Intelligence & Speed Optimization Plan
========================================================================
Covers:
1. Phase 1: STT Prompt Bias & Vocabulary Presence
2. Phase 2: Scoped Room Context & Fuzzy Levenshtein Entity Validator
3. Phase 3: Indirect Intent Engine & Multi-turn Dialogue Memory
4. Phase 4 / Intercom V2: Hands-Free Intercom Lifecycle, Triple-Layer Hangup & Voice-Switching
"""

import os
import sys
import time
import asyncio
from typing import Dict, Any, List

app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from stt_tts_pipeline import DEFAULT_SMART_HOME_WHISPER_PROMPT
from ai_agent_router import AIAgentRouter, ConversationSessionManager
from intercom_router import IntercomRouter


class MockHABridge:
    def __init__(self):
        self.states = {
            "light.cong_tat_phong_ngu_ty_den_1": {
                "state": "off",
                "attributes": {"friendly_name": "Đèn trần phòng ngủ ty"}
            },
            "light.cong_tat_phong_khach_den_1": {
                "state": "off",
                "attributes": {"friendly_name": "Đèn trần phòng khách"}
            },
            "climate.150633094640317_climate": {
                "state": "cool",
                "attributes": {
                    "friendly_name": "Máy lạnh phòng ngủ ty",
                    "temperature": 26.0,
                    "current_temperature": 27.5,
                    "hvac_mode": "cool"
                }
            },
            "fan.phong_khach_quat_tran": {
                "state": "off",
                "attributes": {"friendly_name": "Quạt trần phòng khách"}
            }
        }
        self.service_calls: List[dict] = []

    def get_entities_list(self) -> List[dict]:
        return [
            {
                "entity_id": "light.cong_tat_phong_ngu_ty_den_1",
                "name": "Đèn trần phòng ngủ ty",
                "domain": "light",
                "state": self.states["light.cong_tat_phong_ngu_ty_den_1"]["state"],
                "area_id": "phong_ngu_ty",
                "area_name": "Phòng ngủ ty",
                "attributes": self.states["light.cong_tat_phong_ngu_ty_den_1"]["attributes"]
            },
            {
                "entity_id": "light.cong_tat_phong_khach_den_1",
                "name": "Đèn trần phòng khách",
                "domain": "light",
                "state": self.states["light.cong_tat_phong_khach_den_1"]["state"],
                "area_id": "phong_khach",
                "area_name": "Phòng khách",
                "attributes": self.states["light.cong_tat_phong_khach_den_1"]["attributes"]
            },
            {
                "entity_id": "climate.150633094640317_climate",
                "name": "Máy lạnh phòng ngủ ty",
                "domain": "climate",
                "state": self.states["climate.150633094640317_climate"]["state"],
                "area_id": "phong_ngu_ty",
                "area_name": "Phòng ngủ ty",
                "attributes": self.states["climate.150633094640317_climate"]["attributes"]
            },
            {
                "entity_id": "fan.phong_khach_quat_tran",
                "name": "Quạt trần phòng khách",
                "domain": "fan",
                "state": self.states["fan.phong_khach_quat_tran"]["state"],
                "area_id": "phong_khach",
                "area_name": "Phòng khách",
                "attributes": self.states["fan.phong_khach_quat_tran"]["attributes"]
            }
        ]

    async def call_service(self, domain: str, service: str, entity_id: str = "", service_data: dict = None) -> bool:
        self.service_calls.append({
            "domain": domain,
            "service": service,
            "entity_id": entity_id,
            "service_data": service_data or {}
        })
        if domain == "climate" and service == "set_temperature" and entity_id in self.states:
            if service_data and "temperature" in service_data:
                self.states[entity_id]["attributes"]["temperature"] = service_data["temperature"]
        elif service in ("turn_on", "turn_off") and entity_id in self.states:
            self.states[entity_id]["state"] = "on" if service == "turn_on" else "off"
        return True

    async def master_turn_off_all(self) -> dict:
        self.service_calls.append({"action": "master_turn_off_all"})
        return {"turned_off_count": 4}


def test_phase1_stt_prompt_bias():
    assert "Nala ơi" in DEFAULT_SMART_HOME_WHISPER_PROMPT
    assert "đèn hắt" in DEFAULT_SMART_HOME_WHISPER_PROMPT
    assert "máy lạnh" in DEFAULT_SMART_HOME_WHISPER_PROMPT
    assert "cúp máy" in DEFAULT_SMART_HOME_WHISPER_PROMPT
    print("[PASS] test_phase1_stt_prompt_bias")


def test_phase2_scoped_room_context():
    router = AIAgentRouter(gemini_api_key="mock", deepseek_api_key="mock", ha_bridge=MockHABridge())
    ctx_room = router._build_device_context(context_room="Phòng ngủ ty")
    assert "THIẾT BỊ TẠI PHÒNG HIỆN TẠI (Phòng ngủ ty)" in ctx_room
    assert "light.cong_tat_phong_ngu_ty_den_1" in ctx_room
    assert "climate.150633094640317_climate" in ctx_room
    # Check that current room appears before other rooms
    pos_local = ctx_room.find("THIẾT BỊ TẠI PHÒNG HIỆN TẠI")
    pos_other = ctx_room.find("CÁC THIẾT BỊ KHÁC")
    assert pos_local != -1 and pos_other != -1 and pos_local < pos_other
    print("[PASS] test_phase2_scoped_room_context")


def test_phase2_fuzzy_entity_resolution():
    mock_ha = MockHABridge()
    router = AIAgentRouter(gemini_api_key="mock", deepseek_api_key="mock", ha_bridge=mock_ha)

    # 1. Misspelled/incomplete entity with room preference
    # Should resolve to phong_ngu_ty instead of phong_khach because context_room is 'Phòng ngủ ty'
    real_eid, fname = router._resolve_real_entity_id("den_tran_1", target_domain="light", context_room="Phòng ngủ ty")
    assert real_eid == "light.cong_tat_phong_ngu_ty_den_1"

    # 2. When room is 'Phòng khách', resolve to phong_khach
    real_eid_pk, fname_pk = router._resolve_real_entity_id("den_tran_1", target_domain="light", context_room="Phòng khách")
    assert real_eid_pk == "light.cong_tat_phong_khach_den_1"

    print("[PASS] test_phase2_fuzzy_entity_resolution")


def test_phase3_indirect_intents():
    mock_ha = MockHABridge()
    router = AIAgentRouter(gemini_api_key="mock", deepseek_api_key="mock", ha_bridge=mock_ha)

    async def run_tests():
        # Test 1: Nóng quá -> decrease temp
        mock_ha.service_calls.clear()
        reply = await router.handle_indirect_intent("Nóng nực quá", context_room="Phòng ngủ ty")
        assert reply is not None
        assert "hạ nhiệt độ" in reply or "24" in reply or "25" in reply
        assert any(c["domain"] == "climate" and c["service"] == "set_temperature" for c in mock_ha.service_calls)

        # Test 2: Tối thế -> turn on light in current room
        mock_ha.service_calls.clear()
        reply_light = await router.handle_indirect_intent("Phòng tối thế", context_room="Phòng ngủ ty")
        assert reply_light is not None
        assert "bật" in reply_light
        assert any(c["domain"] == "light" and c["entity_id"] == "light.cong_tat_phong_ngu_ty_den_1" for c in mock_ha.service_calls)

        # Test 3: Đi ngủ thôi -> bedtime routine
        mock_ha.service_calls.clear()
        reply_sleep = await router.handle_indirect_intent("Buồn ngủ quá đi ngủ thôi", context_room="Phòng ngủ ty")
        assert reply_sleep is not None
        assert "ngủ ngon" in reply_sleep

        # Test 4: Chuẩn bị ra ngoài -> master turn off all
        mock_ha.service_calls.clear()
        reply_leave = await router.handle_indirect_intent("Tôi chuẩn bị ra ngoài đi làm đây", context_room="Phòng khách")
        assert reply_leave is not None
        assert "tắt toàn bộ" in reply_leave
        assert any(c.get("action") == "master_turn_off_all" for c in mock_ha.service_calls)

    asyncio.run(run_tests())
    print("[PASS] test_phase3_indirect_intents")


def test_phase4_intercom_lifecycle():
    intercom = IntercomRouter()
    
    # Register 2 mock devices
    class MockWS:
        def __init__(self, key):
            self.key = key
            self.sent_messages = []
            self.sent_bytes = []
        async def send_json(self, msg):
            self.sent_messages.append(msg)
        async def send_bytes(self, b):
            self.sent_bytes.append(b)

    ws_living = MockWS("LIVING_01")
    ws_kitchen = MockWS("KITCHEN_02")

    intercom.register("LIVING_01", ws_living, 1, {"room_name": "Phòng khách", "floor": "Tầng trệt"})
    intercom.register("KITCHEN_02", ws_kitchen, 2, {"room_name": "Phòng bếp", "floor": "Tầng trệt"})

    # 1. Start handsfree call
    sess = intercom.start_handsfree_call("LIVING_01", "KITCHEN_02")
    assert sess is not None
    assert sess["state"] == "active"
    assert intercom.get_active_session_for_device("LIVING_01") is not None
    assert intercom.get_active_session_for_device("KITCHEN_02") is not None

    # 2. Voice hangup
    ended = intercom.end_handsfree_call("LIVING_01", reason="voice_command")
    assert ended is not None
    assert intercom.get_active_session_for_device("LIVING_01") is None
    assert intercom.get_active_session_for_device("KITCHEN_02") is None

    # 3. Test Silence Watchdog timeout
    sess2 = intercom.start_handsfree_call("LIVING_01", "KITCHEN_02")
    sess2["last_audio_time"] = time.time() - 11.0  # Simulated 11s silence
    
    warnings = []
    hangups = []
    
    async def run_watchdog():
        await intercom.check_silence_watchdogs(
            on_warning_cb=lambda s: warnings.append(s),
            on_hangup_cb=lambda s, r: hangups.append((s, r))
        )
        assert len(warnings) == 1
        
        # Advance to 14s silence -> should hangup
        sess2["last_audio_time"] = time.time() - 14.0
        await intercom.check_silence_watchdogs(
            on_warning_cb=lambda s: warnings.append(s),
            on_hangup_cb=lambda s, r: hangups.append((s, r))
        )
        assert len(hangups) == 1

    asyncio.run(run_watchdog())

    # 4. Test Voice Intercom Call Intent Detection
    mock_ha = MockHABridge()
    router = AIAgentRouter(gemini_api_key="mock", deepseek_api_key="mock", ha_bridge=mock_ha)
    targets = intercom.get_targets()
    matched = router.detect_intercom_call_intent("Nala ơi gọi cho phòng bếp giúp tôi", targets)
    assert matched is not None
    assert matched["code"] == "KITCHEN_02"
    assert "bếp" in matched["name"].lower()

    # 5. Test Voice-Switching Half-Duplex feedback suppression
    sess3 = intercom.start_handsfree_call("LIVING_01", "KITCHEN_02")
    # Simulate Living room transmitting packet -> Kitchen room speaker is playing
    # Binary PCM packet: 520 bytes: 0x5A 0xA5 sender_id target_id ...
    pcm_packet_living = bytearray(520)
    pcm_packet_living[0] = 0x5A
    pcm_packet_living[1] = 0xA5
    pcm_packet_living[2] = 1 # sender = living (id 1)
    pcm_packet_living[3] = 2 # target = kitchen (id 2)
    
    asyncio.run(intercom.route_binary_packet("LIVING_01", bytes(pcm_packet_living)))
    assert sess3["active_speaker"] == "LIVING_01"
    assert time.time() < sess3["speaker_release_time"]

    # Now if Kitchen room mic immediately tries to send a packet while Living room is playing -> should be suppressed!
    ws_living.sent_bytes.clear()
    pcm_packet_kitchen = bytearray(520)
    pcm_packet_kitchen[0] = 0x5A
    pcm_packet_kitchen[1] = 0xA5
    pcm_packet_kitchen[2] = 2
    pcm_packet_kitchen[3] = 1
    asyncio.run(intercom.route_binary_packet("KITCHEN_02", bytes(pcm_packet_kitchen)))
    # Because Kitchen mic is muted by Voice-Switching, nothing should have reached ws_living!
    assert len(ws_living.sent_bytes) == 0

    print("[PASS] test_phase4_intercom_lifecycle")


if __name__ == "__main__":
    test_phase1_stt_prompt_bias()
    test_phase2_scoped_room_context()
    test_phase2_fuzzy_entity_resolution()
    test_phase3_indirect_intents()
    test_phase4_intercom_lifecycle()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
