import re

with open('server_nas_hub/app/voiceprint_manager.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update enroll signature
old_enroll = '''    def enroll(self, speaker_name: str, pcm_bytes: bytes, sample_rate: int = 16000) -> Tuple[bool, str]:
        """Đăng ký vân giọng đơn."""
        return self.enroll_multi(speaker_name, [pcm_bytes], sample_rate)'''

new_enroll = '''    def enroll(self, speaker_name: str, pcm_bytes: bytes, sample_rate: int = 16000, description: str = "") -> Tuple[bool, str]:
        """Đăng ký vân giọng đơn kèm mô tả vai trò."""
        return self.enroll_multi(speaker_name, [pcm_bytes], sample_rate=sample_rate, description=description)'''

assert old_enroll in code, "old_enroll not found"
code = code.replace(old_enroll, new_enroll, 1)

# 2. Update enroll_multi signature and meta handling
old_enroll_multi_start = '''    def enroll_multi(self, speaker_name: str, pcm_list: List[bytes], sample_rate: int = 16000) -> Tuple[bool, str]:'''
new_enroll_multi_start = '''    def enroll_multi(self, speaker_name: str, pcm_list: List[bytes], sample_rate: int = 16000, description: str = "") -> Tuple[bool, str]:'''

assert old_enroll_multi_start in code, "old_enroll_multi_start not found"
code = code.replace(old_enroll_multi_start, new_enroll_multi_start, 1)

old_meta_read = '''        # Nếu đã có vector cũ và muốn gộp thêm
        meta_path = os.path.join(self.storage_dir, f"{speaker_name}.json")
        filepath = os.path.join(self.storage_dir, f"{speaker_name}.npy")
        prev_samples_count = 0
        if os.path.isfile(meta_path) and os.path.isfile(filepath):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    old_meta = json.load(f)
                    prev_samples_count = int(old_meta.get("samples_count", 1))
            except Exception:
                prev_samples_count = 1'''

new_meta_read = '''        # Nếu đã có vector cũ và muốn gộp thêm
        meta_path = os.path.join(self.storage_dir, f"{speaker_name}.json")
        filepath = os.path.join(self.storage_dir, f"{speaker_name}.npy")
        prev_samples_count = 0
        prev_desc = ""
        if os.path.isfile(meta_path) and os.path.isfile(filepath):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    old_meta = json.load(f)
                    prev_samples_count = int(old_meta.get("samples_count", 1))
                    prev_desc = old_meta.get("description", "")
            except Exception:
                prev_samples_count = 1'''

assert old_meta_read in code, "old_meta_read not found"
code = code.replace(old_meta_read, new_meta_read, 1)

old_meta_write = '''            # Lưu metadata số mẫu
            total_samples = len(valid_embs)
            meta = {
                "name": speaker_name,
                "samples_count": total_samples,
                "last_updated": time.time()
            }'''

new_meta_write = '''            # Lưu metadata số mẫu và mô tả vai trò
            total_samples = len(valid_embs)
            final_desc = (description or prev_desc or "").strip()
            meta = {
                "name": speaker_name,
                "description": final_desc,
                "samples_count": total_samples,
                "last_updated": time.time()
            }'''

assert old_meta_write in code, "old_meta_write not found"
code = code.replace(old_meta_write, new_meta_write, 1)

# 3. Update list_speakers to include description
old_list_speakers = '''            res.append({
                "name": spk,
                "samples_count": samples_count,
                "last_updated": mtime,
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)) if mtime > 0 else "Chưa rõ",
                "dim": self.dim
            })'''

new_list_speakers = '''            desc = ""
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        desc = json.load(f).get("description", "")
                except Exception:
                    pass
            res.append({
                "name": spk,
                "description": desc,
                "samples_count": samples_count,
                "last_updated": mtime,
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)) if mtime > 0 else "Chưa rõ",
                "dim": self.dim
            })'''

assert old_list_speakers in code, "old_list_speakers not found"
code = code.replace(old_list_speakers, new_list_speakers, 1)

# 4. Add get_speaker_info method
get_speaker_info_method = '''
    def get_speaker_info(self, speaker_name: str) -> Dict[str, Any]:
        """Lấy thông tin chi tiết (tên, vai trò, số mẫu) của một người dùng."""
        meta_path = os.path.join(self.storage_dir, f"{speaker_name}.json")
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"name": speaker_name, "description": "", "samples_count": 1}
'''

idx_single = code.find('# Singleton instance toàn cục')
assert idx_single != -1, "singleton comment not found"
code = code[:idx_single] + get_speaker_info_method + "\n" + code[idx_single:]

with open('server_nas_hub/app/voiceprint_manager.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully patched server_nas_hub/app/voiceprint_manager.py!")
