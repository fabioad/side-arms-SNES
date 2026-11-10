#ifndef SA_SNES_INC_NATIVE_WHEELS_H
#define SA_SNES_INC_NATIVE_WHEELS_H
#ifndef NATIVE_WHEELS_H
#define NATIVE_WHEELS_H
#include "native.h"
typedef struct { u16 type,home,count,x,y; const u16 *keys; const u8 *tiles; const u16 *maps; } NativeWheel;
extern const NativeWheel native_wheels[5];
#endif

#endif
