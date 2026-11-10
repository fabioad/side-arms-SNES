#include "native.h"
#include "sprites.h"
#include "gen/assets.h"
#define SLOTS 48
#define BIG_SLOTS 12
static u16 keys[SLOTS],uploads;
u16 native_small_used[SLOTS];
#define used native_small_used
u16 native_spr_stamp,native_spr_count;
#define stamp native_spr_stamp
#define count native_spr_count
static u8 palettes[SLOTS];
u16 native_small_attributes[SLOTS];
#define attributes native_small_attributes
static const u16 flip_bits[4]={0,0x4000,0x8000,0xc000};
extern u8 native_sprite_hint[32768];
#define hint native_sprite_hint

u16 native_big_keys[BIG_SLOTS],native_big_used[BIG_SLOTS];
#define big_keys native_big_keys
#define big_used native_big_used
static u8 big_pal[BIG_SLOTS];
u8 native_big_hint[2048];
#define big_hint native_big_hint
u16 native_big_attributes[BIG_SLOTS];
#define big_attributes native_big_attributes
volatile u32 spr_dbg_dropped;
extern u16 native_sprite_missing_keys[256],native_big_missing_keys[256];
extern u16 native_sprite_missing_count,native_big_missing_count;
extern u16 native_big_find(u16 key);
extern u16 native_big_victim(void);
static u16 slot_tile(u16 n) { return ((n&0x38)<<2)|((n&7)<<1); }
void spr_init(void)
{
    native_sprite_missing_count=native_big_missing_count=0;
    memset(keys,255,sizeof(keys)); memset(used,0,sizeof(used)); memset(hint,0,sizeof(hint));
    memset(big_keys,255,sizeof(big_keys)); memset(big_used,0,sizeof(big_used));
    memset(big_hint,0,sizeof(big_hint));
}
void spr_begin(void) { native_oam_clear(); stamp++; count=0; uploads=0; }
static u16 pattern(u16 code,u8 colour)
{
    u16 key=(code&2047)|((u16)(colour&15)<<11),i,slot=0,age=0,d,idx,t;
    const u8 *s; static u8 packed[32],data[128],raw[128]; u8 a;
    i=hint[key]; if(i) { used[i-1]=stamp; return i-1; }
    for(i=0;i<SLOTS;i++) { d=keys[i]==0xffff?0xffff:stamp-used[i]; if(d>age) { age=d;slot=i; } }
    if(!age) { spr_dbg_dropped++; return 0xffff; }
    if(keys[slot]!=0xffff) hint[keys[slot]]=0;
    idx=spr_bank_index[key]; palettes[slot]=idx>>15;
    if(idx&0x7fff) s=native_offset(spr_bank,(u32)((idx&0x7fff)-1)*128);
    else {
        if(native_sprite_missing_count<256) native_sprite_missing_keys[native_sprite_missing_count++]=key;
        s=native_offset(sprite_pens,(u32)(code&2047)*128); palettes[slot]=sprite_lut[256+(colour&15)];
        for(i=0;i<128;i++) { a=s[i]; raw[i]=sprite_pair_lut[(u16)(colour&15)*256+a]; }
        for(i=0;i<4;i++) { memcpy(packed,raw+i*32,32); native_tile(packed,data+i*32); }
        s=data;
    }
    /* MD cell order TL,BL,TR,BR -> SNES OBJ row stride of 16 tiles. */
    t=slot_tile(slot);
    native_copy(s,0x6000+t*16,32); native_copy(s+64,0x6000+(t+1)*16,32);
    native_copy(s+32,0x6000+(t+16)*16,32); native_copy(s+96,0x6000+(t+17)*16,32);
    keys[slot]=key;used[slot]=stamp;uploads++;hint[key]=slot+1;
    attributes[slot]=t|((u16)palettes[slot]<<9)|0x3000;
    return slot;
}
void spr_16_slow(u16 code,u8 colour,s16 x,s16 y,u8 flags)
{
    u16 slot;
    x-=32; if(x<=-16 || x>=256 || y<=-16 || y>=224) return;
    if(count>=128) { spr_dbg_dropped++; return; }
    slot=pattern(code,colour); if(slot==0xffff) return;
    native_obj(count*4,x,y,attributes[slot]|flip_bits[flags&3],0);count++;
}
void spr_32_slow(u16 code,u8 col,s16 x,s16 y,u8 f)
{
    u16 dx,dy,off,key,idx,i,slot=0xffff,t;
    const u8 *src;
    if(x-32<=-32 || x-32>=256 || y<=-32 || y>=224) return;
    key=(code&2047)|((u16)(col&15)<<11);
    i=big_hint[code&2047];
    if(i) { if(big_keys[i-1]==key) slot=i-1; }
    if(slot==0xffff) {
        slot=native_big_find(key);
    }
    idx=1;
    if(slot==0xffff) idx=spr_big_index[key];
    if(!(idx&0x7fff)) { if(native_big_missing_count<256) native_big_missing_keys[native_big_missing_count++]=key; }
    if(idx&0x7fff) {
        if(slot==0xffff) {
            slot=native_big_victim();
            if(slot!=0xffff) {
                big_keys[slot]=key; big_pal[slot]=idx>>15;
                src=native_offset(spr_big,(u32)((idx&0x7fff)-1)*512);
                t=192+(slot/4)*64+(slot%4)*4;
                big_attributes[slot]=t|((u16)big_pal[slot]<<9)|0x3000;
                for(i=0;i<4;i++) native_copy(src+i*128,0x6000+(t+i*16)*16,128);
                uploads+=4;
            } else slot=0xffff;
        }
        if(slot!=0xffff) {
            if(count>=128) { spr_dbg_dropped++; return; }
            big_used[slot]=stamp; big_hint[code&2047]=slot+1;
            native_obj(count*4,x-32,y,big_attributes[slot]|flip_bits[f&3],1);count++;return;
        }
    }
    for(dy=0;dy<2;dy++) for(dx=0;dx<2;dx++) {
        off=(f&SPR_FLIPY?1-dy:dy)*8+(f&SPR_FLIPX?1-dx:dx);
        spr_16(code+off,col,x+dx*16,y+dy*16,f);
    }
}
void spr_tile16(u16 t,u8 p,s16 x,s16 y) { (void)t;(void)p;(void)x;(void)y; }
void spr_tile32(u16 t,u8 p,s16 x,s16 y) { (void)t;(void)p;(void)x;(void)y; }
void spr_end(void) {}
u16 spr_uploads(void) { return uploads; }
