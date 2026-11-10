#ifndef SA_SNES_INC_GENESIS_H
#define SA_SNES_INC_GENESIS_H
#ifndef SIDEARMS_SNES_GENESIS_H
#define SIDEARMS_SNES_GENESIS_H
/* Narrow source-compatibility interface; all hardware implementation is SNES. */
#include <snes.h>
#include <string.h>
#include <stdlib.h>
void *native_memset(void *dst,int value,u16 count);
#define memset native_memset
/* SGDK serializes booleans as 0/1; PVSnesLib's TRUE is 255. */
#undef TRUE
#define TRUE 1
#undef true
#define true 1
#define inline
#define GET_VCOUNTER 0
#define PAL0 0
#define PAL1 1
#define PAL2 2
#define PAL3 3
#define DMA_VRAM 0
#define DMA 0
#define DMA_QUEUE 0
#define DMA_QUEUE_COPY 0
#define BG_A 1
#define BG_B 0
#define WINDOW 2
#define TILE_ATTR_FULL(p,pr,v,h,t) (((p)<<13)|((pr)<<15)|((v)<<12)|((h)<<11)|(t))
#define JOY_1 0
#define JOY_2 1
#define JOY_TYPE_PAD6 1
#define BUTTON_UP 1
#define BUTTON_DOWN 2
#define BUTTON_LEFT 4
#define BUTTON_RIGHT 8
#define BUTTON_A 16
#define BUTTON_B 32
#define BUTTON_C 64
#define BUTTON_START 128
#define BUTTON_X 256
#define BUTTON_Y 512
#define BUTTON_Z 1024
#define BUTTON_MODE 2048
u16 JOY_readJoypad(u16 port);
u16 JOY_getJoypadType(u16 port);
void DMA_queueDma(u16 type,void *src,u16 dest,u16 words,u16 step);
void DMA_queueDmaFast(u16 type,void *src,u16 dest,u16 words,u16 step);
void SRAM_enable(void);
void SRAM_enableRO(void);
void SRAM_disable(void);
u8 SRAM_readByte(u16 offset);
u32 SRAM_readLong(u16 offset);
void SRAM_writeByte(u16 offset,u8 value);
void SRAM_writeLong(u16 offset,u32 value);
u32 native_row_bit(u16 row);
#endif

#endif
