import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

# Import ConversationSessionManager once implemented or test directly
from typing import Dict, Any, List, Optional
import unicodedata

def _normalize_vn(s: str) -> str:
    if not s:
        return ""
    s = s.replace("đ", "d").replace("Đ", "d")
    nfd = unicodedata.normalize('NFD', s)
    no_marks = "".join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()
    return no_marks

class ConversationSessionManager:
    def __init__(self, session_timeout: float = 120.0, max_history_turns: int = 8):
        self.session_timeout = session_timeout
        self.max_history_turns = max_history_turns
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_history(self, device_id: str) -> List[Dict[str, str]]:
        if not device_id:
            return []
        session = self.sessions.get(device_id)
        if not session:
            return []
        if time.time() - session.get("last_active", 0) > self.session_timeout:
            self.sessions.pop(device_id, None)
            return []
        return list(session.get("history", []))

    def add_turn(self, device_id: str, user_text: str, assistant_text: str):
        if not device_id or not user_text or not assistant_text:
            return
        now = time.time()
        if device_id not in self.sessions:
            self.sessions[device_id] = {
                "history": [],
                "created_at": now,
                "last_active": now,
                "turn_count": 0
            }
        sess = self.sessions[device_id]
        sess["last_active"] = now
        sess["turn_count"] += 1
        sess["history"].append({"role": "user", "content": user_text})
        sess["history"].append({"role": "assistant", "content": assistant_text})
        if len(sess["history"]) > self.max_history_turns:
            sess["history"] = sess["history"][-self.max_history_turns:]

    def clear_session(self, device_id: str):
        if device_id in self.sessions:
            self.sessions.pop(device_id, None)

    @staticmethod
    def is_farewell(text: str) -> bool:
        if not text:
            return False
        normalized = _normalize_vn(text).strip()
        farewell_keywords = [
            "tam biet", "bye", "goodbye", "cam on", "cam on nhe", "cam on ban",
            "thoi", "thoi duoc roi", "nghi di", "im di", "im lang", "het roi",
            "khong co gi", "dung lai", "khong can nua", "ok roi", "duoc roi"
        ]
        for kw in farewell_keywords:
            if normalized == kw or normalized.startswith(kw + " ") or normalized.endswith(" " + kw) or (f" {kw} " in normalized):
                return True
        return False

# Unit tests
sm = ConversationSessionManager(session_timeout=1.0, max_history_turns=4)

# 1. Test add_turn & get_history
sm.add_turn("panel_1", "Bật đèn phòng khách", "Đã bật đèn phòng khách.")
hist = sm.get_history("panel_1")
assert len(hist) == 2, f"Expected 2 messages, got {len(hist)}"
assert hist[0]["role"] == "user"
assert hist[1]["role"] == "assistant"
print("✓ Test 1: add_turn & get_history passed!")

# 2. Test sliding window max_history_turns
sm.add_turn("panel_1", "Giảm nhiệt độ máy lạnh", "Đã giảm nhiệt độ.")
sm.add_turn("panel_1", "Tắt tivi", "Đã tắt tivi.")
hist2 = sm.get_history("panel_1")
assert len(hist2) == 4, f"Expected max 4 messages, got {len(hist2)}"
assert hist2[0]["content"] == "Giảm nhiệt độ máy lạnh"
print("✓ Test 2: sliding window passed!")

# 3. Test timeout expiry
time.sleep(1.1)
hist_expired = sm.get_history("panel_1")
assert len(hist_expired) == 0, "Expected session to expire after 1.1s"
print("✓ Test 3: session timeout expiry passed!")

# 4. Test is_farewell
assert sm.is_farewell("Cảm ơn bạn nhé") is True
assert sm.is_farewell("Tạm biệt Nala") is True
assert sm.is_farewell("Thôi được rồi") is True
assert sm.is_farewell("Bật máy lạnh 24 độ") is False
assert sm.is_farewell("Tắt đèn phòng ngủ tỉ") is False
print("✓ Test 4: farewell detection passed!")

print("\nALL UNIT TESTS PASSED 100%!")
