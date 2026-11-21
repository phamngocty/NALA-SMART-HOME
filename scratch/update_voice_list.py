with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_snippet = """const XZ_VOICES = [
    { id: 'vi-VN-HoaiMyNeural', name: 'Giọng nữ (Female Voice)', sub: 'Hoài My · Tự nhiên, truyền cảm', rate: '+0%', pitch: '+0Hz', vad: 'normal' },
    { id: 'vi-VN-NamMinhNeural', name: 'giọng nam (Male Voice)', sub: 'Nam Minh · Trầm ấm, đĩnh đạc', rate: '+0%', pitch: '+0Hz', vad: 'normal' },
    { id: 'vi-VN-HoaiMyNeural_young', name: 'cô gái trẻ (Young Girl)', sub: 'Trong trẻo, vui tươi, hoạt bát', rate: '+10%', pitch: '+10Hz', vad: 'fast' },
    { id: 'vi-VN-NamMinhNeural_host', name: 'chủ nhà nam (Male Host)', sub: 'Chững chạc, uy quyền, lịch thiệp', rate: '-5%', pitch: '-10Hz', vad: 'slow' },
    { id: 'vi-VN-NamMinhNeural_young', name: 'chàng trai trẻ (Young Man)', sub: 'Nhanh nhẹn, thân thiện, năng động', rate: '+10%', pitch: '+5Hz', vad: 'normal' },
    { id: 'google_fast', name: 'Thử nghiệm · Google Siêu Tốc (0.15s)', sub: 'Phản xạ tức thì, không độ trễ', rate: '+0%', pitch: '+0Hz', vad: 'fast' }
];"""

new_snippet = """const XZ_VOICES = [
    { id: 'vi-VN-HoaiMyNeural', name: 'Giọng nữ (Female Voice)', sub: 'Hoài My · Tự nhiên, truyền cảm', rate: '+0%', pitch: '+0Hz', vad: 'normal' },
    { id: 'vi-VN-NamMinhNeural', name: 'giọng nam (Male Voice)', sub: 'Nam Minh · Trầm ấm, đĩnh đạc', rate: '+0%', pitch: '+0Hz', vad: 'normal' },
    { id: 'vi-VN-HoaiMyNeural_young', name: 'cô gái trẻ (Young Girl)', sub: 'Trong trẻo, vui tươi, hoạt bát', rate: '+10%', pitch: '+10Hz', vad: 'fast' },
    { id: 'vi-VN-NamMinhNeural_host', name: 'chủ nhà nam (Male Host)', sub: 'Chững chạc, uy quyền, lịch thiệp', rate: '-5%', pitch: '-10Hz', vad: 'slow' },
    { id: 'vi-VN-NamMinhNeural_young', name: 'chàng trai trẻ (Young Man)', sub: 'Nhanh nhẹn, thân thiện, năng động', rate: '+10%', pitch: '+5Hz', vad: 'normal' },
    { id: 'vi-VN-HoaiMyNeural_exp', name: 'Thử nghiệm · Hoài My', sub: 'Edge-TTS Hoài My thử nghiệm', rate: '+5%', pitch: '+2Hz', vad: 'normal' },
    { id: 'google_fast', name: 'Thử nghiệm · Google Siêu Tốc (0.15s)', sub: 'Phản xạ tức thì, không độ trễ', rate: '+0%', pitch: '+0Hz', vad: 'fast' }
];"""

assert old_snippet in content, "Could not find old_snippet in index.html"
content = content.replace(old_snippet, new_snippet)

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added 'Thử nghiệm · Hoài My' to XZ_VOICES in index.html!")
