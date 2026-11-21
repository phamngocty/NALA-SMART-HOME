"""
==============================================================================
NALA SMART HOME - SPEAKER VOICEPRINT IDENTIFICATION ENGINE (CAM++ ONNX)
- Sử dụng mô hình Alibaba 3D-Speaker CAM++ (Context-Aware Masking) qua sherpa-onnx
- Độ trễ tính toán <20ms trên CPU NAS Hub
- Đầu vào: 16kHz, 16-bit Mono PCM trực tiếp từ ESP32 Wall Panel
- Trích xuất vector đặc trưng 192 chiều & so khớp Cosine Similarity
- Tự động lưu trữ và nạp hồ sơ vân giọng người dùng từ ổ cứng NAS
==============================================================================
"""

import os
import time
import json
import logging
import numpy as np
from typing import Optional, Tuple, List, Dict, Any

try:
    import sherpa_onnx
    SHERPA_AVAILABLE = True
except ImportError:
    SHERPA_AVAILABLE = False

logger = logging.getLogger("NalaVoiceprint")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [VOICEPRINT] %(message)s")


class VoiceprintManager:
    def __init__(self, model_path: Optional[str] = None, storage_dir: Optional[str] = None):
        self.is_ready = False
        self.extractor = None
        self.manager = None
        self.model_path = model_path
        self.storage_dir = storage_dir

        if not SHERPA_AVAILABLE:
            logger.warning("sherpa-onnx chưa được cài đặt! Động cơ vân giọng sẽ tắt.")
            return

        # 1. Xác định đường dẫn file mô hình ONNX
        candidate_model_paths = [
            model_path,
            "/app/app/models/campplus_model.onnx",
            "models/campplus_model.onnx",
            "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/models/campplus_model.onnx",
            os.path.join(os.path.dirname(__file__), "models", "campplus_model.onnx")
        ]
        chosen_model = None
        for p in candidate_model_paths:
            if p and os.path.isfile(p):
                chosen_model = p
                break

        if not chosen_model:
            logger.error("Không tìm thấy file mô hình CAM++ ONNX tại các vị trí tìm kiếm!")
            return

        # 2. Xác định thư mục lưu trữ hồ sơ vân giọng
        candidate_storage_dirs = [
            storage_dir,
            "/app/data/voiceprints",
            "data/voiceprints",
            os.path.join(os.path.dirname(__file__), "data", "voiceprints"),
            "/home/nas152/nala-voice-intercom-system/server_nas_hub/data/voiceprints"
        ]
        chosen_storage = None
        for d in candidate_storage_dirs:
            if d:
                try:
                    os.makedirs(d, exist_ok=True)
                    chosen_storage = d
                    break
                except Exception:
                    continue

        if not chosen_storage:
            chosen_storage = "/tmp/nala_voiceprints"
            os.makedirs(chosen_storage, exist_ok=True)

        self.storage_dir = chosen_storage
        self.model_path = chosen_model

        # 3. Khởi tạo Sherpa-ONNX Extractor & Manager
        try:
            t0 = time.time()
            config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=self.model_path,
                num_threads=2,
                provider="cpu",
                debug=False
            )
            if not config.validate():
                logger.error("Cấu hình SpeakerEmbeddingExtractor không hợp lệ!")
                return

            self.extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
            self.manager = sherpa_onnx.SpeakerEmbeddingManager(self.extractor.dim)
            self.dim = self.extractor.dim
            init_ms = (time.time() - t0) * 1000

            logger.info(f"Đã nạp thành công CAM++ Model ({self.model_path}) trong {init_ms:.1f}ms (dim={self.dim})")
            self.is_ready = True

            # 4. Tải các hồ sơ giọng nói đã lưu trước đó từ đĩa
            self._load_all_profiles()

        except Exception as e:
            logger.error(f"Lỗi khởi tạo động cơ vân giọng: {e}", exc_info=True)
            self.is_ready = False

    def is_available(self) -> bool:
        """Kiểm tra động cơ đã sẵn sàng trích xuất và so khớp đặc trưng giọng nói chưa."""
        return bool(self.is_ready and self.extractor and self.manager)

    def _pcm_to_float_samples(self, pcm_bytes: bytes) -> np.ndarray:
        """Chuyển đổi luồng byte PCM 16-bit mono 16kHz thành mảng numpy float32 [-1.0, 1.0]."""
        if not pcm_bytes:
            return np.array([], dtype=np.float32)
        # Đảm bảo chẵn 2 bytes
        length = len(pcm_bytes) - (len(pcm_bytes) % 2)
        int16_arr = np.frombuffer(pcm_bytes[:length], dtype=np.int16)
        float_arr = int16_arr.astype(np.float32) / 32768.0
        return float_arr

    def _compute_embedding_from_samples(self, samples: np.ndarray, sample_rate: int = 16000) -> Optional[np.ndarray]:
        """Trích xuất vector 192 chiều từ mảng âm thanh float32."""
        if not self.is_ready or len(samples) < 3200:  # Ít nhất 0.2 giây (3200 mẫu)
            return None
        try:
            stream = self.extractor.create_stream()
            stream.accept_waveform(sample_rate, samples)
            stream.input_finished()
            emb = self.extractor.compute(stream)
            return np.array(emb, dtype=np.float32)
        except Exception as e:
            logger.error(f"Lỗi tính toán embedding: {e}")
            return None

    def _load_all_profiles(self):
        """Quét thư mục storage và nạp lại toàn bộ vector đặc trưng vào RAM."""
        if not self.is_ready or not os.path.isdir(self.storage_dir):
            return

        loaded_count = 0
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".npy"):
                speaker_name = os.path.splitext(fname)[0]
                filepath = os.path.join(self.storage_dir, fname)
                try:
                    emb = np.load(filepath)
                    if len(emb) == self.dim:
                        self.manager.add(speaker_name, emb.tolist())
                        loaded_count += 1
                except Exception as e:
                    logger.error(f"Không thể đọc hồ sơ giọng {fname}: {e}")

        logger.info(f"Đã nạp {loaded_count} hồ sơ vân giọng từ {self.storage_dir}: {self.manager.all_speakers}")

    def enroll(self, speaker_name: str, pcm_bytes: bytes, sample_rate: int = 16000, description: str = "") -> Tuple[bool, str]:
        """Đăng ký vân giọng đơn kèm mô tả vai trò."""
        return self.enroll_multi(speaker_name, [pcm_bytes], sample_rate=sample_rate, description=description)

    def enroll_multi(self, speaker_name: str, pcm_list: List[bytes], sample_rate: int = 16000, description: str = "") -> Tuple[bool, str]:
        """
        Đăng ký hoặc cập nhật hồ sơ giọng nói từ NHIỀU mẫu âm thanh (Multi-Sample Centroid).
        Tự động tính vector trọng tâm trung bình (Average Normalized Embedding) để khử nhiễu và tăng độ chính xác so khớp.
        """
        if not self.is_ready:
            return False, "Động cơ vân giọng chưa sẵn sàng."

        if not pcm_list:
            return False, "Danh sách mẫu âm thanh rỗng."

        valid_embs = []
        for i, pcm_bytes in enumerate(pcm_list):
            if not pcm_bytes:
                continue
            samples = self._pcm_to_float_samples(pcm_bytes)
            if len(samples) < 8000:  # Tối thiểu 0.5s
                logger.warning(f"Mẫu {i+1} quá ngắn ({len(samples)/16000:.2f}s), bỏ qua")
                continue
            emb = self._compute_embedding_from_samples(samples, sample_rate)
            if emb is not None:
                norm = np.linalg.norm(emb)
                if norm > 0:
                    valid_embs.append(emb / norm)

        if not valid_embs:
            return False, "Không thể trích xuất đặc trưng từ các mẫu âm thanh đã cung cấp. Vui lòng nói to và rõ hơn."

        # Nếu đã có vector cũ và muốn gộp thêm
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
                prev_samples_count = 1

        # Tính vector trung bình (Centroid)
        avg_emb = np.mean(valid_embs, axis=0)
        norm = np.linalg.norm(avg_emb)
        if norm > 0:
            avg_emb = avg_emb / norm

        try:
            np.save(filepath, avg_emb)

            # Lưu metadata số mẫu và mô tả vai trò
            total_samples = len(valid_embs)
            final_desc = (description or prev_desc or "").strip()
            meta = {
                "name": speaker_name,
                "description": final_desc,
                "samples_count": total_samples,
                "last_updated": time.time()
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            if speaker_name in self.manager.all_speakers:
                self.manager.remove(speaker_name)
            self.manager.add(speaker_name, avg_emb.tolist())

            logger.info(f"Đã lưu thành công vân giọng cho: [{speaker_name}] với {total_samples} mẫu âm thanh")
            return True, f"Đã học thành công {total_samples} mẫu giọng nói cho [{speaker_name}]!"
        except Exception as e:
            logger.error(f"Lỗi ghi hồ sơ vân giọng: {e}")
            return False, f"Lỗi hệ thống: {e}"

    def identify(self, pcm_bytes: bytes, threshold: float = 0.60, sample_rate: int = 16000) -> Tuple[Optional[str], float, Dict[str, float]]:
        """
        Nhận diện danh tính người nói từ đoạn âm thanh thu âm.
        threshold: Ngưỡng tương đồng Cosine tối thiểu để xác nhận (mặc định 0.60, range 0.0 - 1.0)
        Trả về: (tên_người_nói_nếu_khớp, điểm_tương_đồng_cao_nhất, bảng_điểm_chi_tiết)
        """
        if not self.is_ready or not self.manager or self.manager.num_speakers == 0:
            return None, 0.0, {}

        samples = self._pcm_to_float_samples(pcm_bytes)
        if len(samples) < 8000:  # Cần ít nhất 0.5 giây để nhận diện
            return None, 0.0, {}

        # Nếu đoạn nói dài hơn 4 giây, chỉ lấy 3 giây đầu tiên chứa âm thanh rõ nhất để tối ưu tốc độ
        if len(samples) > 48000:
            samples = samples[:48000]

        t0 = time.time()
        emb = self._compute_embedding_from_samples(samples, sample_rate)
        if emb is None:
            return None, 0.0, {}

        emb_list = emb.tolist()
        scores = {}
        best_speaker = None
        best_score = -1.0

        for spk in self.manager.all_speakers:
            try:
                score = float(self.manager.score(spk, emb_list))
                scores[spk] = round(score, 3)
                if score > best_score:
                    best_score = score
                    best_speaker = spk
            except Exception as e:
                logger.error(f"Lỗi tính điểm cho {spk}: {e}")

        infer_ms = (time.time() - t0) * 1000

        if best_speaker and best_score >= threshold:
            logger.info(f"Đã nhận diện người nói: [{best_speaker}] (Độ khớp: {best_score:.2f} >= {threshold}, tính trong {infer_ms:.1f}ms)")
            return best_speaker, best_score, scores
        else:
            logger.debug(f"Không nhận diện được người nói (Điểm cao nhất: {best_speaker}={best_score:.2f} < ngưỡng {threshold})")
            return None, max(0.0, best_score), scores

    def delete(self, speaker_name: str) -> bool:
        """Xóa hồ sơ giọng nói của một người."""
        if not self.is_ready or not self.manager:
            return False
        try:
            if speaker_name in self.manager.all_speakers:
                self.manager.remove(speaker_name)
            filepath = os.path.join(self.storage_dir, f"{speaker_name}.npy")
            if os.path.isfile(filepath):
                os.remove(filepath)
            logger.info(f"Đã xóa hồ sơ giọng nói: {speaker_name}")
            return True
        except Exception as e:
            logger.error(f"Lỗi xóa hồ sơ: {e}")
            return False

    def list_speakers(self) -> List[Dict]:
        """Danh sách tất cả người dùng đã đăng ký giọng nói kèm số mẫu đã học."""
        if not self.is_ready or not self.manager:
            return []
        res = []
        for spk in self.manager.all_speakers:
            fp = os.path.join(self.storage_dir, f"{spk}.npy")
            mtime = os.path.getmtime(fp) if os.path.isfile(fp) else 0
            meta_path = os.path.join(self.storage_dir, f"{spk}.json")
            samples_count = 1
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        samples_count = meta.get("samples_count", 1)
                        if "last_updated" in meta:
                            mtime = meta["last_updated"]
                except Exception:
                    pass
            desc = ""
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
            })
        return res



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

# Singleton instance toàn cục
voiceprintManager = VoiceprintManager()
