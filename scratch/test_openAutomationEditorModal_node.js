function testOpenEditor() {
    try {
        const roomSelect = { innerHTML: '', appendChild: () => {} };
        const seenRooms = new Set();
        for (const [code, dev] of Object.entries(devices_db || {})) {
            const rName = dev.room_name || `Phòng ${code}`;
        }
    } catch (e) {
        console.error("CRASH IN openAutomationEditorModal:", e.name, e.message);
    }
}

testOpenEditor();
