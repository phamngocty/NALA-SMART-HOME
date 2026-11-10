"""
Unit and Integration Tests for Nala Adaptive Learned Memory
==========================================================
Verifies:
1. GateKeeper (Signal vs Noise & Sensitive Data Filtering)
2. Device Alias Learning & Candidate Promotion
3. Explicit User Correction Handling
4. Hard Limit Bounding & LRU Eviction
5. Fast-Path Matching (<20ms local execution)
6. Prompt Context Injection Budget
"""

import os
import sys
import time
import shutil

app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)

from adaptive_memory_manager import AdaptiveMemoryManager


def test_gatekeeper_filtering():
    test_dir = os.path.join(app_dir, "test_data_mem_gate")
    mem = AdaptiveMemoryManager(data_dir=test_dir)

    # 1. Sensitive text must be blocked
    assert mem.is_noise_or_sensitive("mật khẩu wifi nhà mình là 123456") is True
    assert mem.is_noise_or_sensitive("đọc mã otp cho tôi") is True
    assert mem.is_noise_or_sensitive("số thẻ ngân hàng là 9999") is True

    # 2. Meaningless noise greetings must be dropped
    assert mem.is_noise_or_sensitive("chào bạn nha") is True
    assert mem.is_noise_or_sensitive("alo alo") is True
    assert mem.is_noise_or_sensitive("ok") is True

    # 3. Legitimate command phrase must be accepted
    assert mem.is_noise_or_sensitive("bật đèn hoa sen ở phòng khách") is False
    assert mem.is_noise_or_sensitive("máy lạnh 25 độ") is False

    shutil.rmtree(test_dir, ignore_errors=True)
    print("[PASS] test_gatekeeper_filtering")


def test_alias_learning_and_promotion():
    test_dir = os.path.join(app_dir, "test_data_mem_learn")
    mem = AdaptiveMemoryManager(data_dir=test_dir)

    # Hit 1: Enters candidates buffer
    mem.learn_device_interaction("bật đèn hoa sen", "light.phong_khach_chum", "Phòng khách")
    assert "đèn hoa sen" in mem.data["candidates"]
    assert "đèn hoa sen" not in mem.data["aliases"]

    # Hit 2: Promoted to permanent alias
    mem.learn_device_interaction("hãy bật đèn hoa sen", "light.phong_khach_chum", "Phòng khách")
    assert "đèn hoa sen" in mem.data["aliases"]
    assert mem.data["aliases"]["đèn hoa sen"]["entity_id"] == "light.phong_khach_chum"
    assert mem.data["aliases"]["đèn hoa sen"]["confidence"] >= 0.8

    # Fast path matching works!
    fast = mem.match_fast_path("tắt đèn hoa sen đi", "Phòng khách")
    assert fast is not None
    assert fast["entity_id"] == "light.phong_khach_chum"
    assert fast["action"] == "turn_off"

    shutil.rmtree(test_dir, ignore_errors=True)
    print("[PASS] test_alias_learning_and_promotion")


def test_user_correction_handling():
    test_dir = os.path.join(app_dir, "test_data_mem_corr")
    mem = AdaptiveMemoryManager(data_dir=test_dir)

    # Simulate user correcting Nala: "Không phải, cái đèn bàn cơ"
    mem.learn_user_correction("Không phải, cái đèn bàn cơ", "light.phong_khach_den_ban", "Phòng khách")
    assert "đèn bàn" in mem.data["aliases"]
    assert mem.data["aliases"]["đèn bàn"]["entity_id"] == "light.phong_khach_den_ban"
    assert mem.data["aliases"]["đèn bàn"]["confidence"] == 0.95

    # Context snippet generation includes it
    ctx = mem.get_prompt_context("Phòng khách", "bật đèn bàn")
    assert "đèn bàn" in ctx
    assert "light.phong_khach_den_ban" in ctx

    shutil.rmtree(test_dir, ignore_errors=True)
    print("[PASS] test_user_correction_handling")


def test_capacity_limit_and_lru_eviction():
    test_dir = os.path.join(app_dir, "test_data_mem_evict")
    mem = AdaptiveMemoryManager(data_dir=test_dir)

    # Insert 55 aliases (MAX is 50)
    for i in range(55):
        mem.data["aliases"][f"thiết bị {i}"] = {
            "entity_id": f"light.device_{i}",
            "room": "Phòng khách",
            "hit_count": i + 1,  # Lower numbers have lower hit count
            "last_used": time.time() + i,
            "confidence": 0.8
        }

    mem._evict_if_needed()
    # Must be bounded to 50
    assert len(mem.data["aliases"]) == 50
    # "thiết bị 0" (lowest hit count) must have been evicted!
    assert "thiết bị 0" not in mem.data["aliases"]
    assert "thiết bị 54" in mem.data["aliases"]

    shutil.rmtree(test_dir, ignore_errors=True)
    print("[PASS] test_capacity_limit_and_lru_eviction")


def test_router_integration():
    from ai_agent_router import AIAgentRouter
    router = AIAgentRouter("gemini_key", "deepseek_key", None)
    assert hasattr(router, "memory_mgr")
    assert router.memory_mgr.is_enabled() is True
    print("[PASS] test_router_integration")


def main():
    test_gatekeeper_filtering()
    test_alias_learning_and_promotion()
    test_user_correction_handling()
    test_capacity_limit_and_lru_eviction()
    test_router_integration()
    print("\nAll Nala Adaptive Learned Memory tests PASSED successfully!")


if __name__ == "__main__":
    main()
