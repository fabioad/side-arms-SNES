#!/usr/bin/env python3
import argparse
import ctypes as C
import hashlib
import os
import random
import shutil
import struct
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from test_snes import Info, ROOT

SDK = Path(os.environ.get("PVSNESLIB_HOME", ROOT.parent / "pvsneslib-sdk-4.6")) / "devkitsnes" / "bin"
OUT = ROOT / "build" / "sa1_probe"
SOURCE = ROOT / "tools" / "sa1_probe.asm"
CURRENT = ROOT / "snes" / "sidearms_md_snes.sfc"
BACKUP = ROOT / "build" / "backups" / "sidearms_md_snes_pre_sa1_565a23b7.sfc"


def collision_cases(seed):
    rng = random.Random(seed)
    enemies = [(rng.randrange(-24, 312), rng.randrange(-16, 224),
                2 * rng.randrange(2, 17), rng.randrange(4, 28)) for _ in range(16)]
    shots = [(rng.randrange(-24, 312), rng.randrange(-16, 224),
              rng.randrange(3, 13), rng.randrange(3, 13)) for _ in range(18)]
    shots[0] = (enemies[0][0], enemies[0][1], 5, 5)
    shots[1] = (enemies[1][0] + enemies[1][2] + 4, enemies[1][1], 4, 4)
    shots[2] = (enemies[2][0] - enemies[2][2] - 4 + 1, enemies[2][1], 4, 4)
    values = [*(v[i] for i in range(4) for v in enemies),
              *(v[i] for i in range(4) for v in shots)]
    inputs = struct.pack("<" + "h" * len(values), *values)
    results = [int(sy > ey - bh - hh and sy < ey + bh + hh and
                   sx > ex - bw - hw and sx < ex + bw + hw)
               for ex, ey, bw, bh in enemies for sx, sy, hw, hh in shots]
    assert len(inputs) == 272 and len(results) == 288 and 0 < sum(results) < 288
    assert results[18 + 1] == 0 and results[2 * 18 + 2] == 1
    return inputs, struct.pack("<" + "H" * len(results), *results)


def checksum(data):
    data[0x7fdc:0x7fe0] = b"\0" * 4
    value = sum(data) + 0x1fe
    data[0x7fdc:0x7fe0] = ((value ^ 0xffff) & 0xffff).to_bytes(2, "little") + (value & 0xffff).to_bytes(2, "little")


def build(repetitions):
    OUT.mkdir(parents=True, exist_ok=True)
    inputs, expected = collision_cases(0x5A1)
    inputs2, expected2 = collision_cases(0x5A2)
    assert expected != expected2
    (OUT / "collision_input.bin").write_bytes(inputs)
    (OUT / "collision_input_2.bin").write_bytes(inputs2)
    obj = OUT / f"probe_{repetitions}.obj"
    rom = OUT / ("sa1_probe.sfc" if repetitions == 1 else f"sa1_probe_{repetitions}.sfc")
    linkfile = OUT / f"linkfile_{repetitions}"
    subprocess.run([str(SDK / "wla-65816"), "-D", f"BATCH_COUNT={repetitions}", "-o", str(obj), str(SOURCE)], cwd=ROOT, check=True)
    linkfile.write_text("[objects]\n" + str(obj) + "\n")
    subprocess.run([str(SDK / "wlalink"), "-d", "-s", str(linkfile), str(rom)], cwd=ROOT, check=True)
    data = bytearray(rom.read_bytes())
    assert len(data) == 1024 * 1024 and data[0x7fd6] == 0x34
    data[0x7fd5] = 0x23
    checksum(data)
    rom.write_bytes(data)
    return rom, data, (expected, expected2)


