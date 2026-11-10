/* Native Home parallax: BG3 line scroll via HDMA, software tile offsets for
 * vertical columns, and the original cave texture/zone variants. */
#include "parallax_native.h"
#include "gen/parallax_data.h"
#include "gen/assets.h"
#include "bg.h"

extern u8 par_hdma_pending[100];
u16 par_hdma_enabled;
volatile u8 par_dbg_mode,par_dbg_band;
static bool running;
static s16 prev_x,prev_y,voff;
extern s16 par_xoff[4],par_yoff[4],par_last_columns[4];
#define xoff par_xoff
#define yoff par_yoff
#define last_columns par_last_columns
extern u16 par_column_map[1024];
extern s16 par_lx[4],par_vs;
extern void native_par_columns(u16 force);
#define column_map par_column_map
static s16 content=-1;
extern const u8 snes_stars[];
extern const u16 snes_star_map[];

/* Speeds 2/16, 4/16, 8/16 and 12/16; avoid 32-bit compiler helpers.
 * Camera coordinates are positive and less than 4096. */
static s16 scaled(s16 v,u16 layer)
{
    if(layer==0) return v>>3;
    if(layer==1) return v>>2;
    if(layer==2) return v>>1;
    return (v*3)>>2;
}
static void columns(s16 y,bool force)
{
    u16 d; bool changed=force;
    for(d=0;d<4;d++) { par_lx[d]=(scaled(y,d)+yoff[d])&255; if(par_lx[d]!=last_columns[d]) changed=TRUE; }
    if(!changed) return;
    /* Only the 32 visible tile columns are needed. The MD view is cropped
     * by 32 pixels, so the first source column is 4 (depth column 2). */
    native_par_columns(force);
    for(d=0;d<4;d++) last_columns[d]=par_lx[d];
}
static void rows(s16 x,s16 y)
{
    s16 vs=(y>>1)+voff; u16 d;
    for(d=0;d<4;d++) par_lx[d]=scaled(x,d)+xoff[d]+32;
    par_vs=vs; native_par_rows();
    par_scroll_x=par_lx[par_star_row[(vs>>3)&31]];par_scroll_y=vs-1;
    par_hdma_enabled=1;
}
void par_native_frame(s16 x,s16 y,bool active)
{
    u16 d,i,m=1; s16 dx,dy,dv,off=0; bool force=FALSE;
    if(!active) {
        par_hdma_enabled=0;par_dbg_mode=0;
        if(running) {
            native_copy(snes_stars,0x3000,STAR_TILE_COUNT*16);
            native_copy(snes_star_map,0x7800,4096);
            par_map_register=0x79;
        }
        running=FALSE; content=-1; return;
    }
    if(!running) {
        running=TRUE; prev_x=0x7fff; voff=0;
        memset(xoff,0,sizeof(xoff));memset(yoff,0,sizeof(yoff));
    }
    dx=x-prev_x;dy=y-prev_y;
    if(prev_x!=0x7fff) {
        if(dx>16 || dx< -16 || dy>16 || dy< -16) {
            for(d=0;d<4;d++) {
                xoff[d]+=scaled(prev_x,d)-scaled(x,d);
                yoff[d]+=scaled(prev_y,d)-scaled(y,d);
            }
            dv=(prev_y>>1)-(y>>1);voff+=(dv+4)&~7;
        }
    }
    /* Identical camera and content need no table rebuild or map transfer. */
    if(x==prev_x && y==prev_y && content>=0) return;
    prev_x=x;prev_y=y;
    for(i=0;i<PAR_COL_LEGS;i++) {
        if(x!=par_col_legs[i].x) continue;
        if(y<par_col_legs[i].y0) continue;
        if(y>par_col_legs[i].y1) continue;
        m=2;break;
    }
    if(bg_zone_index()==10 && y==2064 && x>=1569 && x<=3679) {
        m=3;
        if(x>=1888) off=((x>3360?3360:x)-1888)/2;
    }
    par_dbg_mode=m;par_dbg_band=0;
    if(content!=m) {
        force=TRUE;content=m;par_hdma_enabled=0;
        if(m==2) {
            native_copy(native_star_tiles,0x3000,NATIVE_STAR_BYTES);
            par_map_register=0x78;
        } else {
            par_map_register=0x79;
            if(m==1) {
                native_copy(snes_stars,0x3000,STAR_TILE_COUNT*16);
                native_copy(snes_star_map,0x7800,4096);
            } else {
                native_copy(native_far_tiles,0x3000,256);
                for(i=0;i<1024;i++) column_map[i]=(i/32&3)*4+(i&3)+(5<<10);
                native_copy(column_map,0x7800,2048);
                native_copy(column_map,0x7c00,2048);
            }
        }
    }
    if(m==1) rows(x,y);
    else if(m==2) { columns(y,force);par_scroll_x=0;par_scroll_y=-1; }
    else { par_scroll_x=x-off+32;par_scroll_y=y-1; }
}
