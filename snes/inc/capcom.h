#ifndef SA_SNES_INC_CAPCOM_H
#define SA_SNES_INC_CAPCOM_H
#pragma once
#include <genesis.h>

/* Capcom splash before the boot/title screen, converted from
 * /home/fabio/Street Fighter II (USA).sfc (tools/build_capcom.py). */
#define CAPCOM_COLS 12
#define CAPCOM_ROWS 3
#define CAPCOM_COL 14
#define CAPCOM_ROW 12
#define CAPCOM_TILES 36
#define CAPCOM_FRAMES 266        /* 60 fps: music lead-in, fade in, hold, fade out */

extern const u8 fe_capcom_tiles[];
extern const u16 fe_capcom_map[];
extern const u16 fe_capcom_pal[];   /* CAPCOM_FRAMES x 16 Genesis colour words */

void hud_capcom(bool on);
void capcom_intro(void);
void sound_capcom(void);

#endif
