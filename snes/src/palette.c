#include "palette.h"
#include "gen/assets.h"
static u16 source[64],shown[64];
u8 color_mode=COLOR_VIVID;
extern void native_palette(u16 index,const u16 *src,u16 n);
void pal_load(u16 index,const u16 *cols,u16 count)
{
    u16 i,c,k;
    memcpy(source+index,cols,count*2);
    for(i=index;i<index+count;i++) {
        c=source[i]; k=((c>>1)&7)|(((c>>5)&7)<<3)|(((c>>9)&7)<<6);
        shown[i]=color_mode==COLOR_VIVID?vivid_lut[k]:c;
    }
    native_palette(index,shown+index,count);
}
void pal_set_mode(u8 mode) { color_mode=mode; pal_load(0,source,64); }
