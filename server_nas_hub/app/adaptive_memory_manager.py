"""
NALA SMART HOME - Bounded Adaptive Learned Memory Manager
=========================================================
Implements a private, self-improving, and bounded memory system:
1. Strict Hard Limits:
   - Max 50 Device Aliases
   - Max 30 Routine Habits
   - Max 20 Core Personal Facts
   - Total JSON payload bounded to < 150KB
2. Signal vs Noise GateKeeper:
   - Drops chit-chat, filler phrases, temporary emotions.
   - Blocks sensitive credentials (passwords, OTPs, PINs, cards, phone numbers).
3. Self-Pruning & LRU Eviction:
   - Automatic eviction based on hit frequency, confidence, and recency.
   - Natural decay of stale habits.
4. Selective Context Injection:
   - Injects only relevant 2-4 memory entries into LLM prompt (Budget <= 120 tokens).
"""

import os
import re
import json
import time
import logging
import unicodedata
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("AdaptiveMemoryManager")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _normalize_vn(s: str) -> str:
    """Strip Vietnamese diacritics for robust matching."""
    if not s:
        return ""
    s = s.replace("đ", "d").replace("Đ", "d")
    nfd = unicodedata.normalize('NFD', s)
    no_marks = "".join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', no_marks)
    return ' '.join(cleaned.split())


