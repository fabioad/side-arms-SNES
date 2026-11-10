#include "native.h"
#include "sound.h"
#include "res/sound_meta.h"
extern char SOUNDBANK__0;
/* Modules are converted from the user's existing arcade sound extractions. */
static const u8 commands[]={0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x29,0x2a,0x2c,0x2e,0x33,0x34,0x35,0x36,0x38,0x20,0x32,0x3b};
static u8 pending,last_module=0xff,fx_queue[16],fx_count;
/* last_module: low 5 bits = loaded module, bits 5-6 = one-shot playback state.
 * The arcade clear jingle ($2A) ends after one pass, but SNESMOD restarts a
 * module when its sequence reaches the $FF end marker, so stop it on the wrap. */
#define MODULE_INDEX   (last_module&0x1f)
#define ONESHOT_STATE  ((last_module>>5)&3)
#define SET_ONESHOT(v) (last_module=(last_module&0x9f)|(((u8)(v))<<5))
static bool intro_loaded;
volatile u16 audio_step;
volatile u16 audio_budget_rejected;
volatile u8 audio_last_command;
volatile u16 audio_flush_timeouts;
static bool audio_faulted;
extern volatile u8 spc_fread,spc_fwrite;
static void flush_messages(void)
{
    u16 guard;
    /* This SDK's public spcFlush uses JSR on an RTL epilogue and corrupts
     * the CPU return stack. Its public spcProcess entry is safe to call. */
    for(guard=0;guard<1024;guard++) {
        if(spc_fread==spc_fwrite) return;
        spcProcess();
    }
    audio_flush_timeouts++;audio_faulted=TRUE;
}
static void load_effects(bool intro)
{
    u16 j;
    intro_loaded=FALSE;
    for(j=0;j<6;j++) { audio_step=0x200+j;spcLoadEffect(j);WaitForVBlank(); }
    audio_step=0x207;spcLoadEffect(7);WaitForVBlank();
    if(intro) { audio_step=0x206;spcLoadEffect(6);WaitForVBlank();intro_loaded=TRUE; }
}
void z80_idle(void) {}
void sound_init(void)
{
    /* Module 20 is the Capcom splash sting; it is preloaded so the splash can
     * start it immediately (no module-load hitch in the 60 fps animation). */
    audio_step=1; spcBoot(); audio_step=2; spcSetBank(&SOUNDBANK__0); audio_step=3; spcLoad(20); last_module=20;
    load_effects(FALSE);audio_step=4;
}
void sound_stop_all(void) { spcStop();pending=0;fx_count=0;SET_ONESHOT(0); }
void sound_capcom(void) { pending=0x3b; }
void sound_command(u8 cmd)
{
    if(audio_faulted) return;
    if(cmd==0xff) return;
    cmd&=0x3f;
    if(!cmd) { sound_stop_all();return; }
    if(cmd>=0x39) { spcStop();pending=0;SET_ONESHOT(0);return; }
    if(cmd>=0x20) { pending=cmd; return; }
    if(cmd==0x10 || cmd==0x16 || cmd==0x19 || cmd==0x1f) { fx_count=0;return; }
    if(fx_count<16) fx_queue[fx_count++]=cmd;
}
static void effect(u8 cmd)
{
    u8 i=0,pitch=2;
    if(cmd==2) i=5;
    else if(cmd==4 || cmd==0x11 || cmd==0x12 || cmd==0x14 || cmd==0x15 || cmd==0x17) i=1;
    else if(cmd==5) i=6;
    else if(cmd==0xf) i=2;
    else if(cmd==0x1d) i=3;
    else if(cmd==0x13) i=4;
    else if(cmd==0x0c || cmd==0x0d) { if(!intro_loaded) return;i=7;pitch=1; }
    spcEffect(pitch,i,0xc8);
}
void native_audio_frame(void)
{
    u16 i,need;bool intro;
    if(audio_faulted) { pending=fx_count=0;return; }
    if(pending) {
        audio_last_command=pending;
        SET_ONESHOT(pending==0x2a || pending==0x3b);
        for(i=0;i<sizeof(commands);i++) if(commands[i]==pending) {
            intro=pending==0x20;need=NATIVE_EFFECT_BYTES+(intro?NATIVE_INTRO_BYTES:0);
            if(native_music_bytes[i+1]>NATIVE_MUSIC_LIMIT-need) {
                audio_step=0x500+pending;audio_budget_rejected++;spcStop();break;
            }
            if(MODULE_INDEX!=i+1) {
                audio_step=0x100+pending; spcStop(); spcLoad(i+1); last_module=(last_module&0x60)|(i+1);
                load_effects(intro);
            }
            audio_step=0x300+pending; spcSetModuleVolume(255); spcPlay(0); break;
        }
        pending=0;
    }
    for(i=0;i<fx_count;i++) effect(fx_queue[i]);
    fx_count=0;
    /* QueueMessage has no full check. Drain every batch before another game
     * frame can wrap its 256-byte FIFO and turn payload bytes into commands. */
    audio_step=0x600+audio_last_command;flush_messages();spcProcess();audio_step=0x700+audio_last_command;
    /* ONESHOT_STATE: 1 = wait for the new module to start at order 0,
     *                2 = at order 0, 3 = advanced; stop when it wraps back to 0. */
    if(ONESHOT_STATE && !audio_faulted) {
        u8 pos=spcGetMusicPosition();
        if(ONESHOT_STATE==1) { if(!pos) SET_ONESHOT(2); }
        else if(ONESHOT_STATE==2) { if(pos) SET_ONESHOT(3); }
        else if(!pos) {
            SET_ONESHOT(0);audio_step=0x710;spcStop();
            flush_messages();spcProcess();
        }
    }
}
