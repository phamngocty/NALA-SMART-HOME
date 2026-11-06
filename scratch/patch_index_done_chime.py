import os

html_path = os.path.abspath('server_nas_hub/app/static/index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    text = f.read()

is_crlf = '\r\n' in text
nl = '\r\n' if is_crlf else '\n'

target = f'''        }} else if (type === 'ack') {{
            // Ack Chime "Poong!": A5 (880Hz, 50ms) -> E5 (659Hz, 90ms)
            const osc = webAudioCtx.createOscillator();
            const gain = webAudioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(659, now + 0.12);
            gain.gain.setValueAtTime(0.18, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
            osc.connect(gain);
            gain.connect(webAudioCtx.destination);
            osc.start(now);
            osc.stop(now + 0.14);
        }}'''

repl = f'''        }} else if (type === 'ack') {{
            // Ack Chime "Poong!": A5 (880Hz, 50ms) -> E5 (659Hz, 90ms)
            const osc = webAudioCtx.createOscillator();
            const gain = webAudioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(659, now + 0.12);
            gain.gain.setValueAtTime(0.18, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
            osc.connect(gain);
            gain.connect(webAudioCtx.destination);
            osc.start(now);
            osc.stop(now + 0.14);

        }} else if (type === 'done') {{
            // Action Done Chime "Ting!": E6 (1318Hz, 80ms)
            const osc = webAudioCtx.createOscillator();
            const gain = webAudioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(1318, now);
            gain.gain.setValueAtTime(0.22, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.10);
            osc.connect(gain);
            gain.connect(webAudioCtx.destination);
            osc.start(now);
            osc.stop(now + 0.10);
        }}'''

target_norm = target.replace('\n', nl)
repl_norm = repl.replace('\n', nl)

if target_norm in text:
    text = text.replace(target_norm, repl_norm, 1)
    print("Added done chime to index.html")
elif target in text:
    text = text.replace(target, repl, 1)
    print("Added done chime to index.html (LF)")
else:
    print("Target not found in index.html")

with open(html_path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
