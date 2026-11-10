#include "native.h"
#include "bg.h"
#include "game.h"
#include "palette.h"
#include "sprites.h"
#include "hud.h"
#include "flow.h"
#include "gen/assets.h"
#include "gen/frontend.h"
#include "parallax_native.h"
#include "native_wheels.h"
#include "gen/boss_data.h"

#define SLOTS 47
static const Zone *zone;
static const ZoneVariant *variant;
static u16 zone_id=0xffff;
u16 native_bg_stamp,native_bg_misses;
#define stamp native_bg_stamp
#define misses native_bg_misses
u16 native_bg_keys[SLOTS],native_bg_used[SLOTS];
#define cache_key native_bg_keys
#define cache_used native_bg_used
extern u8 native_meta_slot[1024];
#define meta_slot native_meta_slot
u16 native_bg_map[2048];
static s16 camera_x,camera_y,last_x=-100,last_y=-100;
static s16 star_x,star_y;
static bool enabled=TRUE,stars_on=TRUE,home_mode;
static const BgFrames *frames;
static u16 frame_shown;
extern s16 native_zone_scan_x,native_zone_scan_y;
extern u16 native_zone_rect[5];
extern const u16 *native_zone_map;
extern u16 native_bg_frame_fallback;
#define zone_scan_x native_zone_scan_x
#define zone_scan_y native_zone_scan_y
extern const NativeWheel *native_wheel_current;
extern s16 native_wheel_shown;
extern volatile u16 native_wheel_active;
#define wheel native_wheel_current
#define wheel_shown native_wheel_shown
volatile u16 bg_partial_updates;

u16 native_bg_entry_slow(s16 x,s16 y)
{
    u16 xx=x&127,yy=y&127;
    if(frames && xx>=frames->cx && yy>=frames->cy && xx<frames->cx+frames->w && yy<frames->cy+frames->h)
        return frames->maps[frame_shown*frames->w*frames->h+(yy-frames->cy)*frames->w+xx-frames->cx];
    if(xx<zone->x0 || yy<zone->y0 || xx>=zone->x0+zone->w || yy>=zone->y0+zone->h) return 0xffff;
    return zone->map[(yy-zone->y0)*zone->w+xx-zone->x0];
}
extern u16 native_bg_entry(s16 x,s16 y);
#define entry_at native_bg_entry
extern u16 native_bg_slot(u16 meta);
static u16 acquire(u16 meta)
{
    u16 i,slot; const u8 *src;
    i=native_bg_slot(meta);
    if(i==0xffff) return 0xffff;
    if(!(i&0x8000)) return i;
    slot=i&0x7fff;
    if(meta<zone->metas) src=native_offset(zone->tiles,(u32)meta*512);
    else if(frames && meta-zone->metas<frames->nextra) src=native_offset(frames->extra_tiles,(u32)(meta-zone->metas)*512);
    else if(variant && meta-zone->metas<variant->nextra) src=native_offset(variant->extra_tiles,(u32)(meta-zone->metas)*512);
    else return 0xffff;
    native_copy(src,(16+slot*16)*16,512);
    return slot;
}

