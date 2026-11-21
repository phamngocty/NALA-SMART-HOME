import asyncio
from living_context_engine import (
    LivingContextEngine, STATE_EMPTY, STATE_ACTIVE,
    STATE_APPROACHING, STATE_DEEP_SLEEP, STATE_NIGHT_WAKEUP
)

async def test_all():
    engine = LivingContextEngine()
    # Mock night time
    engine._is_night_time = lambda: True

    room_id = "test_bedroom"
    room_name = "Phòng ngủ"

    print("--- TEST 1: Empty Room ---")
    st = await engine.update_radar_telemetry(room_id, room_name, {"presence": False})
    print(f"State: {st} (Expected: empty)")
    assert st == STATE_EMPTY

    print("\n--- TEST 2: Active / Daytime Moving ---")
    engine._is_night_time = lambda: False
    st = await engine.update_radar_telemetry(room_id, room_name, {
        "presence": True, "dist_cm": 250, "mv_eng": 60, "st_eng": 20, "light": 100
    })
    print(f"State: {st} (Expected: active)")
    assert st == STATE_ACTIVE

    print("\n--- TEST 3: Approaching Panel ---")
    st = await engine.update_radar_telemetry(room_id, room_name, {
        "presence": True, "dist_cm": 60, "is_approaching": True, "light": 100
    })
    print(f"State: {st} (Expected: approaching)")
    assert st == STATE_APPROACHING

    print("\n--- TEST 4: Deep Sleep Transition (Night + Dark + Breathing) ---")
    engine._is_night_time = lambda: True
    # Fast forward stationary time
    ctx = engine.get_room_state(room_id)
    ctx.consecutive_stationary_sec = 35.0  # Simulated 35s in bed
    st = await engine.update_radar_telemetry(room_id, room_name, {
        "presence": True, "dist_cm": 200, "st_eng": 55, "mv_eng": 2, "light": 0
    })
    print(f"State: {st} (Expected: deep_sleep)")
    assert st == STATE_DEEP_SLEEP

    print("\n--- TEST 5: Turning in Bed (Hysteresis Filter: brief movement <= 3s) ---")
    # Brief movement for 1 second
    st = await engine.update_radar_telemetry(room_id, room_name, {
        "presence": True, "dist_cm": 200, "st_eng": 30, "mv_eng": 40, "light": 0
    })
    print(f"State: {st} (Expected: deep_sleep - Tránh bật đèn chói mắt khi trở mình!)")
    assert st == STATE_DEEP_SLEEP

    print("\n--- TEST 6: Getting out of bed at night (Active > 4s) -> Night Wakeup ---")
    ctx.consecutive_active_sec = 5.0 # Sustained walking out of bed
    st = await engine.update_radar_telemetry(room_id, room_name, {
        "presence": True, "dist_cm": 110, "st_eng": 10, "mv_eng": 65, "light": 0
    })
    print(f"State: {st} (Expected: night_wakeup - Kích hoạt đèn dẫn đường dịu mắt!)")
    assert st == STATE_NIGHT_WAKEUP

    print("\n--- TEST 7: Return to bed -> Deep Sleep ---")
    ctx.consecutive_stationary_sec = 25.0
    st = await engine.update_radar_telemetry(room_id, room_name, {
        "presence": True, "dist_cm": 200, "st_eng": 60, "mv_eng": 0, "light": 0
    })
    print(f"State: {st} (Expected: deep_sleep - Đã ngủ lại!)")
    assert st == STATE_DEEP_SLEEP

    print("\n>>> TẤT CẢ 7 BÀI TEST NGỮ CẢNH SỐNG (FSM) ĐỀU PASS 100%! <<<")

if __name__ == "__main__":
    asyncio.run(test_all())
