#include "native.h"
#include "game.h"
#include "hud.h"
#include "capcom.h"
#include "gen/assets.h"
#include "gen/frontend.h"
#include "native_home_logo.h"
typedef struct { u8 unused; } GlyphPool;
static GlyphPool game_pool;
static u16 glyph_keys[192],glyph_entries[192],glyph_count;
static u32 forced_rows;
static bool panel_active;
extern const u8 snes_font_tiles[];
extern u8 native_glyph_hint[16384];
static u16 glyph(GlyphPool *p,u16 code,u8 col)
{
    u16 key=(code&1023)|((u16)(col&63)<<10),i,t,index;
    u8 packed[32]; const u8 *s,*lut;
    (void)p;
    if(font_blank[code&1023]) return 0;
    if(code<256) {
        index=((u16)(col&63)<<8)+code;
        i=native_glyph_hint[index];
        if(i) { if(i<=glyph_count) { if(glyph_keys[i-1]==key) return glyph_entries[i-1]; } }
    } else for(i=0;i<glyph_count;i++) if(glyph_keys[i]==key) return glyph_entries[i];
    if(glyph_count>=192) return 0;
    t=++glyph_count;
    if(code<256) native_copy(native_offset(snes_font_tiles,((u32)(col&63)*256+code)*32),0x4000+t*16,32);
    else {
        s=native_offset(font_pens,(u32)(code&1023)*32); lut=txt_lut+(u16)(col&63)*256;
        for(i=0;i<32;i++) packed[i]=lut[s[i]];
        native_hud_tile(t,packed);
    }
    glyph_keys[t-1]=key; glyph_entries[t-1]=t|((2+txt_pal[col&63])<<10)|0x2000;
    if(code<256) native_glyph_hint[index]=t;
    return glyph_entries[t-1];
}
static GlyphPool *pool_for(s16 row) { (void)row; return &game_pool; }
static bool cell_ok(s16 col,s16 row) { return col>=0 && col<40 && row>=0 && row<28; }
extern void native_panel_put(s16 col,s16 row,u16 entry);
static void put(s16 col,s16 row,u16 entry)
{
    if(panel_active) { native_panel_put(col,row,entry); return; }
    native_hud_put(col,row,entry);
}
void hud_rows(u32 mask) { forced_rows=mask; }
u32 hud_rows_get(void) { return forced_rows; }
void hud_sprites(bool on) { (void)on; hud_game_pool_reset(); }
static void image(const u16 *m,u16 cols,u16 rows,s16 col,s16 row,const u8 *tiles,u16 n,u16 base)
{
    u16 i,r,c,e;
    native_copy(tiles,0x4000+base*16,n*32);
    for(r=0;r<rows;r++) for(c=0;c<cols;c++) {
        e=m[r*cols+c];
        put(col+c,row+r,e?((e&0x7ff)-1+base)|((2+((e>>13)&1))<<10)|0x2000|((e&0x0800)?0x4000:0)|((e&0x1000)?0x8000:0):0);
    }
}
void hud_logo(bool on,u16 tile)
{
    (void)tile;
    if(on) image(fe_logo_map,32,8,FE_LOGO_COL,FE_LOGO_ROW,fe_logo_tiles,FE_LOGO_TILES,169);
    else hud_clear(0xffULL<<FE_LOGO_ROW);
}
void hud_md(s16 col,s16 row,u16 tile) { (void)tile; image(fe_md_map,FE_MD_COLS,FE_MD_ROWS,col,row,fe_md_tiles,FE_MD_TILES,341); }
/* Tiles 384..447 contain the BG1 name table at VRAM $5800. The complete
 * subtitle fits in the 64 free characters above it, before OBJ at $6000. */
void hud_snes(s16 col,s16 row,u16 tile) { (void)tile; image(native_home_snes_map,HOME_SNES_COLS,HOME_SNES_ROWS,col,row,native_home_snes_tiles,HOME_SNES_TILES,448); }
void hud_capcom(bool on)
{
    if(on) image(fe_capcom_map,CAPCOM_COLS,CAPCOM_ROWS,CAPCOM_COL,CAPCOM_ROW,fe_capcom_tiles,CAPCOM_TILES,341);
    else hud_clear(0x07ULL<<CAPCOM_ROW);
}
void hud_screen_reset(void) { hud_clear(HUD_ROWS_ALL&~HUD_ROWS_GAME); }