static void render_cell(s16 x,s16 y,bool partial)
{
    u16 e,meta,slot,sy,px,py,index;
    const u16 *tmpl;
    e=entry_at(x,y);
    slot=0xffff; tmpl=0;
    if(e!=0xffff) {
        meta=e&0xfff; slot=acquire(meta);
        if(slot!=0xffff) {
            if(meta<zone->metas) tmpl=native_offset(zone->tmpl,(u32)meta*32);
            else if(frames) tmpl=native_offset(frames->extra_tmpl,(u32)(meta-zone->metas)*32);
            else tmpl=native_offset(variant->extra_tmpl,(u32)(meta-zone->metas)*32);
        }
    }
    px=((u16)x*4)&63;py=((u16)y*4)&31;
    index=(px&32?1024:0)+py*32+(px&31);
    native_bg_cell(tmpl,slot,e,index);
    if(partial) for(sy=0;sy<4;sy++) native_copy(native_bg_map+index+sy*32,0x3800+index+sy*32,8);

}
static void render(void)
{
    s16 x,y,x0=(camera_x+32)>>5,y0=camera_y>>5;
    bool full=last_x!=x0 && last_x!=x0-1 && last_x!=x0+1;
    u16 e,meta;
    if(last_y!=y0 && last_y!=y0-1 && last_y!=y0+1) full=TRUE;
    stamp++;
    /* Pin every currently visible pattern before evicting any previous one. */
    for(y=y0;y<=y0+7;y++) for(x=x0;x<=x0+8;x++) {
        e=entry_at(x,y); meta=e&0xfff;
        if(meta<1024 && meta_slot[meta]) cache_used[meta_slot[meta]-1]=stamp;
    }
    if(full) {
        memset(native_bg_map,0,sizeof(native_bg_map));
        for(y=y0;y<=y0+7;y++) for(x=x0;x<=x0+8;x++) render_cell(x,y,FALSE);
        native_copy(native_bg_map,0x3800,4096);
    } else {
        bg_partial_updates++;
        if(x0!=last_x) {
            x=x0>last_x?x0+8:x0;
            for(y=y0;y<=y0+7;y++) render_cell(x,y,TRUE);
        }
        if(y0!=last_y) {
            y=y0>last_y?y0+7:y0;
            for(x=x0;x<=x0+8;x++) if(x0==last_x || x!=(x0>last_x?x0+8:x0)) render_cell(x,y,TRUE);
        }
    }
}
void bg_init(void) { memset(cache_key,255,sizeof(cache_key));wheel=0;wheel_shown=-1;native_wheel_active=0;native_bg_frame_fallback=0;zone_scan_x=zone_scan_y=-1; }
void bg_set_zone(u16 z)
{
    if(z>=ZONE_COUNT) return;
    variant=home_mode?zone_home[z]:0;
    zone=variant?&variant->z:&zones[z]; zone_id=z;
    memcpy(native_zone_rect,zone,10);native_zone_map=zone->map;
    memset(cache_key,255,sizeof(cache_key)); memset(meta_slot,0,sizeof(meta_slot)); pal_load(0,zone->pal,32);
    last_x=-100; last_y=-100;
}
void bg_set_camera(s16 x,s16 y) { camera_x=x; camera_y=y; }
void bg_enable(bool on) { enabled=on; last_x=-100; }
void bg_set_home(bool on) { if(home_mode==on) return; home_mode=on; if(zone_id<ZONE_COUNT) bg_set_zone(zone_id); }
bool bg_is_home(void) { return home_mode; }
bool bg_is_enabled(void) { return enabled; }
u16 bg_zone_index(void) { return zone_id; }
void bg_view(s16 *x,s16 *y) { *x=camera_x; *y=camera_y; }
void bg_scroll_external(bool on) { (void)on; }
bool bg_band_lines(s16 *a,s16 *b,s16 *c) { (void)a;(void)b;(void)c; return FALSE; }
u16 bg_cache_misses(void) { return misses; }
u16 bg_reserve_blocks(u16 n,u16 *tiles) { (void)n;(void)tiles; return 0; }
void bg_release_blocks(void) {}
void bg_frames_begin(const BgFrames *f)
{
    u16 i,j,key;
    frames=f; frame_shown=0; bg_set_zone(f->zone); wheel=0;wheel_shown=-1;
    for(i=0;i<3;i++) {
        if(f==wheel_info[i].frames) { j=i*2; if(i==2) j=4; wheel=&native_wheels[j]; break; }
        if(f==wheel_info[i].frames_home) { wheel=&native_wheels[i*2+1]; break; }
    }
    native_wheel_active=wheel!=0;
    native_bg_frame_fallback=wheel==0;
    if(!wheel) return;
    /* All three animation frames share the same fixed VRAM slots. */
    for(i=0;i<wheel->count;i++) {
        key=wheel->keys[i];cache_key[i]=key;meta_slot[key]=i+1;cache_used[i]=stamp;
    }
    native_copy(wheel->tiles,0x100,wheel->count*512);
}
bool bg_frames_ready(void) { return TRUE; }
void bg_frames_show(u16 n) { if(frames && n<frames->nframes && n!=frame_shown) { frame_shown=n; if(!wheel) last_x=-100; } }
void bg_frames_end(void) { frames=0;wheel=0;native_wheel_active=0;native_bg_frame_fallback=0; if(zone_id<ZONE_COUNT) bg_set_zone(zone_id); last_x=-100; }
void bg_update(void)
{
    u16 z; s16 x,y;
    if(!enabled) return;
    if(wheel) {
        if(wheel_shown!=frame_shown) {
            const u16 *image=wheel->maps+frame_shown*1024;
            native_copy(image,0x3800,2048);
            wheel_shown=frame_shown;
        }
        native_bg_x=0;native_bg_y=-1;native_bg_map_register=0x38;
        return;
    }
    x=(camera_x+160)>>5; y=(camera_y+112)>>5;
    if(!frames) if(x!=zone_scan_x || y!=zone_scan_y) {
        const Zone *candidate=zones;
        zone_scan_x=x;zone_scan_y=y;
        for(z=0;z<ZONE_COUNT;z++,candidate++) {
            if(x<candidate->x0) continue; if(y<candidate->y0) continue;
            if(x>=candidate->x0+candidate->w) continue; if(y>=candidate->y0+candidate->h) continue;
            if(z!=zone_id) bg_set_zone(z);break;
        }
    }
    if(zone && (((camera_x+32)>>5)!=last_x || (camera_y>>5)!=last_y)) {
        render(); last_x=(camera_x+32)>>5; last_y=camera_y>>5;
    }
    native_bg_x=camera_x+32;native_bg_y=camera_y-1;native_bg_map_register=0x39;
}
void video_set_camera(s16 x,s16 y) { bg_set_camera(x,y); }
void video_set_layers(bool bg,bool stars)
{
    bg_enable(bg); stars_on=stars;
    if(bg) bgSetEnable(1); else bgSetDisable(1);
    if(stars) bgSetEnable(2); else bgSetDisable(2);
}
void video_stars_step(s16 x,s16 y) { star_x+=x; star_y+=y; }
void video_set_parallax(bool on) { bg_set_home(on); }
void video_frame(void)
{
    bg_update();
    par_native_frame(camera_x,camera_y,home_mode && enabled && stars_on);
    if(!home_mode || !enabled || !stars_on) if(stars_on) { par_scroll_x=star_x+32;par_scroll_y=star_y-1; }
}
extern const u8 snes_stars[];
extern const u16 snes_star_map[];
void video_init(void)
{
    bg_init(); spr_init(); hud_init();
    par_scroll_x=32;par_scroll_y=-1;par_map_register=0x79;
    native_bg_x=0;native_bg_y=-1;native_bg_map_register=0x39;
    native_copy(snes_stars,0x3000,STAR_TILE_COUNT*16);
    native_copy(snes_star_map,0x7800,4096);
    pal_load(32,sprite_pal,32);
}

