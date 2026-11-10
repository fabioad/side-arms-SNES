#ifndef SA_SNES_INC_PARALLAX_NATIVE_H
#define SA_SNES_INC_PARALLAX_NATIVE_H
#ifndef PARALLAX_NATIVE_H
#define PARALLAX_NATIVE_H
#include "native.h"
extern const u16 native_star_phases[];
extern const u8 native_star_tiles[],native_far_tiles[];
#define NATIVE_STAR_BYTES 2928
extern u8 par_hdma_pending[100];
extern u16 par_hdma_enabled;
extern s16 par_scroll_x,par_scroll_y;
extern u16 par_map_register;
void native_parallax_commit(void);
void native_par_rows(void);
void native_par_column(u16 column,const u16 *src,u16 row);
void par_native_frame(s16 x,s16 y,bool active);
#endif

#endif
