#include "native.h"
#include "game.h"
#include "sound.h"
#include "hud.h"
#include "capcom.h"
volatile u32 frame_counter;
volatile u8 native_phase;
extern void native_clear_bss(void);
int main(void)
{
    native_clear_bss(); consoleInit(); native_init(); video_init(); sound_init();
    native_prepare_flush(); native_wait_vblank(); native_flush(); setScreenOn();
    capcom_intro();
    game_init();
    native_prepare_flush(); native_wait_vblank(); native_flush(); setScreenOn();
    for(;;) {
        native_phase=0; input_update(); native_phase=1; game_update();
        native_phase=2; game_draw(); native_phase=3; video_frame(); native_prepare_flush();
        native_phase=4; native_wait_vblank(); native_phase=5; native_flush();
        native_phase=6; native_audio_frame(); frame_counter++;
    }
    return 0;
}
