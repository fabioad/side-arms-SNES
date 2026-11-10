#include "native_wheels.h"
extern const u16 native_wheel0_keys[];
extern const u8 native_wheel0_tiles[];
extern const u16 native_wheel0_maps[];
extern const u16 native_wheel0h_keys[];
extern const u8 native_wheel0h_tiles[];
extern const u16 native_wheel0h_maps[];
extern const u16 native_wheel1_keys[];
extern const u8 native_wheel1_tiles[];
extern const u16 native_wheel1_maps[];
extern const u16 native_wheel1h_keys[];
extern const u8 native_wheel1h_tiles[];
extern const u16 native_wheel1h_maps[];
extern const u16 native_wheel2_keys[];
extern const u8 native_wheel2_tiles[];
extern const u16 native_wheel2_maps[];
const NativeWheel native_wheels[5] = {
{0,0,44,864,272,native_wheel0_keys,native_wheel0_tiles,native_wheel0_maps},
{0,1,44,864,272,native_wheel0h_keys,native_wheel0h_tiles,native_wheel0h_maps},
{1,0,36,2912,2320,native_wheel1_keys,native_wheel1_tiles,native_wheel1_maps},
{1,1,36,2912,2320,native_wheel1h_keys,native_wheel1h_tiles,native_wheel1h_maps},
{2,0,40,2912,2576,native_wheel2_keys,native_wheel2_tiles,native_wheel2_maps},
};
