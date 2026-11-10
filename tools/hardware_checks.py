"""Compare the emulated OBJ VRAM cache with the exact converted ROM patterns."""
from test_snes import ROOT

def wait_cache_commit(r):
    # A prepared frame with no queued uploads is also safe to inspect.
    # Fast updates may finish entirely between two emulator video callbacks.
    for _ in range(200):
        if r.read('native_phase',1) in (1,4) and r.read('queue_count')==0:return
        r.run(1)
    raise AssertionError('Could not sample committed VRAM caches')

def check_obj_cache(r):
    # Phase 1 precedes this frame's sprite-cache writes; the previous batch
    # has already been committed to VRAM, so RAM metadata and VRAM agree.
    wait_cache_commit(r)
    v=r.snapshot_block(b'VRA');checked={'cells':0,'composites':0,'largest_source_offset':0}
    for big,slots in ((False,48),(True,12)):
        prefix='spr_big' if big else 'spr_bank'
        index=(ROOT/f'snes/res/{prefix}_index.bin').read_bytes()
        patterns=(ROOT/f'snes/res/{prefix}.bin').read_bytes()
        keys='native_big_keys' if big else 'tccs_src/sprites.asm_keys'
        for slot in range(slots):
            key=r.read(keys,2,slot*2)
            if key==65535:continue
            n=int.from_bytes(index[key*2:key*2+2],'little')&32767
            if not n:continue # runtime remap fallback is a separate path
            size=512 if big else 128;off=(n-1)*size;expected=patterns[off:off+size]
            if big:
                t=192+(slot//4)*64+(slot%4)*4
                actual=b''.join(v[0xc000+(t+y*16)*32:0xc000+(t+y*16)*32+128] for y in range(4))
                checked['composites']+=1
            else:
                t=(slot//8)*32+(slot%8)*2
                actual=b''.join(v[0xc000+(t+delta)*32:0xc000+(t+delta+1)*32] for delta in (0,16,1,17))
                checked['cells']+=1
            assert actual==expected,f'OBJ VRAM differs from ROM: {prefix} key {key:04x}, slot {slot}, offset {off:x}'
            checked['largest_source_offset']=max(checked['largest_source_offset'],off)
    assert checked['cells']+checked['composites']>0,'No OBJ patterns checked'
    return checked

def check_bg_cache(r):
    wait_cache_commit(r)
    v=r.snapshot_block(b'VRA');zone=r.read('tccs_src/background.asm_zone_id')
    patterns=(ROOT/f'snes/res/zone{zone}_tiles.bin').read_bytes();checked=0;largest=0
    for slot in range(47):
        key=r.read('native_bg_keys',2,slot*2)
        if key==65535 or (key+1)*512>len(patterns):continue # extra wheel frames use another source
        assert v[0x200+slot*512:0x200+(slot+1)*512]==patterns[key*512:(key+1)*512],f'BG VRAM mismatch in zone {zone}, meta {key}, slot {slot}'
        checked+=1;largest=max(largest,key*512)
    a=r.addr('native_bg_map')&0x1ffff
    assert v[0x7000:0x8000]==bytes(r.ram[a:a+4096]),'Scenery map DMA differs from shadow map'
    assert checked,'No scenery patterns checked'
    return {'zone':zone,'metatiles':checked,'largest_source_offset':largest,'map_matches':True}
