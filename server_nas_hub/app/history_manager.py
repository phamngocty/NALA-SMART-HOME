"""
NALA SMART HOME - Voice & Intercom History Manager
Manages STT text, AI responses, and audio recordings with scheduled retention cleanup.
"""

import os
import io
import time
import json
import wave
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger("HistoryManager")

class HistoryManager:
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.path.dirname(__file__)
        self.base_dir = base_dir
        self.history_file = os.path.join(base_dir, "history.json")
        self.settings_file = os.path.join(base_dir, "history_settings.json")
        self.recordings_dir = os.path.join(base_dir, "recordings")

        os.makedirs(self.recordings_dir, exist_ok=True)
        self.records: List[Dict] = []
        self.settings = {"retention_days": 7} # Mặc định tự xóa sau 7 ngày

        self.load_settings()
        self.load_history()
        self.cleanup()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                logger.error("Error loading history settings: %s", e)

    def save_settings(self):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving history settings: %s", e)

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
                    logger.info("Loaded %d history records", len(self.records))
            except Exception as e:
                logger.error("Error loading history file: %s", e)
                self.records = []
        else:
            self.records = []

    def save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error saving history file: %s", e)

    def save_pcm_to_wav(self, pcm_data: bytes, file_id: str) -> Optional[str]:
        """Lưu luồng PCM 16kHz 16-bit Mono thành file WAV chuẩn."""
        if not pcm_data or len(pcm_data) < 320: # Nhỏ hơn 10ms thì bỏ qua
            return None
        filename = f"{file_id}.wav"
        filepath = os.path.join(self.recordings_dir, filename)
        try:
            with wave.open(filepath, "wb") as wf:
                wf.setnchannels(1)     # Mono
                wf.setsampwidth(2)     # 16-bit = 2 bytes
                wf.setframerate(16000) # 16kHz
                wf.writeframes(pcm_data)
            return filename
        except Exception as e:
            logger.error("Error saving WAV file %s: %s", filename, e)
            return None

    def add_record(self,
                   device_code: str,
                   room_name: str,
                   session_type: str, # "voice_ai" | "intercom"
                   text: str,
                   response: str = "",
                   pcm_data: Optional[bytes] = None) -> Dict:
        """Thêm một bản ghi lịch sử đàm thoại / giọng nói mới."""
        now_ts = time.time()
        record_id = f"hist_{int(now_ts)}_{uuid.uuid4().hex[:6]}"
        dt_str = datetime.fromtimestamp(now_ts).strftime("%d/%m/%Y %H:%M:%S")

        audio_filename = None
        duration = 0.0
        if pcm_data and len(pcm_data) > 0:
            audio_filename = self.save_pcm_to_wav(pcm_data, record_id)
            duration = round(len(pcm_data) / 32000.0, 1)

        item = {
            "id": record_id,
            "timestamp": now_ts,
            "datetime": dt_str,
            "device_code": device_code,
            "room_name": room_name,
            "type": session_type,
            "text": text,
            "response": response,
            "audio_file": audio_filename,
            "duration": duration
        }

        # Chèn lên đầu danh sách (mới nhất lên trên)
        self.records.insert(0, item)

        # Giữ tối đa 1000 bản ghi trong RAM/file
        if len(self.records) > 1000:
            removed = self.records[1000:]
            self.records = self.records[:1000]
            for r in removed:
                af = r.get("audio_file")
                if af:
                    self._delete_audio_file(af)

        self.save_history()
        return item

    def get_records(self, limit: int = 100, filter_type: Optional[str] = None) -> List[Dict]:
        """Lấy danh sách bản ghi theo giới hạn và bộ lọc loại."""
        res = self.records
        if filter_type:
            res = [r for r in res if r.get("type") == filter_type]
        return res[:limit]

    def get_audio_path(self, filename: str) -> Optional[str]:
        """Lấy đường dẫn tuyệt đối an toàn tới file ghi âm."""
        # Ngăn directory traversal
        clean_name = os.path.basename(filename)
        path = os.path.join(self.recordings_dir, clean_name)
        if os.path.exists(path):
            return path
        return None

    def _delete_audio_file(self, filename: str):
        try:
            path = self.get_audio_path(filename)
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.error("Error removing audio file %s: %s", filename, e)

    def delete_record(self, record_id: str) -> bool:
        """Xóa 1 bản ghi và file audio đi kèm."""
        target = None
        for r in self.records:
            if r.get("id") == record_id:
                target = r
                break
        if target:
            if target.get("audio_file"):
                self._delete_audio_file(target["audio_file"])
            self.records.remove(target)
            self.save_history()
            return True
        return False

    def clear_all(self) -> int:
        """Xóa toàn bộ lịch sử và dọn sạch file trong thư mục recordings."""
        count = len(self.records)
        self.records.clear()
        self.save_history()

        # Dọn sạch các file wav trong thư mục
        try:
            for fname in os.listdir(self.recordings_dir):
                if fname.endswith(".wav"):
                    try:
                        os.remove(os.path.join(self.recordings_dir, fname))
                    except Exception:
                        pass
        except Exception as e:
            logger.error("Error clearing recordings dir: %s", e)

        return count

    def get_settings(self) -> Dict:
        """Trả về cài đặt hiện tại và thống kê dung lượng lưu trữ."""
        total_audio_bytes = 0
        try:
            for f in os.listdir(self.recordings_dir):
                fp = os.path.join(self.recordings_dir, f)
                if os.path.isfile(fp):
                    total_audio_bytes += os.path.getsize(fp)
        except Exception:
            pass

        return {
            "retention_days": self.settings.get("retention_days", 7),
            "total_records": len(self.records),
            "storage_mb": round(total_audio_bytes / (1024.0 * 1024.0), 2)
        }

    def update_settings(self, retention_days: int) -> Dict:
        """Cập nhật số ngày lưu trữ và dọn dẹp ngay lập tức."""
        self.settings["retention_days"] = int(retention_days)
        self.save_settings()
        deleted_count = self.cleanup()
        info = self.get_settings()
        info["deleted_by_cleanup"] = deleted_count
        return info

    def cleanup(self) -> int:
        """Dọn dẹp các bản ghi cũ hơn retention_days. retention_days = 0 nghĩa là giữ mãi."""
        retention_days = self.settings.get("retention_days", 7)
        if retention_days <= 0:
            return 0

        cutoff = time.time() - (retention_days * 86400)
        retained = []
        deleted_count = 0

        for r in self.records:
            if r.get("timestamp", 0) >= cutoff:
                retained.append(r)
            else:
                af = r.get("audio_file")
                if af:
                    self._delete_audio_file(af)
                deleted_count += 1

        if deleted_count > 0:
            self.records = retained
            self.save_history()
            logger.info("Cleaned up %d history records older than %d days", deleted_count, retention_days)

        return deleted_count