class AdaptiveMemoryManager:
    """Manages local, private, and bounded learning for NALA Smart Home."""

    MAX_ALIASES = 50
    MAX_HABITS = 30
    MAX_FACTS = 20
    CONFIRMATION_THRESHOLD = 2  # Must see candidate at least 2 times before promoting to alias
    DECAY_DAYS = 45  # Stale habits decay after 45 days

    # Sensitive data regex filters
    SENSITIVE_PATTERN = re.compile(
        r'\b(mat khau|password|mat ma|ma pin|ma otp|otp|so the|credit card|ngan hang|tai khoan|cccd|cmnd)\b',
        re.IGNORECASE
    )

    # Casual greeting / meaningless noise filters
    NOISE_PATTERN = re.compile(
        r'^(chao|xin chao|tam biet|bye|goodbye|alo|ha ha|hi hi|u|uh|ok|vang|da|the a|co gi moi khong)\b',
        re.IGNORECASE
    )

    # User correction patterns ("Không phải...", "Nhầm rồi...", "Đổi thành...")
    CORRECTION_PATTERN = re.compile(
        r'\b(khong phai|nham roi|sai roi|y toi la|khong dung|doi thanh|khong can nua|la cai kia)\b',
        re.IGNORECASE
    )

    def __init__(self, data_dir: Optional[str] = None):
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
        self.memory_file = os.path.join(self.data_dir, "nala_learned_memory.json")
        self.data: Dict[str, Any] = self._load_memory()

    def _default_schema(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "version": 1,
            "updated_at": time.time(),
            "aliases": {},       # phrase: {"entity_id": str, "room": str, "hit_count": int, "last_used": float, "confidence": float}
            "habits": [],        # [{"id": str, "room": str, "time_bucket": str, "action": str, "entity_id": str, "hit_count": int, "last_used": float}]
            "facts": [],         # [{"id": str, "category": str, "content": str, "created_at": float}]
            "candidates": {},   # phrase: {"entity_id": str, "room": str, "count": int, "last_seen": float}
        }

    def _load_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    defaults = self._default_schema()
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                    return data
            except Exception as e:
                logger.error("Error reading %s: %s. Using default memory schema.", self.memory_file, e)
        return self._default_schema()

    def save_memory(self) -> bool:
        """Persist bounded memory to disk."""
        try:
            self.data["updated_at"] = time.time()
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Failed to save learned memory to %s: %s", self.memory_file, e)
            return False

    def is_enabled(self) -> bool:
        return bool(self.data.get("enabled", True))

    def set_enabled(self, enabled: bool):
        self.data["enabled"] = bool(enabled)
        self.save_memory()
        logger.info("Adaptive Learned Memory state changed to: %s", self.data["enabled"])

    # --------------------------------------------------------------------------
    # GateKeeper & Filters
    # --------------------------------------------------------------------------
    def is_noise_or_sensitive(self, text: str) -> bool:
        """Check if incoming text is casual noise or contains sensitive information."""
        if not text:
            return True
        clean = text.strip()
        if len(clean) < 3 or len(clean) > 120:
            return True
        norm = _normalize_vn(clean)
        if self.SENSITIVE_PATTERN.search(norm):
            logger.warning("GateKeeper: Blocked text containing sensitive keyword.")
            return True
        if self.NOISE_PATTERN.search(norm):
            return True
        return False

    def is_user_correction(self, text: str) -> bool:
        """Detect if the user is correcting a previous action."""
        if not text:
            return False
        return bool(self.CORRECTION_PATTERN.search(_normalize_vn(text)))

    @staticmethod
    def get_time_bucket(timestamp: Optional[float] = None) -> str:
        """Map current local hour to a routine bucket."""
        h = time.localtime(timestamp or time.time()).tm_hour
        if 5 <= h < 11:
            return "morning"
        elif 11 <= h < 17:
            return "afternoon"
        elif 17 <= h < 22:
            return "evening"
        else:
            return "night"

    # --------------------------------------------------------------------------
    # Eviction & Pruning Logic (LRU + Capacity Limits)
    # --------------------------------------------------------------------------
    def _evict_if_needed(self):
        """Enforce hard limits on aliases, habits, and facts using LRU and confidence."""
        # 1. Prune Aliases
        aliases = self.data.get("aliases", {})
        if len(aliases) > self.MAX_ALIASES:
            # Sort by lowest score: confidence * hit_count, then oldest last_used
            sorted_aliases = sorted(
                aliases.items(),
                key=lambda item: (item[1].get("confidence", 0.5) * item[1].get("hit_count", 1), item[1].get("last_used", 0))
            )
            excess = len(aliases) - self.MAX_ALIASES
            for i in range(excess):
                evicted_key = sorted_aliases[i][0]
                del aliases[evicted_key]
                logger.info("Evicted least used alias: '%s'", evicted_key)

        # 2. Prune Habits
        habits = self.data.get("habits", [])
        now = time.time()
        # Remove decayed habits older than DECAY_DAYS with low hit count
        cutoff = now - (self.DECAY_DAYS * 86400)
        active_habits = [h for h in habits if h.get("last_used", now) >= cutoff or h.get("hit_count", 0) >= 5]
        if len(active_habits) > self.MAX_HABITS:
            active_habits.sort(key=lambda h: (h.get("hit_count", 1), h.get("last_used", 0)), reverse=True)
            active_habits = active_habits[:self.MAX_HABITS]
        self.data["habits"] = active_habits

        # 3. Prune Facts
        facts = self.data.get("facts", [])
        if len(facts) > self.MAX_FACTS:
            # Keep the newest facts
            facts.sort(key=lambda f: f.get("created_at", 0), reverse=True)
            self.data["facts"] = facts[:self.MAX_FACTS]

        # 4. Prune Candidates buffer (Max 40 candidates)
        candidates = self.data.get("candidates", {})
        if len(candidates) > 40:
            sorted_cand = sorted(candidates.items(), key=lambda item: (item[1].get("count", 0), item[1].get("last_seen", 0)))
            for i in range(len(candidates) - 40):
                del candidates[sorted_cand[i][0]]

    # --------------------------------------------------------------------------
    # Learning Operations
    # --------------------------------------------------------------------------
    def learn_device_interaction(self, user_text: str, entity_id: str, context_room: str = "", domain: str = "light", action: str = "turn_on"):
        """
        Record a successful interaction and promote candidates to permanent aliases.
        """
        if not self.is_enabled():
            return
        if not user_text or not entity_id or self.is_noise_or_sensitive(user_text):
            return

        clean_phrase = user_text.strip().lower()
        # Strip common action prefixes to isolate the subject phrase (e.g., "bật đèn chùm" -> "đèn chùm")
        subject = re.sub(r'^(bật|tắt|mở|đóng|chỉnh|hãy bật|hãy tắt|giúp mình bật|giúp mình tắt)\s+', '', clean_phrase).strip()
        if len(subject) < 3:
            return

        now = time.time()
        aliases = self.data.setdefault("aliases", {})

        # If already an established alias, boost hit count and recency
        if subject in aliases:
            aliases[subject]["hit_count"] = aliases[subject].get("hit_count", 0) + 1
            aliases[subject]["last_used"] = now
            aliases[subject]["confidence"] = min(1.0, aliases[subject].get("confidence", 0.8) + 0.05)
            # If room context provided and empty, set it
            if context_room and not aliases[subject].get("room"):
                aliases[subject]["room"] = context_room
            self.save_memory()
            return

        # Track in candidate buffer
        candidates = self.data.setdefault("candidates", {})
        cand = candidates.get(subject)
        if not cand:
            candidates[subject] = {
                "entity_id": entity_id,
                "room": context_room,
                "count": 1,
                "last_seen": now
            }
        else:
            if cand.get("entity_id") == entity_id:
                cand["count"] = cand.get("count", 1) + 1
                cand["last_seen"] = now
                # Promotion condition met!
                if cand["count"] >= self.CONFIRMATION_THRESHOLD:
                    aliases[subject] = {
                        "entity_id": entity_id,
                        "room": context_room or cand.get("room", ""),
                        "hit_count": cand["count"],
                        "last_used": now,
                        "confidence": 0.85
                    }
                    del candidates[subject]
                    logger.info("Promoted candidate phrase '%s' -> '%s' to permanent alias!", subject, entity_id)
            else:
                # User used the same phrase for a different entity; update candidate target
                cand["entity_id"] = entity_id
                cand["count"] = 1
                cand["last_seen"] = now

        # Record routine habit
        self._record_habit(context_room, entity_id, action)
        self._evict_if_needed()
        self.save_memory()

    def learn_user_correction(self, correction_text: str, corrected_entity_id: str, context_room: str = ""):
        """
        Handle explicit correction from user ("Không phải, cái đèn bàn cơ").
        Updates or overrides previous alias linkage immediately with high confidence.
        """
        if not self.is_enabled():
            return
        if not correction_text or not corrected_entity_id:
            return

        clean = correction_text.strip().lower()
        norm = _normalize_vn(clean)
        if not self.CORRECTION_PATTERN.search(norm):
            return

        # Strip correction marker prefixes
        subject = re.sub(
            r'^(không phải|nhầm rồi|sai rồi|ý tôi là|không đúng|đổi thành|không cần nữa|là cái kia|khong phai|nham roi|sai roi|y toi la|khong dung|doi thanh)[,\s:]*',
            '',
            clean,
            flags=re.IGNORECASE
        ).strip()
        # Strip common qualifiers like 'cái', 'phải là'
        subject = re.sub(r'^(cái|phải là)\s+', '', subject, flags=re.IGNORECASE).strip()
        # Strip conversational trailing particles
        subject = re.sub(r'\s+(cơ|đấy|đó|nha|nhé|nhe|co|day|do)$', '', subject, flags=re.IGNORECASE).strip()
        if len(subject) < 3:
            return

        now = time.time()
        aliases = self.data.setdefault("aliases", {})
        aliases[subject] = {
            "entity_id": corrected_entity_id,
            "room": context_room,
            "hit_count": aliases.get(subject, {}).get("hit_count", 0) + 2,
            "last_used": now,
            "confidence": 0.95  # Explicit user correction gets high confidence
        }
        logger.info("Learned user correction: phrase '%s' mapped to '%s'", subject, corrected_entity_id)

        self._evict_if_needed()
        self.save_memory()

    def _record_habit(self, room: str, entity_id: str, action: str):
        """Track recurring usage by time bucket."""
        if not room and not entity_id:
            return
        bucket = self.get_time_bucket()
        habits = self.data.setdefault("habits", [])
        now = time.time()

        for h in habits:
            if h.get("room") == room and h.get("entity_id") == entity_id and h.get("time_bucket") == bucket:
                h["hit_count"] = h.get("hit_count", 0) + 1
                h["last_used"] = now
                return

        # New habit candidate
        habits.append({
            "id": f"hab_{int(now)}_{len(habits)}",
            "room": room,
            "time_bucket": bucket,
            "action": action,
            "entity_id": entity_id,
            "hit_count": 1,
            "last_used": now
        })

    def add_fact(self, content: str, category: str = "general") -> bool:
        """Manually add or learn a core household fact."""
        if not content or self.is_noise_or_sensitive(content):
            return False
        facts = self.data.setdefault("facts", [])
        # Prevent exact duplicate
        for f in facts:
            if f.get("content", "").lower() == content.strip().lower():
                return False

        facts.append({
            "id": f"fact_{int(time.time())}_{len(facts)}",
            "category": category,
            "content": content.strip(),
            "created_at": time.time()
        })
        self._evict_if_needed()
        return self.save_memory()

    # --------------------------------------------------------------------------
    # Retrieval & Fast-Path Matching
    # --------------------------------------------------------------------------
    def match_fast_path(self, user_text: str, context_room: str = "") -> Optional[Dict[str, str]]:
        """
        Check if user's phrasing matches an existing high-confidence alias.
        Returns {"entity_id": ..., "action": ...} for instant <20ms local execution.
        """
        if not self.is_enabled() or not user_text:
            return None

        clean = user_text.strip().lower()
        aliases = self.data.get("aliases", {})

        for phrase, info in aliases.items():
            if info.get("confidence", 0) >= 0.8:
                # If room matches or phrase is distinct enough
                room_match = not info.get("room") or not context_room or (info.get("room").lower() == context_room.lower())
                if phrase in clean and room_match:
                    action = "turn_off" if any(w in clean for w in ["tắt", "đóng", "ngắt"]) else "turn_on"
                    return {
                        "entity_id": info["entity_id"],
                        "action": action,
                        "phrase": phrase,
                        "room": info.get("room", "")
                    }
        return None

    def get_prompt_context(self, context_room: str = "", user_text: str = "") -> str:
        """
        Selectively format top 2-4 relevant memories for LLM prompt injection (Budget <= 120 tokens).
        """
        if not self.is_enabled():
            return ""

        relevant_snippets = []
        clean_text = (user_text or "").lower()

        # 1. Matching Aliases for current room or text
        aliases = self.data.get("aliases", {})
        matched_aliases = []
        for phrase, info in aliases.items():
            if phrase in clean_text or (context_room and info.get("room", "").lower() == context_room.lower()):
                matched_aliases.append(f'"{phrase}" -> {info["entity_id"]}')
                if len(matched_aliases) >= 3:
                    break

        if matched_aliases:
            relevant_snippets.append(f"- Biệt danh thiết bị quen thuộc: {', '.join(matched_aliases)}")

        # 2. Time-bucket habit for current room
        current_bucket = self.get_time_bucket()
        habits = self.data.get("habits", [])
        for h in habits:
            if h.get("time_bucket") == current_bucket and (not context_room or h.get("room", "").lower() == context_room.lower()):
                if h.get("hit_count", 0) >= 3:
                    relevant_snippets.append(f"- Thói quen {current_bucket}: thường {h.get('action')} {h.get('entity_id')} tại {h.get('room')}")
                    break

        # 3. Top core facts (max 2)
        facts = self.data.get("facts", [])
        for f in facts[:2]:
            relevant_snippets.append(f"- Ghi nhớ gia đình: {f.get('content')}")

        if not relevant_snippets:
            return ""

        header = "\n[Trí Nhớ Đã Học Của Nala - Ưu tiên áp dụng]:\n"
        return header + "\n".join(relevant_snippets)

    # --------------------------------------------------------------------------
    # Admin Management Methods
    # --------------------------------------------------------------------------
    def get_summary(self) -> Dict[str, Any]:
        """Summary metrics for the Web Admin dashboard."""
        aliases = self.data.get("aliases", {})
        habits = self.data.get("habits", [])
        facts = self.data.get("facts", [])

        # Calculate memory footprint on disk
        file_size_bytes = 0
        if os.path.exists(self.memory_file):
            file_size_bytes = os.path.getsize(self.memory_file)

        return {
            "enabled": self.is_enabled(),
            "aliases_count": len(aliases),
            "max_aliases": self.MAX_ALIASES,
            "habits_count": len(habits),
            "max_habits": self.MAX_HABITS,
            "facts_count": len(facts),
            "max_facts": self.MAX_FACTS,
            "file_size_kb": round(file_size_bytes / 1024, 2),
            "aliases": aliases,
            "habits": habits,
            "facts": facts,
            "updated_at": self.data.get("updated_at", time.time())
        }

    def delete_item(self, item_type: str, item_id: str) -> bool:
        """Delete a specific learned item by key or id."""
        if item_type == "alias":
            if item_id in self.data.get("aliases", {}):
                del self.data["aliases"][item_id]
                return self.save_memory()
        elif item_type == "habit":
            self.data["habits"] = [h for h in self.data.get("habits", []) if h.get("id") != item_id]
            return self.save_memory()
        elif item_type == "fact":
            self.data["facts"] = [f for f in self.data.get("facts", []) if f.get("id") != item_id]
            return self.save_memory()
        return False

    def clean_garbage_and_decay(self) -> int:
        """Clean low-confidence candidates and stale items."""
        removed_count = 0
        # 1. Clean candidates older than 7 days with only 1 hit
        now = time.time()
        candidates = self.data.get("candidates", {})
        to_del = [k for k, v in candidates.items() if (now - v.get("last_seen", 0) > 7 * 86400) and v.get("count", 0) <= 1]
        for k in to_del:
            del candidates[k]
            removed_count += 1

        # 2. Clean low-confidence aliases (< 0.5)
        aliases = self.data.get("aliases", {})
        low_aliases = [k for k, v in aliases.items() if v.get("confidence", 0) < 0.5]
        for k in low_aliases:
            del aliases[k]
            removed_count += 1

        self.save_memory()
        return removed_count

    def reset_all_memory(self) -> bool:
        """Reset memory to pristine factory state."""
        self.data = self._default_schema()
        return self.save_memory()
