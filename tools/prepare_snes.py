#!/usr/bin/env python3
"""Stage MD game logic and serialize its generated assets for a native SNES build.

The fork root stays the reference. Hardware modules are replaced in snes/src/.
"""
from pathlib import Path
import re, shutil, hashlib, json,struct
from c89_loops import lower
from build_wheels import build_wheels
from build_home_logo import build_home_logo

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT
DEST = ROOT / 'snes'

def planar(data):
    if len(data) % 32: raise ValueError('unaligned tile blob')
    out = bytearray()
    for start in range(0, len(data), 32):
        tile = data[start:start+32]
        planes = [bytearray() for _ in range(4)]
        for y in range(8):
            for p in range(4):
                v = 0
                for x in range(8):
                    pen = (tile[y*4+x//2] >> (0 if x&1 else 4)) & 15
                    v |= ((pen >> p) & 1) << (7-x)
                planes[p].append(v)
        for a,b in ((0,1),(2,3)):
            for y in range(8): out.extend((planes[a][y],planes[b][y]))
    return bytes(out)

def native_boss_banks():
    """Move the MD boss cache's already-converted patterns into native ROM banks.

    Missing generic-bank pairs otherwise require a costly per-pixel remap on
    the 65816 every time a flashing boss evicts them. Existing pairs stay exact.
    """
    gen=UP/'res/generated'; src=(UP/'src/gen/boss_data.c').read_text()
    def array(name):
        m=re.search(r'\b'+name+r'\[[^\]]*\][^=]*=\s*\{(.*?)\};',src,re.S)
        if not m:raise ValueError('Missing boss data '+name)
        return [int(x,16) for x in re.findall(r'0x([0-9a-fA-F]+)',m[1])]
    def words(name):return list(struct.unpack('>'+str((gen/(name+'.bin')).stat().st_size//2)+'H',(gen/(name+'.bin')).read_bytes()))
    def pack(values):return b''.join(struct.pack('>H',v) for v in values)
    keys=words('spr_bank_keys'); old=(gen/'spr_bank.bin').read_bytes(); index=words('spr_bank_index')
    small={k:(old[i*128:(i+1)*128],index[k]>>15) for i,k in enumerate(keys)}
    oldbig=(gen/'spr_big.bin').read_bytes(); oldidx=words('spr_big_index')
    # build_assets.py records len(big) AFTER appending each 512-byte block,
    # so these indices are one-based, just like spr_bank_index.
    big={k:(oldbig[((v&32767)-1)*512:(v&32767)*512],v>>15)
         for k,v in enumerate(oldidx) if v&32767}
    before=(len(small),len(big));lut=(gen/'sprite_lut.bin').read_bytes()
    bkeys=array('boss_block_keys');data=bytes(array('boss_block_data'))
    assert len(data)==len(bkeys)*512
    for i,key in enumerate(bkeys):
        block=data[i*512:(i+1)*512];pal=lut[256+(key>>11)]&1
        big.setdefault(key,(block,pal))
        parts=(block[:64]+block[128:192],block[256:320]+block[384:448],
               block[64:128]+block[192:256],block[320:384]+block[448:512])
        for add,part in zip((0,1,8,9),parts):small.setdefault(((key&2047)+add)&2047|(key&0xf800),(part,pal))
    skeys=array('boss_small_keys');sdata=bytes(array('boss_small_data'))
    assert len(sdata)==len(skeys)*128
    for i,key in enumerate(skeys):small.setdefault(key,(sdata[i*128:(i+1)*128],lut[256+(key>>11)]&1))
    # Motion scripts name additional animation frames beyond the representative
    # metasprites. Build these once rather than remapping pixels on the 65816.
    motion=(UP/'src/gen/enemy_data.c').read_text().split('const EnemyInit')[0]
    pairs={(int(code),int(col)) for dur,col,dy,dx,code in
           re.findall(r'\{(\d+), (\d+), (-?\d+), (-?\d+), (\d+)\}',motion) if int(dur)}
    pens=(gen/'sprite_pens.bin').read_bytes();pairlut=(gen/'sprite_pair_lut.bin').read_bytes()
    for code,col in sorted(pairs):
        pal=lut[256+col]&1;parts=[]
        for add in (0,1,8,9):
            cell=(code+add)&2047;key=cell|(col<<11)
            raw=pens[cell*128:(cell+1)*128]
            block=bytes(pairlut[col*256+b] for b in raw)
            small.setdefault(key,(block,pal));parts.append(block)
        key=(code&2047)|(col<<11)
        tl,tr,bl,br=parts
        block=b''.join(top[h:h+64]+bot[h:h+64]
                       for top,bot,h in ((tl,bl,0),(tl,bl,64),(tr,br,0),(tr,br,64)))
        big.setdefault(key,(block,pal))
    si=[0]*32768;bi=[0]*32768
    for i,k in enumerate(sorted(small)):si[k]=i+1|(small[k][1]<<15)
    for i,k in enumerate(sorted(big)):bi[k]=i+1|(big[k][1]<<15)
    print('Native prebuilt boss patterns:',len(small)-before[0],'cells,',len(big)-before[1],'composites')
    return {'spr_bank_keys':pack(sorted(small)),'spr_bank':b''.join(small[k][0] for k in sorted(small)),
            'spr_bank_index':pack(si),'spr_big':b''.join(big[k][0] for k in sorted(big)),
            'spr_big_index':pack(bi)},len(small)

def parallax_assets():
    """Eight subpixel vertical phases, with exact source colours in BG3 palettes.

    BG2 uses CGRAM 64..95 so BG3 can combine stars from adjacent source rows.
    Each phase stores the 32 visible columns twice vertically, avoiding wrap tests.
    """
    raw=(UP/'res/generated/star_tiles.bin').read_bytes()
    cells=struct.unpack('>2048H',(UP/'res/generated/star_map.bin').read_bytes())
    palettes=((1,2,3),(1,2,17),(1,3,18),(2,17,18),(17,18,0),(5,6,0))
    patterns=[bytes(16)]; lookup={bytes(16):0}; maps=bytearray()
    for phase in range(8):
        for x in range(4,36):
            column=[]
            for y in range(32):
                pixels=[]
                for yy in range(8):
                    sy=y*8+yy+phase; e=cells[(sy//8%32)*64+x]
                    for xx in range(8):
                        b=raw[(e&2047)*32+(sy&7)*4+xx//2]
                        pen=(b>>(0 if xx&1 else 4))&15
                        pixels.append(pen+((e>>13)&1)*16 if pen else 0)
                colors=set(pixels)-{0}
                p=next(i for i,cs in enumerate(palettes) if colors<=set(cs))
                pens=[palettes[p].index(c)+1 if c else 0 for c in pixels]
                packed=bytes((pens[i]<<4)|pens[i+1] for i in range(0,64,2))
                tile=planar(packed)[:16]
                if tile not in lookup:lookup[tile]=len(patterns);patterns.append(tile)
                column.append(lookup[tile]|(p<<10))
            maps+=struct.pack('<64H',*(column+column))
    assert len(patterns)<=256,'BG3 star phases exceed reserved VRAM'
    far=(UP/'res/generated/zone10_far_tiles.bin').read_bytes()
    # The original cave texture uses only pens 5 and 6, both opaque.
    assert set(v for b in far for v in (b>>4,b&15))=={5,6}
    far=bytes((((b>>4)-4)<<4)|((b&15)-4) for b in far)
    far=b''.join(planar(far[i:i+32])[:16] for i in range(0,len(far),32))
    return {'native_star_phases':bytes(maps),'native_star_tiles':b''.join(patterns),
            'native_far_tiles':far}

def stage():
    for p in ('src/logic', 'inc/gen', 'res'): (DEST/p).mkdir(parents=True,exist_ok=True)
    excluded = {'bg.c','video.c','sprites.c','hud.c','main.c','rom_header.c','cart_mapper.c','palette.c','parallax.c','flow_scene.c'}
    for p in (UP/'inc').rglob('*.h'):
        q=DEST/'inc'/p.relative_to(UP/'inc'); q.parent.mkdir(parents=True,exist_ok=True)
        q.write_text(p.read_text())
    sources = list((UP/'src').glob('*.[ch]')) + list((UP/'src/gen').glob('*.c'))
    inventory=[]
    for p in sources:
        if p.name in excluded: continue
        s=p.read_text()
        s=re.sub(r'__attribute__\s*\(\((?:[^()]|\([^()]*\))*\)\)', '', s)
        s=re.sub(r'^#pragma weak .*$', '', s, flags=re.M)
        # The SNES backend owns the sprite cache; the MD boss cache aliases BG VRAM.
        if p.name=='boss.c':
            s=s.replace('#include "gen/assets.h"','#include "gen/assets.h"\nextern void native_boss_contact_snapshot(void);\nextern u16 native_boss_contact_possible;')
            s=s.replace('u8 boss_shots(s16 py, s16 px, u8 c, u8 d2, Player **who)',
                        'u8 native_boss_shots_slow(s16 py, s16 px, u8 c, u8 d2, Player **who)')
            at=s.index('bool boss_touch(')
            s=s[:at]+'''extern void native_boss_hitmask(s16 py,s16 px,u8 c,u8 d2);
extern u16 native_boss_masks[2];
extern u16 native_live_shots;
u8 boss_shots(s16 py,s16 px,u8 c,u8 d2,Player **who)
{
    u8 n=0; u16 i,bits; Player *p=players; Shot *s;
    if(boss_dbg_autohit) { *who=players; n=1; }
    if(!native_live_shots) return n;
    native_boss_hitmask(py,px,c,d2);
    if(!(native_boss_masks[0]|native_boss_masks[1])) return n;
    for(i=0;i<2;i++,p++) {
        bits=native_boss_masks[i]; s=p->shots;
        while(bits) {
            if(bits&1) { shot_hit(p,s); *who=p; n++; }
            bits>>=1; s++;
        }
    }
    return n;
}
\n'''+s[at:]
            s=s.replace('bool boss_touch(s16 py, s16 px, u8 e, u8 f2, s8 oy, s8 ox)',
                        'bool native_boss_touch_slow(s16 py, s16 px, u8 e, u8 f2, s8 oy, s8 ox)')
            a=s.index('#define BC_MAX'); b=s.index('/* ======================================================================= projectiles',a)
            s=s[:a]+'''void bc_reserve(u8 n) { (void)n; }
void bs_reserve(u8 n) { (void)n; }
void bc_release(void) {}
void bc_frame(void) {}
void bc_prefetch(u16 c, u8 p) { (void)c; (void)p; }
void bc_draw(u16 c,u8 p,s16 x,s16 y) { spr_32(c,p,x,y,0); }
void bc_draw_resident(u16 c,u8 p,s16 x,s16 y) { spr_32(c,p,x,y,0); }
static void bs_draw(u16 c,u8 p,s16 x,s16 y) { spr_16(c,p,x,y,0); }
\n'''+s[b:]
            s=s.replace('static Pj pj[NPJ];','static Pj pj[NPJ];\nvolatile u16 native_pj_live;')
            s=s.replace('static Pj pj[NPJ];','Pj native_pj[NPJ];\n#define pj native_pj')
            s=s.replace('void pj_draw(void)','void native_pj_draw_slow(void)')
            s=s.replace('void pj_update(void)\n{', 'void pj_update(void)\n{\n    native_boss_contact_snapshot();')
            s=s.replace('if (p->contact && boss_touch(', 'if (p->contact) if (native_boss_contact_possible) if (boss_touch(')
            s=s.replace('static u8 pj_capped_live(void);','u8 pj_capped_live(void);')
            s=s.replace('static u8 pj_capped_live(void)\n{','u8 native_pj_capped_slow(void)\n{')
            s=s.replace('u8 pj_bank_live(u8 bank)\n{','u8 native_pj_bank_slow(u8 bank)\n{')
            a=s.index('        case PJ_BULLET: {',s.index('void pj_update'))
            b=s.index('\n        }',a)
            bullet=s[a+len('        case PJ_BULLET: {'):b].replace('            break;','')
            s=s[:a]+'        case PJ_BULLET: native_pj_bullet_step(p,lvl); break;'+s[b+len('\n        }'):]
            s=s.replace('void pj_update(void)', 'extern void native_pj_bullet_step(Pj *p,u16 lvl);\nextern void native_final_move(void *p);\nvoid pj_update(void)',1)
            s=s.replace('p->y += p->dy; p->x += p->dx;','native_final_move(p);')
            s+='\nvoid native_pj_bullet_step_slow(Pj *p,u16 lvl) {\n'+bullet+'\n}\n'
            s=s.replace('pj_new = -1; }','pj_new = -1; native_pj_live = 0; }',1)
            s=s.replace('pj[i].kind = kind;', 'pj[i].kind = kind; native_pj_live++;')
            a=s.index('static void pj_kill(Pj *p)');b=s.index('static void missile_steer',a)
            s=s[:a]+'''static void pj_kill(Pj *p)
{
    if (p->mate >= 0) {
        Pj *q = &pj[(u8)p->mate];
        if (q->kind == PJ_BEAM) { q->kind = PJ_NONE; native_pj_live--; }
    }
    if (p->kind) { p->kind = PJ_NONE; native_pj_live--; }
}
\n'''+s[b:]
            for fn in ('pj_update','native_pj_draw_slow'):
                s=s.replace('void '+fn+'(void)\n{','void '+fn+'(void)\n{\n    if (!native_pj_live) return;')
            s=s.replace('for (u16 k = 0; k < NPJ; k++) {\n        Pj *p = &pj[k];',
                        'Pj *p = pj;\n    for (u16 k = 0; k < NPJ; k++, p++) {')
            s=s.replace('if (!p->kind || !p->code) continue;', 'if (!p->kind) continue;\n        if (!p->code) continue;')
            a=s.index('        bool blasts = FALSE;');b=s.index('\n    }',a)
            s=s[:a]+s[b:]  # bc_release is empty in the native backend.
            s=s.replace('for (u16 i = 0; i < 2; i++) {\n        Player *p = &players[i];',
                        'Player *p=players;\n    for (u16 i = 0; i < 2; i++,p++) {')
        if p.name=='boss_final.c':
            a=s.index('void fboss_draw(void)');b=s.index('/* ======================================================================= ending',a)
            reference=s[a:b].replace('void fboss_draw(void)','void native_final_draw_slow(void)',1)
            s=s[:a]+'''extern void native_final_draw(const void *segments);
void fboss_draw(void) { if(f.on) native_final_draw(f.seg); }
'''+reference+s[b:]
            s='extern unsigned short native_live_shots;\n'+s
            s=s.replace('#include "hud.h"','#include "hud.h"\nextern volatile u8 boss_dbg_autohit;\nextern void native_boss_contact_snapshot(void);\nextern u16 native_boss_contact_possible;')
            s=s.replace('bool fboss_update(void)\n{', 'bool fboss_update(void)\n{\n    native_boss_contact_snapshot();')
            s=s.replace('if (!s->nocontact) boss_touch(', 'if (!s->nocontact) if(native_boss_contact_possible) boss_touch(')
            s=s.replace('if (!s->immune) {', 'if (!s->immune) if (native_live_shots || boss_dbg_autohit) {')
            s=s.replace('static void seg_load(Seg *s)', 'void native_final_load_slow(Seg *s)')
            at=s.index('static void seg_run(')
            s=s[:at]+'''extern void native_final_load(Seg *s);
extern void native_final_move(Seg *s);
#define seg_load native_final_load
'''+s[at:]
            s=s.replace('s->y += s->dy; s->x += s->dx;', 'native_final_move(s);')
            s+='\nvoid native_final_move_slow(Seg *s) { s->y += s->dy; s->x += s->dx; }\n'
            s=s.replace('for (u16 k = 0; k < 8; k++) {\n        Seg *s = &f.seg[k];',
                        'Seg *s = f.seg;\n    for (u16 k = 0; k < 8; k++,s++) {')
        if p.name=='enemy_ground.c':
            s=s.replace('b->next = en_bullet_dirs[speed_level() - 3][en_aim(e) & 31];','{ u16 speed = speed_level() - 3; u16 heading = en_aim(e) & 31; b->next = en_bullet_dirs[speed][heading]; }')
        if p.name=='enemies.c':
            s=s.replace('static void update_all(void);','extern void native_enemy_pool(Enemy *base,u16 count,bool big);\nstatic void update_all(void);')
            for pool,count,big in [('SMALL','N_SMALL','FALSE'),('BIG','N_BIG','TRUE'),('ITEM','N_ITEM','FALSE')]:
                s=s.replace('if (n_live[EP_'+pool+']) for (e = en_'+pool.lower()+'; e < en_'+pool.lower()+' + '+count+'; e++) if (e->live) update(e, '+big+');','if (n_live[EP_'+pool+']) native_enemy_pool(en_'+pool.lower()+','+count+','+big+');')
            s=s.replace('static u8 cont;', 'u8 native_enemy_cont;\n#define cont native_enemy_cont')
            s=s.replace('static void step_to(Enemy *e, u16 idx)\n{',
                        'extern bool native_enemy_show(Enemy *e,u16 idx);\nstatic void step_to(Enemy *e, u16 idx)\n{\n    if(native_enemy_show(e,idx)) return;')
            s=s.replace('static void draw_small(Enemy *base, u16 n, u16 rot)',
                        'extern void native_enemy_draw_small(Enemy *base,u16 n,u16 rot);\n#define draw_small native_enemy_draw_small\nvoid native_enemy_draw_small_slow(Enemy *base, u16 n, u16 rot)')
            s=s.replace('static void draw_big(u16 i)',
                        'extern void native_enemy_draw_big(u16 i);\n#define draw_big native_enemy_draw_big\nvoid native_enemy_draw_big_slow(u16 i)')
            a=s.index('static bool overloaded(void)');b=s.index('/* rot < n:',a)
            s=s[:a]+'''extern bool native_enemy_bands(void);
static bool overloaded(void)
{
    if (n_live[EP_SMALL] + n_live[EP_ITEM] + 2 * n_live[EP_BIG] <= 18) return FALSE;
    return native_enemy_bands();
}

'''+s[b:]
            a=s.index('static inline  bool move(') if 'static inline  bool move(' in s else s.index('static inline bool move(')
            b=s.index('/* ------------------------------------------------------------------------------------------ */',a)
            s=s[:a]+'extern bool native_enemy_move(void *e, bool big);\n#define move(e,b) native_enemy_move(e,b)\n\n'+s[b:]
            s=s.replace('static inline bool in_terrain(Enemy *e, bool big)', 'bool native_enemy_terrain_slow(Enemy *e, bool big)')
            s=s.replace('bool en_terrain(Enemy *e)', 'extern bool native_enemy_terrain(void *e,bool big);\n#define in_terrain native_enemy_terrain\nbool en_terrain(Enemy *e)')
            # The original loop unconditionally breaks when pass >= 2. Spell
            # that bound in the condition: 816-tcc drops the increment when
            # the condition is empty or constant true.
            s=s.replace('for (u16 pass = 0; ; pass++)','for (u16 pass = 0; pass < 3; pass++)')
            # Keep each early exit explicit: the 65816 compiler miscompiles
            # this compound condition and restores even unobstructed fliers.
            s=s.replace('if ((e->flags & EF_NOTERRAIN) || pass >= 2 || !in_terrain(e, big)) break;',
                        'if (e->flags & EF_NOTERRAIN) break;\n        if (pass >= 2) break;\n        if (!in_terrain(e, big)) break;')
            # Preserve carrier drops and pickup contact on 816-tcc: spell
            # short-circuit branches separately instead of combining them.
            s=s.replace('if (big || !e->item) en_kill_by(e, player_credit(p));',
                        'if (big) en_kill_by(e, player_credit(p));\n            else if (!e->item) en_kill_by(e, player_credit(p));')
            s=s.replace('if (cy + bh <= shots_y0 || cy - bh >= shots_y1 || cx + bw <= shots_x0 || cx - bw >= shots_x1)\n            goto contact;',
                        'if (cy + bh <= shots_y0) goto contact;\n        if (cy - bh >= shots_y1) goto contact;\n        if (cx + bw <= shots_x0) goto contact;\n        if (cx - bw >= shots_x1) goto contact;')
            changes={
                'static inline u16 absdiff(s16 a, s16 b) { return a > b ? a - b : b - a; }\n':'',
                'if (absdiff(cy, l->cy) >= (u16)(bh + l->hh)) continue;':
                    'if (l->cy <= cy - bh - l->hh) continue;\n            if (l->cy >= cy + bh + l->hh) continue;',
                'if (absdiff(cx, l->cx) >= (u16)(bw + l->hw)) continue;':
                    'if (l->cx <= cx - bw - l->hw) continue;\n            if (l->cx >= cx + bw + l->hw) continue;',
                'if (absdiff(py, oy) >= e->box[2]) continue;':
                    's16 dy = (s16)py - oy, dx = (s16)px2 - ox2;\n        if (dy <= -(s16)e->box[2]) continue;\n        if (dy >= e->box[2]) continue;',
                'if (absdiff(px2, ox2) >= e->box[3]) continue;':
                    'if (dx <= -(s16)e->box[3]) continue;\n        if (dx >= e->box[3]) continue;',
            }
            for old,new in changes.items():
                if s.count(old)!=1:raise ValueError('Enemy collision source changed: '+old)
                s=s.replace(old,new)
            s=s.replace('static u8 pl_alive[2], pl_y[2], pl_x2[2];',
                        'u8 pl_alive[2], pl_y[2], pl_x2[2];')
            s=s.replace('static inline  void collide(',
                        'extern bool native_collision_tick(void *e, bool big);\nextern u16 native_enemy_contact(void *e, bool big);\nstatic inline void collide(')
            s=s.replace('if ((frame & 1) != (big ? 1 : 0) && !(big && combined)) return;\n    e->r[R_X2] = AX2(e);',
                        'if (!native_collision_tick(e,big)) return;')
            a=s.index('    u8 oy = AY(e), ox2 = X2(e);',s.index('void collide('))
            b=s.index('\n/* ------------------------------------------------------------------------------------------ */',a)
            s=s[:a]+'''    u16 pi = native_enemy_contact(e,big);
    if (pi >= 2) return;
    Player *p = &players[pi];
    if (!big) { if (e->item) { en_pickup(e,p); return; } }
    player_kill(p);
    en_kill_by(e,p);
}
'''+s[b:]
            s=s.replace('static inline void collide(Enemy *e, const bool big)',
                        'void native_enemy_collide_slow(Enemy *e, const bool big)')
            s=s.replace('static u16 n_live_shots, live_p2;',
                        'u16 native_live_shots;\n#define n_live_shots native_live_shots\nstatic u16 live_p2;')
            s=s.replace('collide(e, big);','native_enemy_collide(e, big);')
            s=s.replace('void native_enemy_update_slow(Enemy *e, const bool big)',
                        'void native_enemy_update_slow(Enemy *e, const bool big)')
            s=s.replace('extern void native_enemy_update(void *e, bool big);',
                        'extern void native_enemy_update(void *e, bool big);\nextern void native_enemy_collide(void *e, bool big);')
            s=s.replace('static void collect_shots(void)\n{',
                        'extern bool native_collect_contacts(void);\nstatic void collect_shots(void)\n{\n    if (!native_collect_contacts()) { n_live_shots=0; live_p2=0; return; }')
            for line in ('        pl_alive[pi] = p->state == PL_ALIVE;\n',
                         '        pl_y[pi] = (u8)(p->y + 16);\n',
                         '        pl_x2[pi] = (u8)((u16)(p->x + 96) >> 1);\n'):
                s=s.replace(line,'')
            s=s.replace('static inline  void update(Enemy *e, const bool big)',
                        'extern void native_enemy_update(void *e, bool big);\n#define update native_enemy_update\nvoid native_enemy_update_slow(Enemy *e, const bool big)')
            s=s.replace('draw_small(en_small, N_SMALL, rot & 15);',
                        'if (n_live[EP_SMALL]) draw_small(en_small, N_SMALL, rot & 15);')
            s=s.replace('draw_small(en_item, N_ITEM, rot & 7);',
                        'if (n_live[EP_ITEM]) draw_small(en_item, N_ITEM, rot & 7);')
            s=s.replace('draw_big(2); draw_big(3);',
                        'if (n_live[EP_BIG]) { draw_big(2); draw_big(3); }')
            s=s.replace('for (u16 k = 0; k < 7; k++) {\n        draw_big',
                        'if (n_live[EP_BIG]) for (u16 k = 0; k < 7; k++) {\n        draw_big')
        if p.name=='player.c':
            # The native renderer shows MD x=32..287. A 32px body must
            # therefore keep its logical left edge within x=32..256.
            for old,new in (('#define MIN_X 0','#define MIN_X 32'),
                            ('#define MAX_X (SCREEN_W - 32)','#define MAX_X (SCREEN_W - 64)'),
                            ('#define CRUSH_X (-16)','#define CRUSH_X MIN_X')):
                if s.count(old)!=1:raise ValueError('Player bounds source changed: '+old)
                s=s.replace(old,new)
        if p.name=='level.c':
            s=s.replace('bool terrain_solid(s16 wx, s16 wy)', 'bool native_terrain_solid_slow(s16 wx, s16 wy)')
        if p.name=='weapons.c':
            s=s.replace('void weapon_select(Player *p)', 'void native_weapon_select_slow(Player *p)')
            s=s.replace('static void upd_linear(Player *p, u8 n)', 'void native_linear_slow(Player *p, u8 n)')
            at=s.index('static void upd_mbl(')
            s=s[:at]+'''void native_linear_slot(Shot *s) { if(s->active==1) shot_move(s); else explode_tick(s); }
extern void native_weapon_linear(Player *p,u8 n);
#define upd_linear native_weapon_linear
'''+s[at:]
            s=s.replace('void weapons_draw(const Player *p)\n{',
                        'void weapons_draw(const Player *p)\n{\n    if (p->state == PL_OFF) { if (!combined) return; }')
            s=s.replace('for (u16 i = 0; i < MAX_SHOTS; i++) {\n        const Shot *s = &p->shots[i];',
                        'const Shot *s = p->shots;\n    for (u16 i = 0; i < MAX_SHOTS; i++, s++) {')
            reference=s[s.index('void weapons_draw('):].replace('void weapons_draw(', 'void native_weapons_draw_slow(',1)
            s=s.replace('void weapons_draw(', 'extern void native_weapon_shots(const Player *p);\nvoid weapons_draw(',1)
            s=s.replace('const Shot *s = p->shots;\n    for (u16 i = 0; i < MAX_SHOTS; i++, s++) {\n        if (s->active) spr_16(s->code, s->colour, s->x, s->y, 0);\n    }', 'native_weapon_shots(p);')
            s+='\n'+reference
        if p.name=='input.c':
            s=s.replace('static u8 map(u16 i, u16 r, u16 pressed)\n{',
                        'static u8 map(u16 i, u16 r, u16 pressed)\n{\n    if (!r) { pad_fire_held[i]=0; af_t[i][0]=0; af_t[i][1]=0; return 0; }')
        if p.name=='flow_menu.c':
            s=s.replace('#include "hud.h"','#include "hud.h"\n#include "native_home_logo.h"')
            s=s.replace('hud_md((HUD_COLS - FE_MD_COLS) / 2, FE_LOGO_ROW + 8, HUD_MD_TILE);',
                        'hud_snes((HUD_COLS - HOME_SNES_COLS) / 2, FE_LOGO_ROW + 8, HUD_MD_TILE);')
            s=s.replace('hud_text(7, 23, 0, "PORTED BY RESTER 159, 2026");',
                        'hud_text(7, 21, 0, "PORTED BY RESTER 159, 2026");\n'
                        '    hud_text(6, 23, 0, "SNES FORK BY FABIO AD, 2026");')
            a=s.index('static void menu_draw(void)');b=s.index('static void menu_open',a)
            s=s[:a]+'''static void menu_draw_row(u16 i)
{
    s16 row=row0+i*2; const MItem *m=&items[i]; bool on=cursor==i;
    hud_blank(0,row,HUD_COLS);
    hud_text(2,row,0,on?">":" ");
    hud_text(4,row,on?4:0,m->label);
    if(m->val) hud_text(val_col,row,on?4:2,m->names[*m->val]);
}
static void menu_draw(void) { for(u16 i=0;i<n_items;i++) menu_draw_row(i); }

'''+s[b:]
            s=s.replace('if (in & BUTTON_UP) { cursor = cursor ? cursor - 1 : n_items - 1; menu_draw(); }',
                        'if (in & BUTTON_UP) { u16 old=cursor; cursor=cursor?cursor-1:n_items-1; menu_draw_row(old); menu_draw_row(cursor); }')
            s=s.replace('if (in & BUTTON_DOWN) { cursor = cursor + 1 < n_items ? cursor + 1 : 0; menu_draw(); }',
                        'if (in & BUTTON_DOWN) { u16 old=cursor; cursor=cursor+1<n_items?cursor+1:0; menu_draw_row(old); menu_draw_row(cursor); }')
            s=s.replace('        menu_draw();\n        return M_CHANGED;', '        menu_draw_row(cursor);\n        return M_CHANGED;')
            s=s.replace('u16 who = (p1 & (BUTTON_START | BUTTON_A | BUTTON_C)) || !p2 ? 0 : 1;',
                        'u16 who = 0;\n    if (p2) { if (!(p1 & (BUTTON_START | BUTTON_A | BUTTON_C))) who = 1; }')
        if p.name=='flow_game.c':
            s=s.replace('    HudPanel hp;\n    memset(&hp, 0, sizeof(hp));', '''    static HudPanel hp;
    static u8 panel_valid, panel_st[2];
    u16 bars=boss_hud.active?boss_hud.bars:0;
    if(game_active) {
        bool simple=TRUE;
        if(pf[0].st!=PS_IDLE) { if(pf[0].st!=PS_PLAYING) simple=FALSE; }
        if(pf[1].st!=PS_IDLE) { if(pf[1].st!=PS_PLAYING) simple=FALSE; }
        if(panel_st[0]!=pf[0].st) simple=FALSE;
        if(panel_st[1]!=pf[1].st) simple=FALSE;
        if(panel_valid) { if(simple) { if(hp.hi==hi_score) { if(hp.boss_bars==bars) {
            hud_panel(&hp); return;
        } } } }
        panel_valid=TRUE;
    } else panel_valid=FALSE;
    panel_st[0]=pf[0].st; panel_st[1]=pf[1].st;
    memset(&hp, 0, sizeof(hp));''')
            s=s.replace('for (u16 i = 0; i < 2; i++) player_flow(i);','player_flow(0); player_flow(1);')
            s=s.replace('for (u16 i = 0; i < 2; i++)\n            if (players[i].score > hi_score) hi_score = players[i].score;',
                        '{ if(players[0].score>hi_score) hi_score=players[0].score; if(players[1].score>hi_score) hi_score=players[1].score; }')
        if p.name=='flow.c':
            # 816-tcc miscompiles the compound while condition: i <= 0
            # branches into the shift body, copying before ranking[].
            s=s.replace('while (i > 0 && score > ranking[i - 1].score) { ranking[i] = ranking[i - 1]; i--; }',
                        'for (i = 4; i > 0; i--) { if (score <= ranking[i - 1].score) break; ranking[i] = ranking[i - 1]; }')
        if p.name=='boss_data.c':
            # These are private to the removed MD boss VRAM cache. The native
            # OBJ cache uses spr_bank and the original pen data instead.
            s=re.sub(r'^const\s+u(?:8|16)\s+boss_(?:block|small)_(?:keys|data)\[[^\]]*\]\s*=\s*\{.*?\};\s*','',s,flags=re.M|re.S)
            def wheel_tiles(m):
                data=bytes(int(v,16) for v in re.findall(r'0x([0-9a-fA-F]+)',m[2]))
                data=planar(data)
                return m[1]+'{'+','.join('0x%02x'%v for v in data)+'};'
            s=re.sub(r'(static const u8 \w+_tiles\[\d+\]\s*=\s*)\{(.*?)\};',wheel_tiles,s,flags=re.S)
        # UL is 16 bits in this compiler; make the original 32-bit constants explicit.
        s=re.sub(r'(?i)(0x[0-9a-f]+|\b[0-9]+)UL\b',r'\1ULL',s)
        (DEST/'src/logic'/p.name).write_text(lower(s))
        inventory.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    # Real 32-bit words on 816-tcc use long long (long is 16 bits).
    for p in (DEST/'inc').rglob('*.h'):
        s=p.read_text().replace('1UL <<','1ULL <<').replace('0x0FFFFFFFUL','0x0FFFFFFFULL')
        if p.name=='hud.h': s=re.sub(r'#define HUD_ROW_BIT\(r\).*', '#define HUD_ROW_BIT(r) native_row_bit(r)',s)
        p.write_text(s)
    # Referenced symbols in the generated 68K wrappers retain their names.
    wrappers=list((UP/'src/gen').glob('*.s'))
    blobs={}
    for p in wrappers:
        symbol=None
        for line in p.read_text().splitlines():
            m=re.match(r'([A-Za-z_]\w*):',line)
            if m: symbol=m[1]
            m=re.search(r'\.incbin "([^"]+)"',line)
            if m and symbol: blobs[symbol]=UP/m[1]
    words=set()
    for p in (UP/'inc/gen').glob('*.h'):
        words.update(re.findall(r'extern const (?:u16|s16) (\w+)\[',p.read_text()))
    asm=['; Generated by tools/prepare_snes.py. HiROM contiguous data.', '.INCLUDE "hdr.asm"']
    bank=8; offset=0
    sizes={}
    overrides,pattern_count=native_boss_banks()
    header=DEST/'inc/gen/assets.h'
    header.write_text(re.sub(r'#define SPR_BANK_COUNT \d+',f'#define SPR_BANK_COUNT {pattern_count}',header.read_text()))
    for symbol,p in blobs.items():
        data=overrides.get(symbol,p.read_bytes())
        if symbol in words:
            data=b''.join(data[i:i+2][::-1] for i in range(0,len(data),2))
        if re.fullmatch(r'fe_scene\d+_map',symbol):
            cells=struct.unpack('<1792H',data)
            def scene_cell(e):
                return (((e&2047)-160+16)|(((e>>13)&1)<<10)|0x3000|
                        (0x4000 if e&0x0800 else 0)|(0x8000 if e&0x1000 else 0)) if e else 0
            data=b''.join(struct.pack('<H',scene_cell(cells[y*64+x+4])) for y in range(28) for x in range(32))
        # Packed MD patterns are transformed before build, never at runtime.
        is_tiles=(symbol.endswith('_tiles') or symbol in ('spr_bank','spr_big','boss_block_data','boss_small_data'))
        if is_tiles: data=planar(data)
        if symbol=='spr_big':
            # MD composites are column-major. SNES OBJ rows have a stride
            # of sixteen characters; retain each four-character row together.
            data=b''.join(data[b+(x*4+y)*32:b+(x*4+y+1)*32]
                          for b in range(0,len(data),512) for y in range(4) for x in range(4))
        out=DEST/'res'/f'{symbol}.bin'; out.write_bytes(data)
        offset=(offset+511)&~511
        if offset==65536: bank+=1; offset=0
        # Small arrays use ordinary 16-bit indexing in 816-tcc. Keep each
        # within one bank; large graphics use native_offset at runtime.
        if len(data)<=65536 and offset+len(data)>65536:bank+=1;offset=0
        pos=0; first=True
        while pos<len(data):
            n=min(len(data)-pos,65536-offset)
            asm += [f'.BANK {bank} SLOT 0',f'.ORG ${offset:04x}',f'.SECTION "asset_{symbol}_{pos}" FORCE KEEP']
            if first: asm.append(f'{symbol}:'); first=False
            asm += [f'.INCBIN "res/{symbol}.bin" SKIP {pos} READ {n}', '.ENDS']
            pos+=n; offset+=n
            if offset==65536: bank+=1; offset=0
        sizes[symbol]=len(data)
    # Pre-colour the text font. Converting bitmap planes on the 65816 costs
    # hundreds of frames on menu entry; all common glyphs are ROM-native.
    font=(UP/'res/generated/font_pens.bin').read_bytes()
    lut=(UP/'res/generated/txt_lut.bin').read_bytes()
    native_font=bytearray()
    for colour in range(64):
        table=lut[colour*256:(colour+1)*256]
        native_font+=planar(bytes(table[b] for b in font[:256*32]))
    (DEST/'res/snes_font_tiles.bin').write_bytes(native_font)
    offset=(offset+511)&~511; pos=0
    while pos<len(native_font):
        if offset==65536:bank+=1;offset=0
        n=min(len(native_font)-pos,65536-offset)
        asm += [f'.BANK {bank} SLOT 0',f'.ORG ${offset:04x}',f'.SECTION "font_{pos}" FORCE KEEP']
        if not pos:asm.append('snes_font_tiles:')
        asm += [f'.INCBIN "res/snes_font_tiles.bin" SKIP {pos} READ {n}','.ENDS']
        pos+=n;offset+=n
    if bank>=56:raise ValueError('Graphics overlap sound bank 56')
    # Starfield uses BG3's two bitplanes; the seeded star colours occupy
    # palette 0 entries 1..3 and palette 1 entries 1..2 in the MD assets.
    raw=(UP/'res/generated/star_tiles.bin').read_bytes()
    star=b''.join(planar(raw[i:i+32])[:16] for i in range(0,len(raw),32))
    rawmap=(UP/'res/generated/star_map.bin').read_bytes()
    smap=bytearray(4096)
    for y in range(32):
        for x in range(64):
            e=int.from_bytes(rawmap[(y*64+x)*2:(y*64+x)*2+2],'big')
            v=(e&0x7ff)|(((e>>13)&1)<<12)
            at=((1024 if x&32 else 0)+y*32+(x&31))*2
            smap[at:at+2]=v.to_bytes(2,'little')
    panel_cells=[]
    for row in range(28):
        for col in range(40):
            c,r=col,row;valid=True
            if r==0:
                if c<=2:c+=4
                elif 4<=c<=11:c+=3
                elif 14<=c<=15:r=1;c+=2
                elif 17<=c<=24:r=1;c+=2
                elif 28<=c<=30 or 32<=c<=39:c-=4
                else:valid=False
            elif r==1:
                if c<8:c+=4
                elif c<28 or c>=36:valid=False
            elif r==2:
                if c<8:valid=False
                c-=4
            elif 25<=r<=27:
                player=int(c>=20);local=c-player*20
                if r==25:
                    if local>=16:valid=False
                    c=4+player*16+local
                elif r==26:
                    k=local&3
                    if k==3:valid=False
                    c=4+player*16+(local>>2)*3+k
                elif local<8:c=4+player*16+local
                else:
                    local-=8;k=local&3
                    if k==1 or k==2:valid=False
                    c=4+player*16+8+(local>>2)*2+int(k==3)
            c-=4
            panel_cells.append((r*32+c)*2 if valid and 0<=c<32 else 65535)
    panel_data=struct.pack('<1120H',*panel_cells)
    for name,data in [('snes_stars',star),('snes_star_map',smap),('native_panel_cells',panel_data)]:
        (DEST/'res'/f'{name}.bin').write_bytes(data)
        asm += [f'.SECTION "{name}" SUPERFREE',f'{name}:',f'.INCBIN "res/{name}.bin"','.ENDS']
    # Keep bank 55 free for the native routine probes; audio starts in 56.
    home_assets,home_tiles=build_home_logo(UP)
    for name,data in home_assets.items():
        if name.endswith('_tiles'):data=planar(data)
        (DEST/'res'/f'{name}.bin').write_bytes(data)
        asm += [f'.SECTION "{name}" SUPERFREE',f'{name}:',f'.INCBIN "res/{name}.bin"','.ENDS']
    (DEST/'inc/native_home_logo.h').write_text(
        '#ifndef NATIVE_HOME_LOGO_H\n#define NATIVE_HOME_LOGO_H\n#include "native.h"\n'
        '#define HOME_SNES_COLS 16\n#define HOME_SNES_ROWS 4\n'
        f'#define HOME_SNES_TILES {home_tiles}\n'
        'extern const u8 native_home_snes_tiles[];\nextern const u16 native_home_snes_map[];\n'
        'void hud_snes(s16 col,s16 row,u16 tile);\n#endif\n')
    pos=0; par_assets=parallax_assets()
    for name,data in par_assets.items():
        (DEST/'res'/f'{name}.bin').write_bytes(data)
        asm += ['.BANK 54 SLOT 0',f'.ORG ${pos:04x}',f'.SECTION "{name}" FORCE KEEP',
                f'{name}:',f'.INCBIN "res/{name}.bin"','.ENDS']
        pos+=len(data)
    wheel_blobs,wheels=build_wheels(UP,planar)
    wheel_bank=6;wheel_pos=0
    for name,data in wheel_blobs.items():
        if wheel_pos+len(data)>65536:
            wheel_bank=7 if wheel_bank==6 else 53;wheel_pos=0
        assert wheel_pos+len(data)<=65536
        (DEST/'res'/f'{name}.bin').write_bytes(data)
        asm += [f'.BANK {wheel_bank} SLOT 0',f'.ORG ${wheel_pos:04x}',f'.SECTION "{name}" FORCE KEEP',
                f'{name}:',f'.INCBIN "res/{name}.bin"','.ENDS']
        wheel_pos+=len(data)
    wheel_header='''#ifndef NATIVE_WHEELS_H
#define NATIVE_WHEELS_H
#include "native.h"
typedef struct { u16 type,home,count,x,y; const u16 *keys; const u8 *tiles; const u16 *maps; } NativeWheel;
extern const NativeWheel native_wheels[5];
#endif
'''
    (DEST/'inc/native_wheels.h').write_text(wheel_header)
    wheel_c=['#include "native_wheels.h"']
    for name in wheel_blobs:wheel_c.append('extern const '+('u8' if name.endswith('_tiles') else 'u16')+' '+name+'[];')
    wheel_c+=['const NativeWheel native_wheels[5] = {']
    for n,home,count,x,y,name in wheels:
        wheel_c.append('{%d,%d,%d,%d,%d,%s_keys,%s_tiles,%s_maps},'%(n,home,count,x,y,name,name,name))
    wheel_c+=['};']
    (DEST/'src/wheel_data.c').write_text('\n'.join(wheel_c)+'\n')
    (DEST/'inc/parallax_native.h').write_text(
        '#ifndef PARALLAX_NATIVE_H\n#define PARALLAX_NATIVE_H\n#include "native.h"\n'
        'extern const u16 native_star_phases[];\nextern const u8 native_star_tiles[],native_far_tiles[];\n'
        f'#define NATIVE_STAR_BYTES {len(par_assets["native_star_tiles"])}\n'
        'extern u8 par_hdma_pending[100];\nextern u16 par_hdma_enabled;\n'
        'extern s16 par_scroll_x,par_scroll_y;\nextern u16 par_map_register;\n'
        'void native_parallax_commit(void);\nvoid native_par_rows(void);\n'
        'void native_par_column(u16 column,const u16 *src,u16 row);\n'
        'void par_native_frame(s16 x,s16 y,bool active);\n#endif\n')
    (DEST/'src/assets.asm').write_text('\n'.join(asm)+'\n')
    (ROOT/'build/source_manifest.json').write_text(json.dumps({'md_sources':inventory,'blobs':sizes,'last_data_bank':bank},indent=2)+'\n')
    print(f'Staged {len(inventory)} source files, {len(blobs)} blobs, last data bank {bank}')
    build_hud()
    guard_headers()

def guard_headers():
    for p in list((DEST/'inc').rglob('*.h'))+list((DEST/'src/logic').glob('*.h')):
        s=p.read_text(); guard='SA_SNES_'+str(p.relative_to(DEST)).upper().replace('/','_').replace('.','_')
        if p.name=='game.h':
            s=re.sub(r'^static inline s16 cam_[xy]\(void\);\n','',s,flags=re.M)
            for axis in ('x','y'):
                s=s.replace('static inline s16 cam_'+axis+'(void) { return level.scroll_'+axis+' + ARCADE_VIEW_'+axis.upper()+'; }',
                            '#define cam_'+axis+'() ((s16)(level.scroll_'+axis+' + ARCADE_VIEW_'+axis.upper()+'))')
        if p.name=='boss_int.h':
            for name,param,expr in [('to_gx','x','(s16)(x)-ARCADE_VIEW_X-boss_shift'),('to_gy','y','(s16)(y)-ARCADE_VIEW_Y'),
                                    ('raw_x','gx','(s16)(gx)+ARCADE_VIEW_X+boss_shift'),('raw_y','gy','(s16)(gy)+ARCADE_VIEW_Y')]:
                s=re.sub(r'^static inline s16 '+name+r'\([^\n]+\}\n', '#define '+name+'('+param+') ((s16)('+expr+'))\n',s,flags=re.M)
        p.write_text(s)
        if not s.startswith('#ifndef '+guard): p.write_text('#ifndef '+guard+'\n#define '+guard+'\n'+s+'\n#endif\n')

def build_hud():
    original=(UP/'src/hud.c').read_text()
    # Retain the MD's formatting, scores, lives, weapon state and HUD panel logic.
    text=original[original.index('void hud_codes('):original.index('/* ---- logo')]
    panel=original[original.index('#define COL_P'):original.index('/* ---- frame / init')]
    a=panel.index('static void bar_slot('); b=panel.index('static u16 speed_cache',a)
    panel=panel[:a]+'''static void bar_slot(u16 i,u16 s,u8 state)
{
    u16 k,t=193+i*20+s*4; const u8 *src=fe_bar_tiles+(state*20+s*4)*32;
    for(k=0;k<4;k++) { native_copy(src+k*32,0x4000+(t+k)*16,32); put(COL_P(i)+s*4+k,26,(t+k)|((2+(fe_bar_pal[state]&1))<<10)|0x2000); }
    cur.slot[i][s]=state;
}
\n'''+panel[b:]
    panel=panel.replace('cur.on = FALSE;', 'cur.on = FALSE; panel_active = FALSE;')
    panel=panel.replace('if (!p->on) { hud_panel_off(); return; }', 'if (!p->on) { hud_panel_off(); return; }\n    panel_active = TRUE;')
    prefix=(ROOT/'snes/src/hud_prefix.inc').read_text()
    suffix='''
void hud_frame(void) {}
void hud_flush_done(void) {}
void hud_game_pool_reset(void) { panel_active=FALSE; native_hud_clear(); cur.on=FALSE; glyph_count=0; memset(digit_cache,0,sizeof(digit_cache)); memset(speed_cache,0,sizeof(speed_cache)); }
void hud_init(void) { glyph_count=0; memset(&cur,0,sizeof(cur)); native_hud_clear(); hud_game_pool_reset(); }
'''
    s=prefix+'\n'+text+'\n'+panel+'\n'+suffix
    # The panel's flash phase changes every four ticks. Avoid re-evaluating
    # every bar, score and label on the other ticks when its inputs match.
    cache='''
static HudPanel native_panel_last;
static u32 native_panel_score[2];
static u8 native_panel_stats[2][9], native_panel_phase;
static bool native_panel_changed(const HudPanel *p)
{
    u16 i; bool changed = !cur.on;
    if (native_panel_phase != (frame & 12)) changed = TRUE;
    if (memcmp(&native_panel_last,p,sizeof(HudPanel))) changed = TRUE;
    for (i=0;i<2;i++) {
        const Player *pl=&players[i];
        if (native_panel_score[i]!=pl->score) changed=TRUE;
        if (memcmp(native_panel_stats[i],&pl->speed,9)) changed=TRUE;
    }
    if (!changed) return FALSE;
    native_panel_phase=frame&12;
    memcpy(&native_panel_last,p,sizeof(HudPanel));
    for (i=0;i<2;i++) {
        native_panel_score[i]=players[i].score;
        memcpy(native_panel_stats[i],&players[i].speed,9);
    }
    return TRUE;
}
'''
    cache=cache.replace('static bool native_panel_changed(', 'bool native_panel_changed_slow(')
    cache+='''
extern bool native_panel_probe(const HudPanel *p,bool visible);
static bool native_panel_changed(const HudPanel *p) { return native_panel_probe(p,cur.on); }
'''
    s=s.replace('void hud_panel(const HudPanel *p)\n{',cache+'\nvoid hud_panel(const HudPanel *p)\n{')
    s=s.replace('panel_active = TRUE;\n    if (!cur.on)',
                'panel_active = TRUE;\n    if (!native_panel_changed(p)) return;\n    if (!cur.on)')
    s=re.sub(r'(?i)(0x[0-9a-f]+|\b[0-9]+)UL\b',r'\1ULL',s)
    (DEST/'src/hud.c').write_text(lower(s))

if __name__=='__main__': stage()
