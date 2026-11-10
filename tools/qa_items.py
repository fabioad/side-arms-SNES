#!/usr/bin/env python3
"""Exercise real shot -> carrier drop -> contact pickup -> robot/ring paths.

QA arranges three live stage carriers and their carried letters in a clear lane;
it does not invoke player_apply_item or the debug item-grant command.
"""
from test_snes import Runner, ROOT
import json

r = Runner()
r.logic(5); r.press('START'); r.logic(10); r.press('START'); r.logic(5); r.press('START')
for _ in range(3): r.press('B')
r.logic(500)
r.write('en_dbg_mute', 1, 1)
rows = []
for carrier, (letter, expected) in enumerate((('P', 0x80), ('t', 1), ('A', 6))):
    r.write('players', 255, 1, r.layout['invuln'])
    r.write('players', 60, 2, r.layout['x']); r.write('players', 60, 2, r.layout['y'])
    offset = carrier * 40
    assert r.read('en_big', 1, offset), 'Expected a live stage carrier'
    # Stationary, one-hit carrier, 80 pixels ahead of the player.
    for off, value, size in ((4, 140, 2), (6, 60, 2), (8, 0, 2),
                             (10, 200, 1), (16, 1, 1), (30, ord(letter), 1)):
        r.write('en_big', value, size, offset + off)
    r.logic(4); r.logic(3, ['B']); r.logic(12)
    slots = [i for i in range(8) if r.read('en_item', 1, i * 40)]
    assert len(slots) == 1, ('Carrier drop missing or collected from a distance', letter, slots)
    item_offset = slots[0] * 40
    item = r.read('en_item', 1, item_offset + 17)
    assert item == expected, (letter, item)
    assert r.read('en_item', 2, item_offset + 12), 'Pickup has no visible sprite'
    r.capture('pickup-' + letter)
    x = r.read('en_item', 2, item_offset + 4)
    y = r.read('en_item', 2, item_offset + 6)
    r.write('players', x - 8, 2, r.layout['x'])
    r.write('players', y - 8, 2, r.layout['y']); r.logic(4)
    assert not r.read('en_item', 1, item_offset), 'Pickup did not vanish on contact'
    if letter == 'P': assert r.read('players', 1, 14) == 2, 'POW speed upgrade missing'
    if letter == 't': assert r.read('players', 1, 17) == 1, 'BIT weapon upgrade missing'
    if letter == 'A': assert r.read('combined', 1) == 1, 'Alpha did not trigger combination'
    rows.append({'letter': letter, 'item': item, 'dropped_and_collected': True})
r.logic(300)
assert r.read('combined', 1) == 1 and r.read('combined_hp', 1) == 2
r.logic(4); r.logic(2, ['B'])
partner = r.layout['player_size']
ring = [i for i in range(9) if r.read('players', 1, partner + r.layout['shots'] + i*r.layout['shot_size'] + r.layout['shot_active'])]
assert len(ring) == 8, ('Eight-direction ring missing', ring)
r.capture('super-robot-ring')
assert r.read('native_dma_overflow') == 0
assert r.read('audio_flush_timeouts') == 0
result = {'rom_sha256': r.rom_sha256, 'pickups': rows, 'robot_hp': r.read('combined_hp', 1), 'ring_shots': len(ring)}
(ROOT / 'build/qa/items.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
