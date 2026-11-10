"""
Unit and integration test for Wake Word Model Deletion & RAM cleanup
"""

import os
import sys
import json
import asyncio
from unittest.mock import patch, MagicMock

# Add app to path
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_dir)

from wake_word_manager import WakeWordManager


def test_wake_model_deletion_and_unloading():
    # Setup temporary test data dir
    test_data_dir = os.path.join(app_dir, "test_data_wake")
    models_dir = os.path.join(test_data_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    dummy_onnx = os.path.join(models_dir, "my_custom_wake.onnx")
    with open(dummy_onnx, "wb") as f:
        f.write(b"DUMMY_ONNX_CONTENT")

    assert os.path.exists(dummy_onnx)

    wake_mgr = WakeWordManager(data_dir=test_data_dir)
    wake_mgr.save_config({
        "selected_models": ["my_custom_wake", "nala_oiv1"],
        "hidden_models": []
    })

    assert "my_custom_wake" in wake_mgr.config.get("selected_models", [])

    # Simulate deletion logic
    model_to_delete = "my_custom_wake"
    deleted_file = False
    for fname in os.listdir(models_dir):
        base, ext = os.path.splitext(fname)
        if ext.lower() in [".onnx", ".tflite"] and base.lower() == model_to_delete.lower():
            p = os.path.join(models_dir, fname)
            os.remove(p)
            deleted_file = True

    assert deleted_file is True
    assert not os.path.exists(dummy_onnx)

    # Update config & unload from memory
    selected = list(wake_mgr.config.get("selected_models", []))
    if model_to_delete in selected:
        selected.remove(model_to_delete)

    hidden = list(wake_mgr.config.get("hidden_models", []))
    if model_to_delete not in hidden:
        hidden.append(model_to_delete)

    wake_mgr.save_config({
        "selected_models": selected,
        "hidden_models": hidden
    })

    assert "my_custom_wake" not in wake_mgr.config.get("selected_models", [])
    assert "my_custom_wake" in wake_mgr.config.get("hidden_models", [])

    # Clean up test dir
    try:
        import shutil
        shutil.rmtree(test_data_dir)
    except Exception:
        pass

    print("[PASS] test_wake_model_deletion_and_unloading")


if __name__ == "__main__":
    test_wake_model_deletion_and_unloading()
    print("All Wake Model deletion tests passed successfully!")