static s16 scene_loaded=-1,scene_pending=-1,scene_shown=-1;
static s16 scene_visible=-1;
static u16 scene_pos;
void scene_load_set(u16 n) { if(scene_loaded!=n && scene_pending!=n) { scene_pending=n; scene_pos=0; scene_loaded=-1; scene_visible=-1; bg_enable(FALSE); } }
bool scene_ready(void) { return scene_pending<0 && scene_loaded>=0; }
void scene_show(u16 n) { if(scene_visible!=n) scene_shown=n; }
void scene_off(void) { scene_shown=scene_visible=-1; bgSetDisable(1); }
void scene_invalidate(void) { scene_loaded=scene_pending=scene_shown=scene_visible=-1; }
void scene_update(void)
{
    const FeSceneSet *s; u16 n;
    if(scene_pending>=0) {
        s=&fe_scene_sets[scene_pending]; n=s->count-scene_pos; if(n>96) n=96;
        native_copy(native_offset(s->tiles,(u32)scene_pos*32),(16+scene_pos)*16,n*32); scene_pos+=n;
        if(scene_pos>=s->count) { pal_load(0,s->pal,32); scene_loaded=scene_pending; scene_pending=-1; }
        return;
    }
    if(scene_shown<0 || scene_loaded!=fe_scenes[scene_shown].set) return;
    native_copy(fe_scenes[scene_shown].map,0x3800,32*28*2);
    native_bg_x=0;native_bg_y=-1;native_bg_map_register=0x38;
    bgSetEnable(1); scene_visible=scene_shown; scene_shown=-1;
}
void stage_video_on(void)
{
    u8 blank[32]; memset(blank,0,32); native_copy(blank,0,32);
    scene_invalidate(); last_x=-100; video_set_layers(TRUE,TRUE);
}
void stage_sprites_on(void) { spr_init(); }
