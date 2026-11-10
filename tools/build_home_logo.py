"""Build the SNES subtitle from editable pixel-grid letter outlines.

Use the main logo's existing palette, without adding colours to the PPU.
The source polygons are intentionally aliased, matching the arcade artwork.
"""
import struct
from PIL import Image,ImageDraw,ImageFilter

COLS,ROWS=16,4
# Coordinates on a 24px cap-height grid. Each letter has the logo's forward
# lean, pointed terminals and broad white/cyan strokes.
LETTERS={
 'S':[(6,0),(29,0),(26,6),(12,6),(10,9),(24,9),(26,12),(23,24),(0,24),(3,18),(17,18),(18,15),(5,15),(2,12)],
 'N':[(0,24),(6,0),(13,0),(21,14),(24,0),(30,0),(24,24),(17,24),(9,10),(6,24)],
 'E':[(6,0),(30,0),(27,6),(12,6),(11,9),(25,9),(23,15),(10,15),(9,18),(26,18),(23,24),(0,24)],
}

def build_home_logo(root):
    """Return packed MD-format tiles/map for the existing native HUD loader."""
    # Recover pen numbers and palette selection from the source logo instead
    # of relying on an incidental global CGRAM index.
    raw=(root/'res/generated/fe_logo_tiles.bin').read_bytes()
    cells=struct.unpack('>256H',(root/'res/generated/fe_logo_map.bin').read_bytes())
    logo=Image.new('L',(256,64));pixels=logo.load();pal=None
    for i,e in enumerate(cells):
        if not e:continue
        pal=(e>>13)&1;tile=raw[((e&2047)-1)*32:(e&2047)*32]
        for y in range(8):
            for x in range(8):
                sx=7-x if e&0x800 else x;sy=7-y if e&0x1000 else y
                pixels[(i%32)*8+x,(i//32)*8+y]=(tile[sy*4+sx//2]>>(0 if sx&1 else 4))&15
    red=pixels[100,15];white=pixels[90,20]
    colours=set(logo.get_flattened_data())-{0,red,white}
    assert len(colours)==1,(red,white,colours)
    cyan=colours.pop()
    body=Image.new('L',(128,32));d=ImageDraw.Draw(body)
    for letter,ox in zip('SNES',(3,33,65,97)):
        d.polygon([(x+ox,y+3) for x,y in LETTERS[letter]],fill=255)
    # A two-pixel red keyline echoes the large logo's red surround,
    # without smoothing or new palette entries.
    outline=body.filter(ImageFilter.MaxFilter(5));canvas=Image.new('L',body.size)
    canvas.paste(red,mask=outline)
    b=body.load();p=canvas.load()
    for y in range(32):
        for x in range(128):
            if not b[x,y]:continue
            p[x,y]=white if y<=12 else cyan
            # A crisp white bevel follows the left-facing edges of the cyan
            # lower half, preserving the original logo's bright metal face.
            if y>12 and x>0 and not b[x-1,y]:p[x,y]=white
    tiles=[];lookup={};mapping=[]
    for ty in range(ROWS):
        for tx in range(COLS):
            tile=bytes((p[tx*8+x,ty*8+y]<<4)|p[tx*8+x+1,ty*8+y] for y in range(8) for x in range(0,8,2))
            if not any(tile):mapping.append(0);continue
            if tile not in lookup:lookup[tile]=len(tiles);tiles.append(tile)
            mapping.append(lookup[tile]+1|(pal<<13))
    assert len(tiles)<=64,'Home subtitle would overlap OBJ VRAM'
    return {'native_home_snes_tiles':b''.join(tiles),'native_home_snes_map':struct.pack('<64H',*mapping)},len(tiles)
