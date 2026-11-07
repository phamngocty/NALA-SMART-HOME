import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server_nas_hub'))

from app.history_manager import HistoryManager

mgr = HistoryManager(base_dir=os.path.join(os.path.dirname(__file__), 'test_hist_dir'))

# Add turn 1
r1 = mgr.add_record(
    device_code="881C",
    room_name="Phòng ngủ ty",
    session_type="voice_ai",
    text="Bật máy lạnh phòng ngủ ty 26 độ",
    response="Đã bật máy lạnh 26 độ",
    session_id="sess_test_123",
    turn_index=1,
    ai_model="Google Gemini 2.5"
)

# Add turn 2
r2 = mgr.add_record(
    device_code="881C",
    room_name="Phòng ngủ ty",
    session_type="voice_ai",
    text="Hạ xuống 22 độ đi",
    response="Đã hạ xuống 22 độ",
    session_id="sess_test_123",
    turn_index=2,
    ai_model="Google Gemini 2.5"
)

recs = mgr.get_records()
print("Total records:", len(recs))
assert len(recs) == 2
assert recs[0]["session_id"] == "sess_test_123"
assert recs[1]["session_id"] == "sess_test_123"

# Test delete session
cnt = mgr.delete_session("sess_test_123")
print("Deleted count:", cnt)
assert cnt == 2
assert len(mgr.get_records()) == 0

print("Test chat history passed successfully!")
