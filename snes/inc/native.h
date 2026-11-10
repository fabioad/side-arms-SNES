#ifndef SA_SNES_INC_NATIVE_H
#define SA_SNES_INC_NATIVE_H
#ifndef SIDEARMS_NATIVE_H
#define SIDEARMS_NATIVE_H
#include <genesis.h>
void native_copy(const void *src,u16 word,u16 bytes);
void native_flush(void);
void native_prepare_flush(void);
void native_wait_vblank(void);
void native_tile(const u8 *packed,u8 *planar);
void native_map(u16 plane,const u16 *src,u16 x,u16 y,u16 w,u16 h,u16 stride);
void native_hud_tile(u16 tile,const u8 *packed);
void native_hud_put(s16 col,s16 row,u16 entry);
void native_hud_clear(void);
void native_init(void);
void native_audio_frame(void);
void native_oam_clear(void);
void native_obj(u16 offset,s16 x,s16 y,u16 attributes,u16 large);
const void *native_offset(const void *base,u32 offset);
extern s16 native_bg_x,native_bg_y;
extern u16 native_bg_map_register;
extern volatile u16 native_dma_splits;
extern u16 native_boss_snapshot_valid;
void native_bg_cell(const u16 *tmpl,u16 slot,u16 entry,u16 index);
#endif

#endif
