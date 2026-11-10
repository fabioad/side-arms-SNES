#!/usr/bin/env python3
"""Measure native update cadence and fully black frames during active stage 1."""
from collections import Counter
from test_snes import Runner, ROOT
import json

r = Runner()
r.logic(5); r.press('START'); r.logic(10); r.press('START'); r.logic(5); r.press('START')
for _ in range(3): r.press('B')
r.logic(550)
start = r.read('frame_counter', 4)
phases = Counter()
black = 0
frames = 3000
for _ in range(frames):
    r.write('players', 255, 1, r.layout['invuln'])
    r.run(1)
    phases[r.read('native_phase', 1)] += 1
    black += bool(r.frame.max() == 0)
result = {'rom_sha256': r.rom_sha256, 'video_frames': frames,
          'logic_hz': 60 * (r.read('frame_counter', 4) - start) / frames,
          'black_frames': black, 'phases': dict(phases),
          'forced_blanks': r.read('native_long_blank'),
          'reused_vblanks': r.read('native_vblank_reused'),
          'late_dma': r.read('native_dma_late'),
          'dma_overflow': r.read('native_dma_overflow'),
          'audio_timeouts': r.read('audio_flush_timeouts')}
(ROOT/'build/qa/performance-after.json').write_text(json.dumps(result, indent=2) + '\n')
assert black == 0, 'Gameplay includes fully black video frames'
assert result['dma_overflow'] == 0 and result['audio_timeouts'] == 0
assert result['late_dma'] == 0, 'DMA exceeded VBlank'
assert result['logic_hz'] <= 60, 'Simulation must not run faster than video cadence'
assert result['logic_hz'] >= 30, 'Reference stage-1 workload must reach 30 updates/s'
print(json.dumps(result))
