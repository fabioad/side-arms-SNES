#include "capcom.h"
#include "native.h"
#include "hud.h"
#include "video.h"
#include "palette.h"
#include "sound.h"
#include "gen/assets.h"

/* Boot splash: the Capcom logo from Street Fighter II (USA), shown once
 * before the port's title/boot screen.  The source logo fades in, holds and
 * fades out while its logo music plays; the palette steps once per frame. */
void capcom_intro(void)
{
    u16 f;

    video_set_layers(FALSE, FALSE);      /* black background, stars off */
    hud_screen_reset();
    hud_clear(HUD_ROWS_ALL);
    hud_capcom(TRUE);                    /* upload tiles + draw the 12x3 logo */
    sound_capcom();                      /* one-shot logo music */

    for (f = 0; f < CAPCOM_FRAMES; f++) {
        pal_load(48, fe_capcom_pal + f * 16, 16);
        native_prepare_flush();
        native_wait_vblank();
        native_flush();
        native_audio_frame();
        if (f >= 30 && (JOY_readJoypad(JOY_1) & (BUTTON_START | BUTTON_A | BUTTON_C))) break;
    }

    sound_stop_all();
    native_audio_frame();
    hud_capcom(FALSE);
    hud_clear(HUD_ROWS_ALL);
    pal_load(32, sprite_pal, 32);        /* restore the text/OBJ palettes */
    native_prepare_flush();
    native_wait_vblank();
    native_flush();
}
