"""
NALA SMART HOME - ESP32-S3 Firmware Flash Tool
Tự động nạp file firmware .bin từ kho lưu trữ NAS hoặc thư mục nas_firmware_backup vào màn hình qua cổng COM.
Khắc phục triệt để lỗi màn hình đen do phân vùng otadata cũ của ESP32.
"""

import os
import sys
import subprocess
import glob

ESPTOOL_PATH = os.path.expanduser(r"~\.platformio\packages\tool-esptoolpy\esptool.py")
PYTHON_EXE = sys.executable

def main():
    print("=" * 65)
    print("      NALA SMART HOME - CÔNG CỤ NẠP FIRMWARE ESP32-S3")
    print("=" * 65)

    if not os.path.exists(ESPTOOL_PATH):
        print(f"❌ Không tìm thấy esptool tại: {ESPTOOL_PATH}")
        return

    # Quét các file firmware trong nas_firmware_backup và thư mục gốc
    bin_files = glob.glob("nas_firmware_backup/*.bin") + glob.glob("*.bin")
    if not bin_files:
        print("❌ Không tìm thấy file .bin nào trong nas_firmware_backup!")
        return

    print("\nDanh sách các bản firmware đã tải về:")
    for i, f in enumerate(bin_files):
        size_mb = round(os.path.getsize(f) / (1024 * 1024), 2)
        print(f" [{i+1}] {f} ({size_mb} MB)")

    choice = input(f"\nChọn bản firmware muốn nạp (1-{len(bin_files)}) [Mặc định 1]: ").strip()
    idx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(bin_files) else 0
    selected_bin = bin_files[idx]

    port = input("Nhập cổng COM [Mặc định COM20]: ").strip()
    if not port:
        port = "COM20"

    print(f"\n👉 Chuẩn bị nạp file: {selected_bin} vào cổng {port}")
    print("👉 Xóa otadata (0xe000) để đảm bảo ESP32 khởi động chính xác vào phân vùng mới...")

    # Bước 1: Xóa otadata để reset boot partition về app0
    cmd_erase_ota = [
        PYTHON_EXE, ESPTOOL_PATH,
        "--chip", "esp32s3",
        "-p", port,
        "-b", "921600",
        "erase_region", "0xe000", "0x2000"
    ]
    try:
        subprocess.run(cmd_erase_ota, check=True)
    except Exception as e:
        print(f"⚠️ Cảnh báo xóa otadata: {e}")

    # Bước 2: Nạp firmware vào 0x10000
    print("\n👉 Đang nạp firmware vào flash (offset 0x10000)...")
    cmd_flash = [
        PYTHON_EXE, ESPTOOL_PATH,
        "--chip", "esp32s3",
        "-p", port,
        "-b", "921600",
        "write_flash",
        "0x10000", selected_bin
    ]
    try:
        subprocess.run(cmd_flash, check=True)
        print("\n" + "=" * 65)
        print("🎉 NẠP FIRMWARE THÀNH CÔNG! ESP32 ĐANG KHỞI ĐỘNG LẠI.")
        print("=" * 65)
    except Exception as e:
        print(f"\n❌ Lỗi khi nạp: {e}")

if __name__ == "__main__":
    main()
