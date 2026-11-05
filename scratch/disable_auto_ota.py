import re

with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r'(\s+)# Tự động đẩy lệnh cập nhật OTA.*?logger\.info\("Auto-triggered OTA update.*?\)'

replacement = r'\1# KHONG tu dong cuong buc OTA khi ket noi de tranh vong lap downgrade / freeze cam ung\n\1logger.info("Panel [%s] connected with firmware %s (Auto-OTA disabled)", code, fw_ver)'

new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
print(f"Substitutions made: {count}")
assert count == 1, "Failed to match auto-OTA block!"

with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(new_text)

print("Successfully disabled auto-OTA in server_nas_hub/app/main_ws_server.py!")
