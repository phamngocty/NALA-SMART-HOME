with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update VoiceprintEnrollRequest
old_req = """class VoiceprintEnrollRequest(BaseModel):
    name: Optional[str] = None
    speaker_name: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_list_base64: Optional[List[str]] = None
    record_id: Optional[str] = None
    filename: Optional[str] = None
    filenames: Optional[List[str]] = None"""

new_req = """class VoiceprintEnrollRequest(BaseModel):
    name: Optional[str] = None
    speaker_name: Optional[str] = None
    description: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_list_base64: Optional[List[str]] = None
    record_id: Optional[str] = None
    filename: Optional[str] = None
    filenames: Optional[List[str]] = None"""

assert old_req in code, "old_req not found"
code = code.replace(old_req, new_req, 1)

# 2. Update enroll_multi call
old_enroll_call = """ok, msg = voiceprintManager.enroll_multi(target_name, pcm_list)"""
new_enroll_call = """ok, msg = voiceprintManager.enroll_multi(target_name, pcm_list, description=req.description or "")"""

assert old_enroll_call in code, "old_enroll_call not found"
code = code.replace(old_enroll_call, new_enroll_call, 1)

# 3. Enrich identified_speaker with description when calling stream_intent
old_harvest = """if best_spk:
                    identified_speaker = best_spk
                    vp_score = best_sc
                    logger.info("[VOICEPRINT] 🎯 Xác thực thành công người nói: %s (score: %.3f)", best_spk, best_sc)"""

new_harvest = """if best_spk:
                    spk_info = voiceprintManager.get_speaker_info(best_spk) if hasattr(voiceprintManager, "get_speaker_info") else {}
                    spk_desc = spk_info.get("description", "")
                    identified_speaker = f"{best_spk} ({spk_desc})" if spk_desc else best_spk
                    vp_score = best_sc
                    logger.info("[VOICEPRINT] 🎯 Xác thực thành công người nói: %s (score: %.3f)", identified_speaker, best_sc)"""

assert old_harvest in code, "old_harvest not found"
code = code.replace(old_harvest, new_harvest, 1)

with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Successfully patched main_ws_server.py for Voiceprint description and enrichment!")
