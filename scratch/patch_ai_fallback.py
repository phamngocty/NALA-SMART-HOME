import os
import sys

router_path = os.path.abspath('server_nas_hub/app/ai_agent_router.py')
with open(router_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update _load_initial_config
t1 = '''            "stt_provider": "auto",
            "stt_groq_model": "whisper-large-v3-turbo"
        }'''

r1 = '''            "stt_provider": "auto",
            "stt_groq_model": "whisper-large-v3-turbo",
            "auto_fallback": True
        }'''

if t1 in text:
    text = text.replace(t1, r1, 1)
    print("1. Updated _load_initial_config")
elif t1.replace('\n', '\r\n') in text:
    text = text.replace(t1.replace('\n', '\r\n'), r1.replace('\n', '\r\n'), 1)
    print("1. Updated _load_initial_config (CRLF)")
else:
    print("1. t1 not found")

# 2. Update get_safe_config
t2 = '''            "stt_groq_model": self.config.get("stt_groq_model", "whisper-large-v3-turbo"),'''
r2 = '''            "stt_groq_model": self.config.get("stt_groq_model", "whisper-large-v3-turbo"),
            "auto_fallback": self.config.get("auto_fallback", True),'''

if t2 in text:
    text = text.replace(t2, r2, 1)
    print("2. Updated get_safe_config")
elif t2.replace('\n', '\r\n') in text:
    text = text.replace(t2.replace('\n', '\r\n'), r2.replace('\n', '\r\n'), 1)
    print("2. Updated get_safe_config (CRLF)")
else:
    print("2. t2 not found")

# 3. Update save_config
t3 = '''            if "stt_groq_model" in new_data:
                self.config["stt_groq_model"] = new_data["stt_groq_model"]'''

r3 = '''            if "stt_groq_model" in new_data:
                self.config["stt_groq_model"] = new_data["stt_groq_model"]
            if "auto_fallback" in new_data:
                self.config["auto_fallback"] = bool(new_data["auto_fallback"])'''

if t3 in text:
    text = text.replace(t3, r3, 1)
    print("3. Updated save_config")
elif t3.replace('\n', '\r\n') in text:
    text = text.replace(t3.replace('\n', '\r\n'), r3.replace('\n', '\r\n'), 1)
    print("3. Updated save_config (CRLF)")
else:
    print("3. t3 not found")

with open(router_path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Updated config handlers in ai_agent_router.py")
