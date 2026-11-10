#!/usr/bin/env python3
"""Build the one-shot SNESMOD module for the Capcom logo music.

The WAV is the logo sting captured from Street Fighter II (USA) at boot,
downmixed to 16 kHz mono.  It plays as a single non-looping sample; the module
pattern is long enough to cover the splash so it only wraps after the logo has
faded out.
"""
from pathlib import Path
import struct
import wave

ROOT = Path(__file__).resolve().parents[1]
WAV = ROOT / 'tools/capcom_logo.wav'
TEMPLATE = ROOT / 'sidearms_snes/res/pollen8.it'
OUT = ROOT / 'snes/res/capcom.it'
C5SPEED = 16000
ROWS = 64
SPEED = 4
TEMPO = 36                     # keeps the 64-row pattern well past the splash


def read_wav(path):
    w = wave.open(str(path), 'rb')
    assert w.getnchannels() == 1 and w.getsampwidth() == 2
    rate = w.getframerate()
    vals = list(struct.unpack('<%dh' % w.getnframes(), w.readframes(w.getnframes())))
    w.close()
    return rate, vals


def make_sample(name, count):
    hdr = bytearray(80)
    hdr[0:4] = b'IMPS'
    fn = name.encode('ascii')[:12]
    hdr[4:4 + len(fn)] = fn
    hdr[17] = 64                # global volume
    hdr[18] = 0x00              # no loop, 8-bit mono
    hdr[19] = 64                # default volume
    nm = name.encode('ascii')[:26]
    hdr[20:20 + len(nm)] = nm
    hdr[46] = 1                 # signed samples
    struct.pack_into('<I', hdr, 48, count)
    struct.pack_into('<I', hdr, 52, 0)     # loop start
    struct.pack_into('<I', hdr, 56, 0)     # loop end
    struct.pack_into('<I', hdr, 60, C5SPEED)
    return hdr


def make_instrument(template, name):
    ins = bytearray(template)
    nm = name.encode('ascii')[:26]
    ins[32:32 + len(nm)] = nm
    # The pollen8 template has a short volume envelope meant for FM-style
    # notes; this module plays one pre-recorded sample, so keep it open.
    ins[0x18] = 128               # global volume
    ins[0x19] = 32                # default pan centre
    ins[0x14:0x16] = b'\x00\x00'   # fadeout
    ins[0x130] = 0                 # volume envelope off
    ins[0x182] = 0                 # panning envelope off
    ins[0x1D4] = 0                 # pitch envelope off
    for n in range(120):
        ins[64 + n * 2] = n
        ins[64 + n * 2 + 1] = 1           # sample 1
    return ins


def main():
    rate, vals = read_wav(WAV)
    assert rate == C5SPEED, (rate, C5SPEED)
    peak = max(1, max(abs(v) for v in vals))
    gain = 0.85 * 32767.0 / peak
    sample = bytes(max(-128, min(127, int(round(v * gain)) >> 8)) & 0xFF for v in vals)

    tpl = TEMPLATE.read_bytes()
    ordnum, insnum, _, _ = struct.unpack_from('<4H', tpl, 32)
    ins_off = struct.unpack_from('<%dI' % insnum, tpl, 192 + ordnum)
    ins0 = tpl[ins_off[0]:ins_off[0] + 554]

    ordnum, insnum, smpnum, patnum = 2, 1, 1, 1
    hdr = bytearray(192)
    hdr[0:4] = b'IMPM'
    title = b'Capcom logo'
    hdr[4:4 + 26] = title.ljust(26, b'\x00')[:26]
    struct.pack_into('<HHHH', hdr, 32, ordnum, insnum, smpnum, patnum)
    struct.pack_into('<HH', hdr, 40, 0x0888, 0x0888)
    struct.pack_into('<H', hdr, 44, 0x09)     # instrument mode + linear slides
    hdr[48] = 128                            # global volume
    hdr[49] = 128                            # mix volume
    hdr[50] = SPEED
    hdr[51] = TEMPO
    for i in range(64):
        hdr[64 + i] = 32                     # pan centre
        hdr[128 + i] = 64                    # channel volume

    orders = bytes([0, 255])
    # One note at row 0 on channel 1, then 62 empty rows and a note-off on the
    # last row. The trailing event keeps smconv from trimming the pattern, so
    # the module lasts the full splash instead of wrapping mid-logo.
    pattern = bytes([0x81, 0x03, 60, 1, 0]) + b'\x00' * 62 + bytes([0x81, 0x01, 254, 0])
    pat_blob = struct.pack('<HH', len(pattern), ROWS) + b'\x00\x00\x00\x00' + pattern

    ins_table = 192 + ordnum
    smp_table = ins_table + insnum * 4
    pat_table = smp_table + smpnum * 4
    instr_data = pat_table + patnum * 4
    smp_hdr_data = instr_data + insnum * 554
    pat_data = smp_hdr_data + smpnum * 80
    smp_data = pat_data + len(pat_blob)
    smp_data += (-smp_data) % 16

    blob = bytearray(hdr) + orders
    blob += struct.pack('<I', instr_data)
    blob += struct.pack('<I', smp_hdr_data)
    blob += struct.pack('<I', pat_data)
    blob += make_instrument(ins0, 'capcom')
    smp_hdr = make_sample('capcom_logo', len(sample))
    struct.pack_into('<I', smp_hdr, 72, smp_data)
    blob += smp_hdr
    blob += pat_blob
    blob += b'\x00' * (smp_data - len(blob))
    blob += sample

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(blob)
    print('Capcom logo music: %.3f s, %d samples, %d bytes module' %
          (len(vals) / rate, len(vals), len(blob)))


if __name__ == '__main__':
    main()
