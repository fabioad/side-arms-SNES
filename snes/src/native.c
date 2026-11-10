#include "native.h"
#include "video.h"

/* Immutable ROM data is queued directly; transient RAM data is snapshotted. */
#define QUEUE_BYTES 30000
#define QUEUE_ITEMS 512
u8 queue_data[QUEUE_BYTES];
u16 queue_dest[QUEUE_ITEMS],queue_size[QUEUE_ITEMS],queue_off[QUEUE_ITEMS];
u16 queue_bank[QUEUE_ITEMS];
u16 queue_used,queue_count,queue_total;
typedef union { const void *ptr; struct { u16 address,bank; } words; } NativeAddress;
volatile u16 native_dma_bytes,native_dma_overflow,native_long_blank;
volatile u16 native_dma_late;
u16 hud_map[1024];
u32 hud_dirty;
u16 palram[256];
bool paldirty;
u32 native_row_bit(u16 row)
{
    static const u32 bits[32]={
        1ULL,2ULL,4ULL,8ULL,16ULL,32ULL,64ULL,128ULL,256ULL,512ULL,1024ULL,2048ULL,4096ULL,8192ULL,16384ULL,32768ULL,
        65536ULL,131072ULL,262144ULL,524288ULL,1048576ULL,2097152ULL,4194304ULL,8388608ULL,
        16777216ULL,33554432ULL,67108864ULL,134217728ULL,268435456ULL,536870912ULL,1073741824ULL,2147483648ULL};
    return bits[row&31];
}

