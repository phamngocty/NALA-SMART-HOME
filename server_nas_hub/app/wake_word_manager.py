"""
NALA SMART HOME - MULTI-DEVICE WAKE WORD & SPATIAL ARBITRATION MANAGER
Coordinates OpenWakeWord on NAS, RMS Energy calculation, and Multi-Room Spatial Arbitration.
Ensures that among 6+ wall panels, only the panel closest to the speaker wakes up.
"""

import os
import json
import time
import math
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
import numpy as np

logger = logging.getLogger("WakeWordManager")

class SpatialArbitrationSession:
    def __init__(self, arbitration_id: str, window_ms: int = 300):
        self.arbitration_id = arbitration_id
        self.window_ms = window_ms
        self.start_time = time.time()
        self.candidates: List[Dict[str, Any]] = []
        self.is_resolved = False

class WakeWordManager:
    def __init__(self, data_dir: Optional[str] = None, on_winner_callback: Optional[Callable] = None, on_suppress_callback: Optional[Callable] = None):
        self.on_winner_callback = on_winner_callback
        self.on_suppress_callback = on_suppress_callback

        if data_dir:
            self.data_dir = data_dir
        else:
            candidates = [
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
                os.path.join(os.path.dirname(__file__), "data"),
                "/app/data"
            ]
            self.data_dir = next((c for c in candidates if os.path.exists(c)), candidates[0])

        os.makedirs(self.data_dir, exist_ok=True)
        self.config_file = os.path.join(self.data_dir, "wake_config.json")
        self.config = self._load_config()

        self.oww_model = None
        self._init_model()

        # Per-device state
        self.device_buffers: Dict[str, bytearray] = {}
        self.device_last_rms: Dict[str, float] = {}

        # Spatial Arbitration state
        self.active_arbitration: Optional[SpatialArbitrationSession] = None
        self._arbitration_lock = asyncio.Lock()

    def _load_config(self) -> Dict[str, Any]:
        default_cfg = {
            "global_enabled": True,
            "selected_model": "hey_jarvis", # "hey_jarvis", "alexa"
            "threshold": 0.5,
            "arbitration_window_ms": 300,
            "panel_settings": {} # device_id: {"wake_enabled": bool, "sensitivity": 0.5}
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    default_cfg.update(saved)
            except Exception as e:
                logger.error("Error reading %s: %s", self.config_file, e)
        return default_cfg

    def save_config(self, new_cfg: Dict[str, Any]) -> bool:
        try:
            self.config.update(new_cfg)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("Saved Wake Word configuration to %s", self.config_file)
            return True
        except Exception as e:
            logger.error("Failed to save Wake Word config: %s", e)
            return False

    def _init_model(self):
        try:
            import openwakeword
            from openwakeword.model import Model
            selected = self.config.get("selected_model", "hey_jarvis")
            models_to_load = [selected]
            if "alexa" not in models_to_load:
                models_to_load.append("alexa")
            self.oww_model = Model(wakeword_models=models_to_load)
            logger.info("OpenWakeWord engine initialized with models: %s", models_to_load)
        except Exception as e:
            logger.warning("Failed to initialize OpenWakeWord model: %s", e)
            self.oww_model = None

    def calculate_rms(self, pcm_data: bytes) -> float:
        """Tính cường độ âm lượng RMS (0.0 đến 100.0) từ dữ liệu PCM 16-bit Mono."""
        if not pcm_data or len(pcm_data) < 2:
            return 0.0
        try:
            samples = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32)
            if len(samples) == 0:
                return 0.0
            rms = math.sqrt(np.mean(samples ** 2))
            # Chuẩn hóa về thang điểm 0 - 100 dB tương đối
            if rms > 0:
                rms_db = 20 * math.log10(rms / 32768.0) + 100.0
                return max(0.0, min(100.0, rms_db))
        except Exception:
            pass
        return 0.0

    async def feed_audio_chunk(self, device_id: str, pcm_chunk: bytes) -> Optional[Dict[str, Any]]:
        """
        Nạp một chunk âm thanh 16kHz 16-bit Mono (từ ESP32) vào bộ đệm và chạy suy luận.
        Nếu phát hiện Wake Word, tự động đưa vào quy trình Phân Xử Không Gian (Spatial Arbitration).
        """
        if not self.config.get("global_enabled", True):
            return None

        # Kiểm tra xem màn hình phòng này có bật tính năng Wake Word không
        panel_cfg = self.config.get("panel_settings", {}).get(device_id, {})
        if not panel_cfg.get("wake_enabled", True):
            return None

        if device_id not in self.device_buffers:
            self.device_buffers[device_id] = bytearray()

        self.device_buffers[device_id].extend(pcm_chunk)
        rms = self.calculate_rms(pcm_chunk)
        self.device_last_rms[device_id] = rms

        # OpenWakeWord cần các khối 1280 mẫu (80ms = 2560 bytes)
        FRAME_BYTES = 2560
        if len(self.device_buffers[device_id]) < FRAME_BYTES:
            return None

        frame_data = bytes(self.device_buffers[device_id][:FRAME_BYTES])
        self.device_buffers[device_id] = self.device_buffers[device_id][FRAME_BYTES:]

        if not self.oww_model:
            return None

        try:
            audio_array = np.frombuffer(frame_data, dtype=np.int16)
            preds = self.oww_model.predict(audio_array)

            target_model = self.config.get("selected_model", "hey_jarvis")
            threshold = panel_cfg.get("sensitivity", self.config.get("threshold", 0.5))

            score = 0.0
            matched_key = None
            for k, s in preds.items():
                if target_model in k.lower() or k.lower() in target_model:
                    if s > score:
                        score = float(s)
                        matched_key = k

            if score >= threshold:
                logger.info("Wake Word DETECTED from Panel [%s]! Model: %s, Score: %.3f, RMS: %.1fdB",
                            device_id, matched_key, score, rms)

                wake_candidate = {
                    "device_id": device_id,
                    "model": matched_key,
                    "score": score,
                    "rms": rms,
                    "timestamp": time.time()
                }

                # Đưa vào cửa sổ Phân Xử Không Gian (Spatial Arbitration)
                await self._submit_to_arbitration(wake_candidate)
                return wake_candidate

        except Exception as e:
            logger.error("Error predicting wake word for %s: %s", device_id, e)

        return None

    async def _submit_to_arbitration(self, candidate: Dict[str, Any]):
        """Gộp các ứng viên cùng phát hiện Wake Word trong cửa sổ 300ms để chọn ra 1 phòng chiến thắng."""
        async with self._arbitration_lock:
            if self.active_arbitration is None or self.active_arbitration.is_resolved:
                # Khởi tạo phiên phân xử mới
                window_ms = self.config.get("arbitration_window_ms", 300)
                session = SpatialArbitrationSession(
                    arbitration_id=f"arb_{int(time.time()*1000)}",
                    window_ms=window_ms
                )
                session.candidates.append(candidate)
                self.active_arbitration = session
                # Tạo task chạy nền đợi 300ms rồi chốt kết quả
                asyncio.create_task(self._resolve_arbitration_task(session))
            else:
                # Phiên đang mở, thêm ứng viên từ phòng khác vào danh sách so tài
                self.active_arbitration.candidates.append(candidate)
                logger.info("Added candidate [%s] (RMS: %.1fdB) to ongoing arbitration %s",
                            candidate["device_id"], candidate["rms"], self.active_arbitration.arbitration_id)

    async def _resolve_arbitration_task(self, session: SpatialArbitrationSession):
        # Đợi hết cửa sổ thời gian (ví dụ 300ms)
        await asyncio.sleep(session.window_ms / 1000.0)

        async with self._arbitration_lock:
            session.is_resolved = True
            if not session.candidates:
                return

            # Tiêu chí chọn Winner: Điểm kết hợp giữa Cường độ âm lượng RMS và Độ tin cậy Score
            # Điểm = RMS (0..100) * 0.7 + Score (0..1) * 30
            def rank_func(c):
                return (c["rms"] * 0.7) + (c["score"] * 30.0)

            sorted_candidates = sorted(session.candidates, key=rank_func, reverse=True)
            winner = sorted_candidates[0]
            winning_id = winner["device_id"]

            logger.info("SPATIAL ARBITRATION RESOLVED! Winner: [%s] (RMS: %.1fdB, Score: %.3f) out of %d candidates",
                        winning_id, winner["rms"], winner["score"], len(session.candidates))

            # 1. Báo cho phòng chiến thắng thức dậy
            if self.on_winner_callback:
                asyncio.create_task(self.on_winner_callback(winning_id, winner))

            # 2. Báo cho các phòng thua cuộc tiếp tục ngủ (chống dội âm / echo)
            if self.on_suppress_callback:
                for c in sorted_candidates[1:]:
                    if c["device_id"] != winning_id:
                        asyncio.create_task(self.on_suppress_callback(c["device_id"], c))
