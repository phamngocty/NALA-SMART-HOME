"""
Unit tests for GroqFailoverClient
Validates model discovery filtering, candidate ordering, cooldown mechanics, and cascading rollback.
"""

import asyncio
import time
from unittest.mock import patch, MagicMock
from groq_failover_client import GroqFailoverClient


async def test_scan_models_filtering():
    client = GroqFailoverClient(api_key="gsk_dummy_test_key")

    mock_models_response = {
        "data": [
            {"id": "llama-3.3-70b-versatile", "active": True, "context_window": 128000},
            {"id": "whisper-large-v3", "active": True, "context_window": 1500},
            {"id": "llama-guard-3-8b", "active": True, "context_window": 8192},
            {"id": "llama-3.1-8b-instant", "active": True, "context_window": 128000},
            {"id": "deprecated-model", "active": False, "context_window": 4096},
            {"id": "qwen-2.5-32b", "active": True, "context_window": 32768},
        ]
    }

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = mock_models_response

    with patch("httpx.AsyncClient.get", return_value=mock_res):
        models = await client.scan_and_sync_models(force_refresh=True)

    ids = [m["id"] for m in models]
    assert "llama-3.3-70b-versatile" in ids
    assert "llama-3.1-8b-instant" in ids
    assert "qwen-2.5-32b" in ids
    # Non-chat or inactive models must be filtered out
    assert "whisper-large-v3" not in ids
    assert "llama-guard-3-8b" not in ids
    assert "deprecated-model" not in ids
    print("[PASS] test_scan_models_filtering")


def test_candidate_ordering_and_cooldown():
    client = GroqFailoverClient(api_key="gsk_dummy_test_key")
    # Pre-populate cache
    client._cached_models = {
        "llama-3.3-70b-versatile": {"id": "llama-3.3-70b-versatile"},
        "llama-3.1-8b-instant": {"id": "llama-3.1-8b-instant"},
        "qwen-2.5-32b": {"id": "qwen-2.5-32b"},
        "deepseek-r1-distill-llama-70b": {"id": "deepseek-r1-distill-llama-70b"},
    }

    # 1. Preferred model selected first
    candidates = client.get_candidate_models(preferred_model="qwen-2.5-32b")
    assert candidates[0] == "qwen-2.5-32b"
    assert "llama-3.3-70b-versatile" in candidates
    assert "llama-3.1-8b-instant" in candidates

    # 2. Put preferred model on cooldown (simulate 429)
    client.mark_model_cooldown("qwen-2.5-32b", reason="Rate limit")
    candidates_after_cooldown = client.get_candidate_models(preferred_model="qwen-2.5-32b")
    # "qwen-2.5-32b" should be demoted to the end of the queue
    assert candidates_after_cooldown[0] != "qwen-2.5-32b"
    assert candidates_after_cooldown[-1] == "qwen-2.5-32b"

    # 3. Permanently deprecate a model (simulate 404)
    client.mark_model_deprecated("llama-3.3-70b-versatile", reason="Decommissioned")
    candidates_after_deprecate = client.get_candidate_models()
    assert "llama-3.3-70b-versatile" not in candidates_after_deprecate
    print("[PASS] test_candidate_ordering_and_cooldown")


async def test_cascading_rollback():
    client = GroqFailoverClient(api_key="gsk_dummy_test_key")
    client._cached_models = {
        "llama-3.3-70b-versatile": {"id": "llama-3.3-70b-versatile"},
        "llama-3.1-8b-instant": {"id": "llama-3.1-8b-instant"},
    }

    # Mock response: 1st call (llama-3.3-70b) returns 429, 2nd call (llama-3.1-8b) returns 200
    mock_res_429 = MagicMock()
    mock_res_429.status_code = 429
    mock_res_429.text = "Rate limit reached for model llama-3.3-70b-versatile on TPM"

    mock_res_200 = MagicMock()
    mock_res_200.status_code = 200
    mock_res_200.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "Phòng khách đã bật đèn."}}]
    }

    call_count = 0

    async def mock_post(url, headers=None, json=None, timeout=None):
        nonlocal call_count
        call_count += 1
        if json.get("model") == "llama-3.3-70b-versatile":
            return mock_res_429
        elif json.get("model") == "llama-3.1-8b-instant":
            return mock_res_200
        return mock_res_429

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        result = await client.chat_completion(
            messages=[{"role": "user", "content": "Bật đèn phòng khách"}],
            preferred_model="llama-3.3-70b-versatile"
        )

    assert result["success"] is True
    assert result["model_used"] == "llama-3.1-8b-instant"
    assert result["rollback_occurred"] is True
    assert len(result["rollback_history"]) == 1
    assert result["rollback_history"][0]["http_code"] == 429
    assert result["message"]["content"] == "Phòng khách đã bật đèn."
    print("[PASS] test_cascading_rollback")


async def test_ai_agent_router_integration():
    from ai_agent_router import AIAgentRouter
    router = AIAgentRouter("dummy_gemini", "dummy_deepseek", None)
    router.config["groq"] = {
        "api_key": "gsk_test_groq",
        "model": "llama-3.3-70b-versatile"
    }
    router.groq_client.set_api_key("gsk_test_groq")
    router.groq_client._cached_models = {
        "llama-3.3-70b-versatile": {"id": "llama-3.3-70b-versatile"},
        "llama-3.1-8b-instant": {"id": "llama-3.1-8b-instant"}
    }

    mock_res_429 = MagicMock(status_code=429, text="Rate limit 429 TPM reached")
    mock_res_200 = MagicMock(status_code=200)
    mock_res_200.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": "Đèn ban công đã bật."}}]
    }

    async def mock_post(url, headers=None, json=None, timeout=None):
        if json and json.get("model") == "llama-3.3-70b-versatile":
            return mock_res_429
        return mock_res_200

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        reply = await router.process_intent("Bật đèn ban công", model_preference="groq")

    assert reply == "Đèn ban công đã bật."
    print("[PASS] test_ai_agent_router_integration")


async def main():
    await test_scan_models_filtering()
    test_candidate_ordering_and_cooldown()
    await test_cascading_rollback()
    await test_ai_agent_router_integration()
    print("\nAll Groq Rollback & Router Integration tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