/* Assembly handles the frequent, bank-contained ROM transfers directly. */
void native_copy_slow(const void *src,u16 word,u16 bytes)
{
    const u8 *p=src; u16 n,bank; NativeAddress source,dest;
    if(!bytes) return;
    if(bytes>2048) {
        while(bytes) { n=bytes>2048?2048:bytes; native_copy(p,word,n); p=native_offset(p,n); word+=n/2; bytes-=n; }
        return;
    }
    if(queue_count>=QUEUE_ITEMS) { native_dma_overflow++; return; }
    if(bytes>QUEUE_BYTES-queue_total) { native_dma_overflow++; return; }
    source.ptr=src; bank=source.words.bank&255;
    n=65535-source.words.address;
    if(bank>=0xc0) {
        if(bytes-1<=n) {
            queue_dest[queue_count]=word; queue_size[queue_count]=bytes;
            queue_off[queue_count]=source.words.address; queue_bank[queue_count++]=bank|0x8000;
            queue_total+=bytes; return;
        }
    }
    dest.ptr=queue_data+queue_used;
    queue_dest[queue_count]=word; queue_size[queue_count]=bytes;
    queue_off[queue_count]=dest.words.address; queue_bank[queue_count++]=(dest.words.bank&255)|0x8000;
    /* MVN and DMA wrap their 16-bit source address at the bank boundary.
     * Snapshot crossing sources in two pieces, including odd boundaries. */
    if(bytes-1>n) {
        n++; memcpy(queue_data+queue_used,src,n);
        memcpy(queue_data+queue_used+n,native_offset(src,n),bytes-n);
    } else memcpy(queue_data+queue_used,src,bytes);
    queue_used+=bytes; queue_total+=bytes;
}
void native_tile(const u8 *src,u8 *dst)
{
    u16 x,y,p; u8 n,v;
    memset(dst,0,32);
    for(y=0;y<8;y++) for(x=0;x<8;x++) {
        n=(src[y*4+x/2] >> ((x&1)?0:4))&15;
        for(p=0;p<4;p++) { v=(n>>p)&1; dst[(p/2)*16+y*2+(p&1)] |= v<<(7-x); }
    }
}
static u16 mdcolor(u16 c)
{
    u16 r=(c>>1)&7,g=(c>>5)&7,b=(c>>9)&7;
    r=(r<<2)|(r>>1); g=(g<<2)|(g>>1); b=(b<<2)|(b>>1);
    return r|(g<<5)|(b<<10);
}
void native_palette(u16 index,const u16 *src,u16 n)
{
    u16 i,k;
    for(i=0;i<n;i++) {
        k=index+i; palram[k]=mdcolor(src[i]);
        if(k<32) palram[64+k]=palram[k];
        if(k>=32 && k<64) palram[128+k-32]=palram[k];
    }
    /* BG3 palettes for pre-shifted star tiles. BG2's original colours live
     * at 64..95; HUD and OBJ retain their existing independent palettes. */
    palram[5]=palram[65]; palram[6]=palram[66]; palram[7]=palram[81];
    palram[9]=palram[65]; palram[10]=palram[67]; palram[11]=palram[82];
    palram[13]=palram[66]; palram[14]=palram[81]; palram[15]=palram[82];
    palram[21]=palram[69]; palram[22]=palram[70];
    paldirty=TRUE;
}
void native_hud_tile(u16 tile,const u8 *packed)
{
    u8 data[32]; native_tile(packed,data); native_copy(data,0x4000+tile*16,32);
}
void native_hud_put_slow(s16 col,s16 row,u16 entry)
{
    col-=4; /* centre the MD's 40 columns in the 32-column SNES display */
    if(col<0 || col>=32 || row<0 || row>=28) return;
    if(hud_map[row*32+col]==entry) return;
    hud_map[row*32+col]=entry; hud_dirty|=native_row_bit(row);
}
void native_hud_clear(void) { memset(hud_map,0,sizeof(hud_map)); hud_dirty=0x0fffffffULL; }
void native_map(u16 plane,const u16 *src,u16 x,u16 y,u16 w,u16 h,u16 stride)
{
    u16 r,c,e,base,at; u16 row[64];
    base=plane==BG_B?0x3800:0x7800;
    for(r=0;r<h;r++) {
        for(c=0;c<w;c++) {
            e=src[r*stride+c];
            row[c]=(e&0x7ff)|(((e>>13)&3)<<10)|((e&0x8000)?0x2000:0)|((e&0x0800)?0x4000:0)|((e&0x1000)?0x8000:0);
        }
        /* SNES 64-wide maps consist of two 32x32 screens, not 64-word rows. */
        for(c=0;c<w;c++) { at=base+(((x+c)&32)?1024:0)+((y+r)&31)*32+((x+c)&31); native_copy(row+c,at,2); }
    }
}
void native_prepare_flush(void)
{
    u16 i,rows;
    rows=(u16)hud_dirty;i=0;
    while(rows) {
        if(rows&1) native_copy((u8 *)(hud_map+i*32),0x5800+i*32,64);
        rows>>=1;i++;
    }
    rows=(u16)(hud_dirty>>16);i=16;
    while(rows) {
        if(rows&1) native_copy((u8 *)(hud_map+i*32),0x5800+i*32,64);
        rows>>=1;i++;
    }
    hud_dirty=0; native_dma_bytes=queue_total;
}
void native_init(void)
{
    u8 blank[32];
    native_dma_splits=0;native_boss_snapshot_valid=0;
    setScreenOff(); setMode(BG_MODE1,0);
    bgSetGfxPtr(0,0x4000); bgSetMapPtr(0,0x5800,SC_32x32);
    bgSetGfxPtr(1,0x0000); bgSetMapPtr(1,0x3800,SC_64x32);
    bgSetGfxPtr(2,0x3000); bgSetMapPtr(2,0x7800,SC_64x32);
    bgSetEnable(0); bgSetEnable(1); bgSetEnable(2); bgSetDisable(3);
    REG_OBSEL=0x60|3; /* 16/32 pixel OBJ, base $6000 words */
    oamClear(0,128); memset(blank,0,32);
    dmaCopyVram(blank,0,32); dmaCopyVram(blank,0x4000,32);
    native_hud_clear();
}
u16 JOY_getJoypadType(u16 port) { (void)port; return JOY_TYPE_PAD6; }
u16 JOY_readJoypad(u16 port)
{
    u16 k=padsCurrent(port),r=0;
    if(k&KEY_UP) r|=BUTTON_UP; if(k&KEY_DOWN) r|=BUTTON_DOWN;
    if(k&KEY_LEFT) r|=BUTTON_LEFT; if(k&KEY_RIGHT) r|=BUTTON_RIGHT;
    if(k&KEY_Y) r|=BUTTON_A; if(k&KEY_B) r|=BUTTON_B;
    if(k&KEY_A) r|=BUTTON_C; if(k&KEY_START) r|=BUTTON_START;
    if(k&KEY_L) r|=BUTTON_X; if(k&KEY_R) r|=BUTTON_Y;
    if(k&KEY_X) r|=BUTTON_Z; if(k&KEY_SELECT) r|=BUTTON_MODE;
    return r;
}
void SRAM_enable(void) {} void SRAM_enableRO(void) {} void SRAM_disable(void) {}
u8 SRAM_readByte(u16 offset) { return *((volatile u8 *)0x306000+offset); }
void SRAM_writeByte(u16 offset,u8 v) { *((volatile u8 *)0x306000+offset)=v; }
u32 SRAM_readLong(u16 off)
{
    u32 v=0; u16 i; for(i=0;i<4;i++) v=(v<<8)|SRAM_readByte(off+i); return v;
}
void SRAM_writeLong(u16 off,u32 v)
{
    SRAM_writeByte(off,(u8)(v>>24)); SRAM_writeByte(off+1,(u8)(v>>16));
    SRAM_writeByte(off+2,(u8)(v>>8)); SRAM_writeByte(off+3,(u8)v);
}
void DMA_queueDma(u16 type,void *src,u16 dest,u16 words,u16 step)
{
    u16 i,e,x,y; const u16 *s=src; (void)type;
    if(dest>=VRAM_PLANE_B && dest<VRAM_PLANE_B+4096) {
        for(i=0;i<words;i++) { e=(dest-VRAM_PLANE_B+i*step)/2; x=e&63; y=e>>6; native_map(BG_B,s+i,x,y,1,1,1); }
    } else if(dest>=VRAM_BG_TILE*32 && dest<VRAM_BG_TILE*32+28672) {
        native_copy(src,(dest-VRAM_BG_TILE*32)/2,words*2);
    }
}
void DMA_queueDmaFast(u16 t,void *s,u16 d,u16 n,u16 a) { DMA_queueDma(t,s,d,n,a); }
