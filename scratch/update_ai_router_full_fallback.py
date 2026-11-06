import os
import sys

def main():
    target_file = os.path.abspath("server_nas_hub/app/ai_agent_router.py")
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    cut_pattern = "    async def process_intent("
    idx = content.find(cut_pattern)
    if idx == -1:
        print("ERROR: Could not find 'async def process_intent(' in ai_agent_router.py")
        sys.exit(1)

    prefix = content[:idx]

    new_code = '''    async def _try_local_rule_fallback(self, user_text: str, context_room: str = "") -> Optional[str]:
        """Dự phòng offline nội bộ qua Home Assistant khi toàn bộ Cloud AI bị đứt mạng hoặc quá tải."""
        if not user_text or not self.ha_bridge:
            return None
        t = user_text.lower().strip()

        is_turn_on = any(w in t for w in ["bật", "mở", "khởi động", "set", "chỉnh"])
        is_turn_off = any(w in t for w in ["tắt", "đóng", "ngắt", "dừng"])
        if not is_turn_on and not is_turn_off:
            return None

        action = "turn_on" if is_turn_on else "turn_off"
        action_name = "bật" if is_turn_on else "tắt"

        target_domain = ""
        if any(w in t for w in ["máy lạnh", "điều hòa", "ac"]):
            target_domain = "climate"
        elif any(w in t for w in ["đèn", "ánh sáng", "led"]):
            target_domain = "light"
        elif any(w in t for w in ["quạt", "fan"]):
            target_domain = "fan"
        elif any(w in t for w in ["công tắc", "ổ cắm"]):
            target_domain = "switch"

        matched_eid = None
        matched_name = None
        room_lower = (context_room or "").lower()

        for eid, state_obj in self.ha_bridge.states.items():
            domain = eid.split(".")[0]
            if target_domain and domain != target_domain:
                continue
            attrs = state_obj.get("attributes", {})
            friendly_name = attrs.get("friendly_name", "").lower()

            if room_lower and room_lower in t:
                if room_lower in friendly_name or room_lower in eid.lower():
                    matched_eid = eid
                    matched_name = attrs.get("friendly_name", eid)
                    break
            elif target_domain:
                if room_lower and (room_lower in friendly_name or room_lower in eid.lower()):
                    matched_eid = eid
                    matched_name = attrs.get("friendly_name", eid)
                    break
                elif not matched_eid:
                    matched_eid = eid
                    matched_name = attrs.get("friendly_name", eid)

        if matched_eid:
            domain = matched_eid.split(".")[0]
            try:
                if domain == "climate":
                    if is_turn_off:
                        await self.ha_bridge.call_service("climate", "set_hvac_mode", entity_id=matched_eid, service_data={"hvac_mode": "off"})
                    else:
                        await self.ha_bridge.call_service("climate", "set_hvac_mode", entity_id=matched_eid, service_data={"hvac_mode": "cool"})
                else:
                    await self.ha_bridge.call_service(domain, action, entity_id=matched_eid)
                return f"Đã {action_name} {matched_name or matched_eid} theo lệnh dự phòng nội bộ."
            except Exception as ex:
                logger.error("Local rule execution error for %s: %s", matched_eid, ex)

        return None

    async def process_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None) -> str:
        """Xử lý giọng nói người dùng, kết hợp Fast-Rule, Multi-AI Function Calling và Cơ chế Tự Động Dự Phòng (Failover/Fallback)."""
        if not user_text:
            return "Tôi không nghe thấy gì cả."

        lower_text = user_text.lower().strip()

        # 1. FAST-PATH RULE BASED (<20ms) cho các lệnh thường gặp
        if any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"]):
            res = await self.ha_bridge.master_turn_off_all()
            cnt = res.get("turned_off_count", 0)
            return f"Đã tắt {cnt} thiết bị trong nhà cho bạn."

        # 2. Xây dựng danh sách ứng viên Provider theo thứ tự ưu tiên (Primary -> Fallbacks)
        preferred = model_preference or self.config.get("active_provider", "gemini")
        auto_fallback = self.config.get("auto_fallback", True)

        candidates = []
        if self.config.get(preferred, {}).get("api_key"):
            candidates.append(preferred)

        if auto_fallback:
            for alt in ["groq", "deepseek", "gemini", "openrouter", "custom"]:
                if alt != preferred and self.config.get(alt, {}).get("api_key"):
                    candidates.append(alt)

        if not candidates:
            local_res = await self._try_local_rule_fallback(user_text, context_room)
            if local_res:
                return local_res
            return f"Tôi đã nghe: '{user_text}', nhưng hệ thống chưa được cài đặt API Key AI khả dụng."

        device_ctx = self._build_device_context()
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx,
            current_room=context_room or "Không xác định"
        )

        last_error_desc = ""

        for prov_idx, prov in enumerate(candidates):
            prov_cfg = self.config.get(prov, {})
            api_key = prov_cfg.get("api_key", "")
            model = prov_cfg.get("model", "")
            base_url = prov_cfg.get("base_url", "")

            logger.info("Processing intent with [%s] (Candidate %d/%d, model: %s)...",
                        prov, prov_idx + 1, len(candidates), model)

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    if prov == "gemini":
                        norm_mod = normalize_gemini_model(model)
                        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:generateContent"
                        headers = {
                            "x-goog-api-key": api_key,
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                            "tools": [{"function_declarations": self._get_ha_tools_schema_gemini()}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 150}
                        }
                        res = await client.post(endpoint, headers=headers, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            candidate = data.get("candidates", [{}])[0]
                            parts = candidate.get("content", {}).get("parts", [])

                            confirmations = []
                            text_replies = []
                            for part in parts:
                                if "functionCall" in part:
                                    fn = part["functionCall"]
                                    res_msg = await self.execute_tool(fn.get("name", ""), fn.get("args", {}))
                                    confirmations.append(res_msg)
                                elif "text" in part:
                                    text_replies.append(part["text"].strip())

                            if confirmations:
                                return " ".join(confirmations)
                            if text_replies:
                                return " ".join(text_replies)
                        else:
                            last_error_desc = f"Gemini HTTP {res.status_code}"
                            logger.warning("Gemini API error %d: %s. Auto-falling back to next provider...",
                                           res.status_code, res.text[:120])
                            continue

                    else:
                        if prov == "groq":
                            endpoint = "https://api.groq.com/openai/v1/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "llama-3.3-70b-versatile"
                        elif prov == "deepseek":
                            endpoint = "https://api.deepseek.com/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "deepseek-flash"
                        elif prov == "openrouter":
                            endpoint = "https://openrouter.ai/api/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://nalasmarthome.local",
                                "X-Title": "NALA Smart Home Hub"
                            }
                            use_model = model or "google/gemini-2.0-flash-exp:free"
                        else:
                            endpoint = f"{base_url.rstrip('/')}/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model

                        payload = {
                            "model": use_model,
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": user_text}
                            ],
                            "tools": self._get_ha_tools_schema_openai(),
                            "tool_choice": "auto",
                            "max_tokens": 150,
                            "temperature": 0.4
                        }
                        if prov == "deepseek":
                            payload["thinking"] = {"type": "disabled"}

                        res = await client.post(endpoint, headers=headers, json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            msg = data["choices"][0]["message"]
                            tool_calls = msg.get("tool_calls", [])
                            if tool_calls:
                                confirmations = []
                                for tc in tool_calls:
                                    func = tc.get("function", {})
                                    fn_name = func.get("name", "")
                                    raw_args = func.get("arguments", "{}")
                                    try:
                                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                                    except Exception:
                                        args = {}
                                    res_msg = await self.execute_tool(fn_name, args)
                                    confirmations.append(res_msg)
                                if confirmations:
                                    return " ".join(confirmations)
                                return "Đã thực hiện yêu cầu cho bạn."

                            content = msg.get("content", "").strip()
                            if content:
                                return content
                        else:
                            last_error_desc = f"{prov} HTTP {res.status_code}"
                            logger.warning("Provider '%s' error %d: %s. Auto-falling back...",
                                           prov, res.status_code, res.text[:120])
                            continue

            except Exception as e:
                last_error_desc = str(e)
                logger.warning("Exception communicating with AI Provider '%s': %s. Auto-falling back...", prov, e)
                continue

        logger.error("All AI providers failed (%s). Triggering offline local rule fallback...", last_error_desc)
        local_res = await self._try_local_rule_fallback(user_text, context_room)
        if local_res:
            return local_res

        return f"Xin lỗi, các máy chủ AI đều đang bận ({last_error_desc}). Vui lòng thử lại sau ít giây."

    async def stream_intent(self, user_text: str, context_room: str = "", model_preference: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream kết quả đối thoại thời gian thực từng token với cơ chế Tự Động Dự Phòng (Failover / Fallback)."""
        if not user_text or not user_text.strip():
            yield "Tôi không nghe thấy gì cả."
            return

        lower_text = user_text.lower().strip()

        # 1. Fast-Path Rule Based (<20ms) cho các lệnh thường gặp
        if any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"]):
            res = await self.ha_bridge.master_turn_off_all()
            cnt = res.get("turned_off_count", 0)
            msg = f"Đã tắt toàn bộ {cnt} thiết bị trong nhà cho bạn."
            for word in msg.split(" "):
                yield word + " "
                await asyncio.sleep(0.03)
            return

        # 2. Xây dựng danh sách ứng viên Provider theo thứ tự ưu tiên (Primary -> Fallbacks)
        preferred = model_preference or self.config.get("active_provider", "gemini")
        auto_fallback = self.config.get("auto_fallback", True)

        candidates = []
        if self.config.get(preferred, {}).get("api_key"):
            candidates.append(preferred)

        if auto_fallback:
            for alt in ["groq", "deepseek", "gemini", "openrouter", "custom"]:
                if alt != preferred and self.config.get(alt, {}).get("api_key"):
                    candidates.append(alt)

        if not candidates:
            local_res = await self._try_local_rule_fallback(user_text, context_room)
            if local_res:
                for word in local_res.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.03)
                return
            msg = f"Tôi đã nghe: '{user_text}', nhưng hệ thống chưa có API Key AI khả dụng."
            for word in msg.split(" "):
                yield word + " "
                await asyncio.sleep(0.03)
            return

        device_ctx = self._build_device_context()
        system_instruction = SYSTEM_PROMPT_TEMPLATE.format(
            device_context=device_ctx,
            current_room=context_room or "Không xác định"
        )

        completed_successfully = False
        last_error_msg = ""

        for prov_idx, prov in enumerate(candidates):
            prov_cfg = self.config.get(prov, {})
            api_key = prov_cfg.get("api_key", "")
            model = prov_cfg.get("model", "")
            base_url = prov_cfg.get("base_url", "")

            logger.info("Attempting AI stream with [%s] (Candidate %d/%d, model: %s)...",
                        prov, prov_idx + 1, len(candidates), model)

            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    if prov != "gemini":
                        if prov == "groq":
                            endpoint = "https://api.groq.com/openai/v1/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "llama-3.3-70b-versatile"
                        elif prov == "deepseek":
                            endpoint = "https://api.deepseek.com/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model or "deepseek-flash"
                        elif prov == "openrouter":
                            endpoint = "https://openrouter.ai/api/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "HTTP-Referer": "https://nalasmarthome.local",
                                "X-Title": "NALA Smart Home Hub"
                            }
                            use_model = model or "google/gemini-2.0-flash-exp:free"
                        else:
                            endpoint = f"{base_url.rstrip('/')}/chat/completions"
                            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                            use_model = model

                        payload = {
                            "model": use_model,
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": user_text}
                            ],
                            "tools": self._get_ha_tools_schema_openai(),
                            "tool_choice": "auto",
                            "stream": True,
                            "max_tokens": 200,
                            "temperature": 0.3
                        }
                        if prov == "deepseek":
                            payload["thinking"] = {"type": "disabled"}

                        accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}
                        has_text = False

                        async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                            if response.status_code != 200:
                                err_body = await response.aread()
                                last_error_msg = f"{prov} HTTP {response.status_code}"
                                logger.warning("Provider '%s' returned HTTP %d: %s. Auto-falling back...",
                                               prov, response.status_code, err_body[:100].decode('utf-8', errors='replace'))
                                continue

                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break

                                try:
                                    chunk_json = json.loads(data_str)
                                    choices = chunk_json.get("choices", [])
                                    if not choices:
                                        continue
                                    delta = choices[0].get("delta", {})

                                    if "tool_calls" in delta and delta["tool_calls"]:
                                        for tc in delta["tool_calls"]:
                                            idx = tc.get("index", 0)
                                            if idx not in accumulated_tool_calls:
                                                accumulated_tool_calls[idx] = {
                                                    "name": tc.get("function", {}).get("name", ""),
                                                    "args": ""
                                                }
                                            fn_data = tc.get("function", {})
                                            if "name" in fn_data and fn_data["name"]:
                                                accumulated_tool_calls[idx]["name"] = fn_data["name"]
                                            if "arguments" in fn_data and fn_data["arguments"]:
                                                accumulated_tool_calls[idx]["args"] += fn_data["arguments"]

                                    content_piece = delta.get("content", "")
                                    if content_piece:
                                        has_text = True
                                        yield content_piece

                                except Exception:
                                    continue

                        if accumulated_tool_calls:
                            confirmations = []
                            for idx, call in accumulated_tool_calls.items():
                                fn_name = call.get("name", "")
                                raw_args = call.get("args", "{}")
                                try:
                                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                                except Exception:
                                    args = {}
                                res_msg = await self.execute_tool(fn_name, args)
                                confirmations.append(res_msg)

                            final_msg = " ".join(confirmations) if confirmations else "Đã thực hiện xong cho bạn."
                            if has_text:
                                yield " " + final_msg
                            else:
                                for word in final_msg.split(" "):
                                    yield word + " "
                                    await asyncio.sleep(0.03)

                        completed_successfully = True
                        break

                    else:
                        norm_mod = normalize_gemini_model(model)
                        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{norm_mod}:streamGenerateContent?alt=sse"
                        headers = {
                            "x-goog-api-key": api_key,
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "system_instruction": {"parts": [{"text": system_instruction}]},
                            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                            "tools": [{"function_declarations": self._get_ha_tools_schema_gemini()}],
                            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 200}
                        }

                        async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                            if response.status_code != 200:
                                err_body = await response.aread()
                                last_error_msg = f"Gemini HTTP {response.status_code}"
                                logger.warning("Gemini returned HTTP %d: %s. Auto-falling back to next provider...",
                                               response.status_code, err_body[:100].decode('utf-8', errors='replace'))
                                continue

                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data: "):
                                    continue
                                try:
                                    chunk_json = json.loads(line[6:])
                                    candidates_chunk = chunk_json.get("candidates", [])
                                    if not candidates_chunk:
                                        continue
                                    parts = candidates_chunk[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        if "text" in p and p["text"]:
                                            yield p["text"]
                                        elif "functionCall" in p:
                                            fn = p["functionCall"]
                                            res_msg = await self.execute_tool(fn.get("name", ""), fn.get("args", {}))
                                            for word in res_msg.split(" "):
                                                yield word + " "
                                                await asyncio.sleep(0.03)
                                except Exception:
                                    continue

                        completed_successfully = True
                        break

            except Exception as e:
                last_error_msg = str(e)
                logger.warning("Exception with provider '%s': %s. Auto-falling back...", prov, e)
                continue

        if not completed_successfully:
            logger.error("All AI providers failed (%s). Triggering offline local rule fallback...", last_error_msg)
            local_res = await self._try_local_rule_fallback(user_text, context_room)
            if local_res:
                for word in local_res.split(" "):
                    yield word + " "
                    await asyncio.sleep(0.03)
                return
            yield f"Các máy chủ AI đều đang bận ({last_error_msg}). Vui lòng thử lại sau ít giây."
'''

    full_updated_content = prefix + new_code
    with open(target_file, "w", encoding="utf-8", newline="") as f:
        f.write(full_updated_content)

    print("SUCCESS: Updated server_nas_hub/app/ai_agent_router.py with Auto-Failover/Rollback for both process_intent and stream_intent!")

if __name__ == "__main__":
    main()
