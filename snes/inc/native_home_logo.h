#ifndef SA_SNES_INC_NATIVE_HOME_LOGO_H
#define SA_SNES_INC_NATIVE_HOME_LOGO_H
#ifndef NATIVE_HOME_LOGO_H
#define NATIVE_HOME_LOGO_H
#include "native.h"
#define HOME_SNES_COLS 16
#define HOME_SNES_ROWS 4
#define HOME_SNES_TILES 50
extern const u8 native_home_snes_tiles[];
extern const u16 native_home_snes_map[];
void hud_snes(s16 col,s16 row,u16 tile);
#endif

#endif
