import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server_nas_hub"))

from app.main_ws_server import load_all_house_config, save_all_house_config, get_house_status_summary, ha_bridge

print("1. Testing load_all_house_config()...")
cfg = load_all_house_config()
print("Loaded config:", cfg)
assert "controlled_domains" in cfg
assert "excluded_entities" in cfg

print("2. Mocking HA bridge states...")
ha_bridge.states = {
    "light.den_phong_khach": {"state": "on", "attributes": {"friendly_name": "Đèn Phòng Khách"}},
    "fan.quat_phong_ngu": {"state": "on", "attributes": {"friendly_name": "Quạt Phòng Ngủ"}},
    "climate.dieu_hoa_phong_chieu": {"state": "cool", "attributes": {"friendly_name": "Điều Hòa"}},
    "switch.tu_lanh": {"state": "on", "attributes": {"friendly_name": "Tủ Lạnh SamSung"}},
    "switch.wifi_router": {"state": "on", "attributes": {"friendly_name": "Router WiFi"}}
}

print("3. Testing get_house_status_summary() with default config...")
st1 = get_house_status_summary()
print("House status 1:", st1)
# With default config (controlled_domains: [light, fan], include_climate: False, include_switch: False):
assert st1["total_on_lights"] == 1
assert st1["total_on_fans"] == 1
assert st1["total_on_climates"] == 0
assert st1["total_on_switches"] == 0
assert st1["total_on_devices"] == 2
print("✓ Default count verified: 2 devices (1 light + 1 fan)")

print("4. Testing with excluded entities...")
cfg["excluded_entities"] = ["light.den_phong_khach"]
save_all_house_config(cfg)
st2 = get_house_status_summary()
print("House status 2 (light.den_phong_khach excluded):", st2)
assert st2["total_on_lights"] == 0
assert st2["total_on_fans"] == 1
assert st2["total_on_devices"] == 1
print("✓ Excluded logic verified!")

# Reset config
cfg["excluded_entities"] = []
save_all_house_config(cfg)
print("5. Reset config verified!")
print("ALL TESTS PASSED!")