def run(rom, data, expected, repetitions):
    core = C.CDLL("/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so")
    callbacks = []
    video_frames = []
    pixel_format = [0]
    def set_callback(name, typ, fn):
        cb = typ(fn)
        callbacks.append(cb)
        setter = getattr(core, "retro_set_" + name)
        setter.argtypes = [typ]
        setter(cb)
    def env(cmd, ptr):
        if (cmd & 0xffff) == 47:
            C.cast(ptr, C.POINTER(C.c_uint))[0] = 3
            return True
        if cmd == 17:
            C.cast(ptr, C.POINTER(C.c_bool))[0] = False
            return True
        if cmd == 10:
            pixel_format[0] = C.cast(ptr, C.POINTER(C.c_int))[0]
            return True
        return cmd in (18, 35, 37)
    def video(ptr, width, height, pitch):
        if ptr:
            video_frames[:] = [(C.string_at(ptr, pitch * height), width, height, pitch)]
    set_callback("environment", C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p), env)
    set_callback("video_refresh", C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t), video)
    set_callback("audio_sample", C.CFUNCTYPE(None, C.c_int16, C.c_int16), lambda *a: None)
    set_callback("audio_sample_batch", C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t), lambda p, n: n)
    set_callback("input_poll", C.CFUNCTYPE(None), lambda: None)
    set_callback("input_state", C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint), lambda *a: 0)
    core.retro_init()
    buffer = C.create_string_buffer(bytes(data))
    info = Info(str(rom).encode(), C.cast(buffer, C.c_void_p), len(data), None)
    core.retro_load_game.argtypes = [C.POINTER(Info)]
    core.retro_load_game.restype = C.c_bool
    assert core.retro_load_game(C.byref(info)), "SA-1 ROM rejected by emulator"
    core.retro_get_memory_data.argtypes = [C.c_uint]
    core.retro_get_memory_data.restype = C.c_void_p
    ram = (C.c_uint8 * 131072).from_address(core.retro_get_memory_data(2))
    for frame in range(120):
        core.retro_run()
        if ram[0x2000] in (0xa5, 0xee):
            break
    assert ram[0x2000] == 0xa5, f"SA-1 handshake failed: status={ram[0x2000]:02x}"
    cpu_results = bytes(ram[0x2100:0x2340])
    sa1_results = bytes(ram[0x2340:0x2580])
    cpu_results2 = bytes(ram[0x27c0:0x2a00])
    sa1_results2 = bytes(ram[0x2580:0x27c0])
    assert cpu_results == expected[0], "SNES first collision results differ from reference"
    assert sa1_results == expected[0], "SA-1 first collision results differ from reference"
    assert cpu_results2 == expected[1], "SNES second collision results differ from reference"
    assert sa1_results2 == expected[1], "SA-1 second collision results differ from reference"
    for _ in range(4):
        core.retro_run()
    assert video_frames, "Probe produced no video frame"
    pixels, width, height, pitch = video_frames[0]
    stride = 4 if pixel_format[0] == 1 else 2
    colours = {pixels[y * pitch + x * stride:y * pitch + (x + 1) * stride]
               for y in range(height) for x in range(width)}
    assert len(colours) >= 2, "Probe booted but showed a blank screen"
    raw = np.frombuffer(pixels, np.uint8).reshape(height, pitch)
    if pixel_format[0] == 1:
        rgb = raw[:, :width * 4].reshape(height, width, 4)[:, :, [2, 1, 0]]
    else:
        values = raw[:, :width * 2].copy().view(np.uint16).reshape(height, width)
        red = (values >> (11 if pixel_format[0] == 2 else 10)) & 31
        green = (values >> 5) & (63 if pixel_format[0] == 2 else 31)
        blue = values & 31
        rgb = np.stack((red * 255 // 31, green * 255 // (63 if pixel_format[0] == 2 else 31),
                        blue * 255 // 31), axis=2).astype(np.uint8)
    background = rgb[0, 0]
    assert background[1] > background[0] and background[1] > background[2], "Probe success screen is not green"
    assert np.count_nonzero(np.all(rgb[90:108, 90:160] != background, axis=2)) >= 50, "SA-1 OK text is missing"
    if repetitions == 1:
        Image.fromarray(rgb).save(OUT / "sa1_probe.png")
    print(f"PASS: SNES CPU and SA-1 agree on two distinct {repetitions} × 288 collision batches")


def benchmark(rom, expected, repetitions):
    if not shutil.which("mesen"):
        raise RuntimeError("Mesen is required for cycle-aware SA-1 benchmark")
    result = OUT / f"mesen_result_{repetitions}.txt"
    env = dict(os.environ, SA1_PROBE_RESULT=str(result))
    process = subprocess.run(["mesen", "--testRunner", str(rom), str(ROOT / "tools/sa1_probe_mesen.lua")],
                             cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=60, check=True)
    lines = result.read_text().splitlines()
    if len(lines) != 30:
        raise AssertionError(f"Unexpected Mesen result: {process.stdout}\n{lines[:26]}")
    values = dict(line.split("=", 1) for line in lines[:26])
    assert int(values["status"]) == 0xa5, f"Mesen SA-1 handshake failed: {process.stdout}"
    for actual, reference in zip(lines[26:], (expected[0], expected[0], expected[1], expected[1])):
        assert bytes.fromhex(actual) == reference, "Mesen collision results differ from reference"
    def timestamp(prefix, i):
        scanline = int(values[f"{prefix}v{i}"])
        nmi = int(values[f"{prefix}f{i}"])
        return 262 * (nmi - (scanline >= 225)) + scanline
    ticks = [timestamp("", i) for i in range(6)]
    second = [timestamp("second_", i) for i in range(6)]
    copy_in, cpu, gap, sa1, copy_out = (b - a for a, b in zip(ticks, ticks[1:]))
    second_copy, second_cpu, second_setup, second_sa1, second_out = (b - a for a, b in zip(second, second[1:]))
    assert all(v >= 0 for v in (copy_in, cpu, gap, sa1, copy_out, second_copy, second_cpu, second_setup, second_sa1, second_out)), (ticks, second)
    print(f"Mesen {repetitions} batch(es): input {copy_in}, SNES CPU compute {cpu}, "
          f"setup {gap}, SA-1 release+wait {sa1}, output {copy_out} scanlines; "
          f"second input {second_copy}, CPU compute {second_cpu}, setup {second_setup}, "
          f"SA-1 request+wait {second_sa1}, output {second_out} scanlines")
    return copy_in, cpu, sa1, copy_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    before = hashlib.sha256(CURRENT.read_bytes()).hexdigest()
    backup_hash = hashlib.sha256(BACKUP.read_bytes()).hexdigest()
    assert backup_hash == "565a23b701dff77092ca3d141158a7bbc83a421c7978507c650ce69c3fd6de81", "SA-1 backup is not the preserved ROM"
    rom, data, expected = build(1)
    run(rom, data, expected, 1)
    if args.benchmark:
        one = benchmark(rom, expected, 1)
        rom_four, data_four, expected_four = build(4)
        run(rom_four, data_four, expected_four, 4)
        four = benchmark(rom_four, expected_four, 4)
        print(f"Mesen SNES CPU/SA-1 compute+handshake: {one[1] / one[2]:.2f}x (1 batch), "
              f"{four[1] / four[2]:.2f}x (4 batches); "
              f"with input/output transfers: {one[1] / (one[0] + one[2] + one[3]):.2f}x (1 batch)")
    assert hashlib.sha256(CURRENT.read_bytes()).hexdigest() == before
    print(f"Current ROM unchanged: {before}; preserved backup: {backup_hash}")
