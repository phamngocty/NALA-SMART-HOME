"""
Groq Cloud LPU Client with Automatic Model Discovery and Dynamic Rollback / Failover
===================================================================================
Features:
1. Auto-Scan: Queries Groq's `/v1/models` endpoint to detect active models,
   filtering out audio/moderation models (Whisper, Llama-Guard).
2. Intelligent Ranking & Selection: Prioritizes flagship reasoning models,
   ultra-fast lightweight instant models, and MoE models.
3. Automated Rollback & Cooldown:
   - On 429 (Rate Limit / TPM / RPM): Temporarily cools down model and immediately
     rolls back to high-capacity instant fallback models (e.g., llama-3.1-8b-instant).
   - On 404 (Model Decommissioned): Automatically blacklists deprecated model,
     re-scans active registry, and switches to active successor.
   - On 500/503 (LPU Overload / Glitch): Smoothly cascades to alternate model.
4. Full Support for both standard chat completions and real-time streaming (SSE).
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
import httpx

logger = logging.getLogger("GroqFailoverClient")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class GroqFailoverClient:
    """Async Groq Client featuring automated model discovery, health tracking, and cascading rollback."""

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"

    # Default priority ordering if API scan cannot be performed or for ranking candidates:
    # 1. Flagship versatile / reasoning models
    # 2. Fast instant models (massive token limits & high speeds for rollback)
    # 3. Balanced / specialized models
    PRIORITY_RANKS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "deepseek-r1-distill-llama-70b",
        "qwen-2.5-32b",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        cooldown_seconds: float = 60.0,
        cache_ttl_seconds: float = 1800.0,
        default_preferred_model: str = "llama-3.3-70b-versatile",
        client_timeout: float = 15.0,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.cooldown_seconds = cooldown_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.default_preferred_model = default_preferred_model
        self.client_timeout = client_timeout

        # In-memory model cache & health registries
        self._cached_models: Dict[str, Dict[str, Any]] = {}
        self._last_scan_time: float = 0.0
        self._model_cooldowns: Dict[str, float] = {}  # {model_id: expire_timestamp}
        self._blacklisted_models: set = set()  # Permanently deprecated/decommissioned models

    def set_api_key(self, api_key: str):
        """Update API Key at runtime."""
        self.api_key = api_key
        self._cached_models.clear()
        self._last_scan_time = 0.0

    async def scan_and_sync_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Scan available models from Groq Cloud `/models` endpoint.
        Filters out non-chat models (whisper, guard, embedding).
        Caches results with TTL to ensure low latency.
        """
        now = time.time()
        if not force_refresh and self._cached_models and (now - self._last_scan_time < self.cache_ttl_seconds):
            return list(self._cached_models.values())

        if not self.api_key:
            logger.warning("No Groq API Key configured; using default model catalog.")
            return [{"id": m, "active": True} for m in self.PRIORITY_RANKS]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "GroqFailoverClient/1.0"
        }

        try:
            async with httpx.AsyncClient(timeout=self.client_timeout) as client:
                res = await client.get(f"{self.base_url}/models", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    scanned = {}
                    for item in data.get("data", []):
                        m_id = item.get("id", "")
                        is_active = item.get("active", True)

                        # Filter out Whisper audio STT and Guard moderation models
                        lower_id = m_id.lower()
                        if "whisper" in lower_id or "guard" in lower_id or "embed" in lower_id:
                            continue

                        if not is_active or m_id in self._blacklisted_models:
                            continue

                        scanned[m_id] = {
                            "id": m_id,
                            "context_window": item.get("context_window", 8192),
                            "owned_by": item.get("owned_by", "groq"),
                            "active": is_active,
                        }

                    if scanned:
                        self._cached_models = scanned
                        self._last_scan_time = now
                        logger.info("Successfully scanned %d active chat models from Groq Cloud.", len(scanned))
                        return list(self._cached_models.values())
                    else:
                        logger.warning("Scan returned 0 suitable chat models; using priority fallback catalog.")
                else:
                    logger.warning("Groq /models scan failed with HTTP %d: %s", res.status_code, res.text[:120])
        except Exception as e:
            logger.warning("Exception during Groq models scan: %s", e)

        # Fallback if scan fails
        if not self._cached_models:
            return [{"id": m, "active": True} for m in self.PRIORITY_RANKS if m not in self._blacklisted_models]
        return list(self._cached_models.values())

    def get_candidate_models(self, preferred_model: Optional[str] = None) -> List[str]:
        """
        Build an ordered candidate list of models for inference with automatic rollback order.
        Filters out models currently in cooldown or blacklisted.
        """
        now = time.time()
        # Clean expired cooldowns
        expired = [m for m, expiry in self._model_cooldowns.items() if now >= expiry]
        for m in expired:
            del self._model_cooldowns[m]
            logger.info("Model '%s' cooldown period expired; restored to active pool.", m)

        target_preferred = preferred_model or self.default_preferred_model

        # Get available models pool
        if self._cached_models:
            available_set = set(self._cached_models.keys())
        else:
            available_set = set(self.PRIORITY_RANKS)

        available_set = available_set - self._blacklisted_models

        # Candidates ordering
        ordered_candidates: List[str] = []

        # 1. Preferred model if available
        if target_preferred in available_set:
            ordered_candidates.append(target_preferred)

        # 2. Known high-priority models
        for rank_mod in self.PRIORITY_RANKS:
            if rank_mod in available_set and rank_mod not in ordered_candidates:
                ordered_candidates.append(rank_mod)

        # 3. Any other scanned models
        for other_mod in sorted(available_set):
            if other_mod not in ordered_candidates:
                ordered_candidates.append(other_mod)

        # Split into available vs cooling down
        ready_candidates = [m for m in ordered_candidates if m not in self._model_cooldowns]
        cooling_candidates = [m for m in ordered_candidates if m in self._model_cooldowns]

        # Sort cooling candidates by earliest expiry so they act as last-resort fallback
        cooling_candidates.sort(key=lambda m: self._model_cooldowns[m])

        final_queue = ready_candidates + cooling_candidates
        return final_queue or self.PRIORITY_RANKS

    def mark_model_cooldown(self, model_id: str, reason: str = "Rate Limit 429"):
        """Mark a model as temporarily unavailable under cooldown."""
        self._model_cooldowns[model_id] = time.time() + self.cooldown_seconds
        logger.warning("Placed model '%s' on cooldown for %.1fs (Reason: %s).",
                       model_id, self.cooldown_seconds, reason)

    def mark_model_deprecated(self, model_id: str, reason: str = "Decommissioned 404"):
        """Permanently blacklist a model that has been decommissioned or deleted."""
        self._blacklisted_models.add(model_id)
        if model_id in self._cached_models:
            del self._cached_models[model_id]
        if model_id in self._model_cooldowns:
            del self._model_cooldowns[model_id]
        logger.error("Model '%s' blacklisted permanently (Reason: %s).", model_id, reason)

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        preferred_model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.4,
        max_tokens: int = 500,
        **extra_params
    ) -> Dict[str, Any]:
        """
        Execute chat completion with automatic rollback / failover on Groq LPU.
        Iterates through candidate models in priority order until success.
        """
        if not self.api_key:
            raise ValueError("Groq API Key is not configured. Set GROQ_API_KEY environment variable.")

        # Ensure cache is warmed up
        await self.scan_and_sync_models()

        candidates = self.get_candidate_models(preferred_model)
        if not candidates:
            raise RuntimeError("No candidate Groq models available.")

        rollback_history: List[Dict[str, Any]] = []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GroqFailoverClient/1.0"
        }

        endpoint = f"{self.base_url}/chat/completions"

        for idx, model in enumerate(candidates):
            t0 = time.time()
            logger.info("Attempting inference on Groq LPU [Candidate %d/%d: %s]...",
                        idx + 1, len(candidates), model)

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **extra_params
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = tool_choice

            try:
                async with httpx.AsyncClient(timeout=self.client_timeout) as client:
                    res = await client.post(endpoint, headers=headers, json=payload)
                    latency = round((time.time() - t0) * 1000, 1)

                    if res.status_code == 200:
                        data = res.json()
                        # Success! Clear cooldown if it was active
                        self._model_cooldowns.pop(model, None)

                        return {
                            "success": True,
                            "model_used": model,
                            "latency_ms": latency,
                            "rollback_occurred": (idx > 0),
                            "rollback_history": rollback_history,
                            "data": data,
                            "message": data["choices"][0]["message"]
                        }

                    # Handle 429 Rate Limit (RPM / TPM exceeded)
                    elif res.status_code == 429:
                        err_text = res.text[:200]
                        self.mark_model_cooldown(model, reason=f"HTTP 429: {err_text}")
                        rollback_history.append({
                            "model": model,
                            "http_code": 429,
                            "latency_ms": latency,
                            "error": "Rate limit exceeded. Rolling back to fallback model."
                        })
                        continue

                    # Handle 404 Model Decommissioned / Not Found
                    elif res.status_code == 404 or "model_decommissioned" in res.text:
                        err_text = res.text[:200]
                        self.mark_model_deprecated(model, reason=f"HTTP 404 / Decommissioned: {err_text}")
                        rollback_history.append({
                            "model": model,
                            "http_code": 404,
                            "latency_ms": latency,
                            "error": "Model decommissioned or not found. Rolling back."
                        })
                        continue

                    # Handle 500, 502, 503, 504 (Groq LPU cluster glitch or service busy)
                    elif res.status_code in [500, 502, 503, 504]:
                        err_text = res.text[:200]
                        logger.warning("Groq LPU returned HTTP %d on model '%s': %s. Rolling back...",
                                       res.status_code, model, err_text)
                        rollback_history.append({
                            "model": model,
                            "http_code": res.status_code,
                            "latency_ms": latency,
                            "error": f"Groq Server Error {res.status_code}. Rolling back."
                        })
                        continue

                    # Other client errors (400, 401, etc.)
                    else:
                        err_text = res.text[:250]
                        logger.error("Groq unrecoverable client error HTTP %d: %s", res.status_code, err_text)
                        return {
                            "success": False,
                            "model_used": model,
                            "http_code": res.status_code,
                            "error": err_text,
                            "rollback_history": rollback_history
                        }

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                latency = round((time.time() - t0) * 1000, 1)
                logger.warning("Network timeout/error with model '%s' (%s). Rolling back...", model, net_err)
                rollback_history.append({
                    "model": model,
                    "http_code": 0,
                    "latency_ms": latency,
                    "error": str(net_err)
                })
                continue

        # If all candidates exhausted
        return {
            "success": False,
            "error": "All candidate Groq models failed or are on cooldown.",
            "rollback_history": rollback_history
        }

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, Any]],
        preferred_model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.3,
        max_tokens: int = 500,
        **extra_params
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Stream chat completions with real-time rollback.
        Yields (chunk_content, model_name).
        If primary model fails before emitting tokens, it rolls back seamlessly.
        """
        if not self.api_key:
            raise ValueError("Groq API Key is not configured.")

        await self.scan_and_sync_models()
        candidates = self.get_candidate_models(preferred_model)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GroqFailoverClient/1.0"
        }
        endpoint = f"{self.base_url}/chat/completions"

        for idx, model in enumerate(candidates):
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
                **extra_params
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = tool_choice

            try:
                async with httpx.AsyncClient(timeout=self.client_timeout) as client:
                    async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                        if response.status_code == 429:
                            self.mark_model_cooldown(model, "Stream 429 Rate Limit")
                            continue
                        elif response.status_code == 404 or "model_decommissioned" in (await response.aread()).decode('utf-8', 'ignore'):
                            self.mark_model_deprecated(model, "Stream 404 Decommissioned")
                            continue
                        elif response.status_code in [500, 502, 503, 504]:
                            logger.warning("Groq stream HTTP %d on model '%s'. Rolling back...", response.status_code, model)
                            continue
                        elif response.status_code != 200:
                            err_content = (await response.aread()).decode('utf-8', 'ignore')[:150]
                            logger.error("Groq stream failed with HTTP %d: %s", response.status_code, err_content)
                            break

                        # Stream connected successfully; yield tokens
                        self._model_cooldowns.pop(model, None)

                        async for line in response.aiter_lines():
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if not choices:
                                    continue
                                delta = choices[0].get("delta", {})
                                text_piece = delta.get("content", "")
                                if text_piece:
                                    yield text_piece, model
                            except Exception:
                                continue
                        # Completed stream successfully
                        return

            except Exception as e:
                logger.warning("Exception during stream with model '%s': %s. Rolling back...", model, e)
                continue

        logger.error("All candidate models failed during streaming.")
