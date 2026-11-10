#include "game.h"
#include <stddef.h>
/* Cartridge ABI metadata for tests: no guessed struct packing. */
const u16 native_player_layout[]={
    sizeof(Player),offsetof(Player,x),offsetof(Player,y),offsetof(Player,invuln),
    offsetof(Player,lives),offsetof(Player,shots),sizeof(Shot),offsetof(Shot,active)
};
