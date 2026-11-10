.INCLUDE "hdr.asm"
.BASE $00
.RAMSECTION "port_bss" BANK $7e SLOT 2 ORGA $2000 FORCE KEEP
.ENDS
.BASE $c0
.SECTION "native_oam" SUPERFREE
; Clear the packed OAM table once. Every native_obj call owns a distinct
; entry until the next clear, allowing high-table bits to be ORed in.
native_oam_clear:
    php
    phx
    rep #$30
    lda.l native_spr_count
    and #255
    beq native_oam_high_clear
    asl a
    asl a
    tax
    dex
    dex
    dex
    dex
    lda #$e000
-   sta.l oamMemory,x
    dex
    dex
    dex
    dex
    bpl -
native_oam_high_clear:
    ldx #30
    lda #0
-   sta.l oamMemory+512,x
    dex
    dex
    bpl -
    plx
    plp
    rtl

; 816-tcc stack parameters: offset, x, y, tile/attributes, large.
; Preserve signed X's ninth bit; SDK oamSetEx(OBJ_SHOW) clears that bit.
native_obj:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    tax
    lda 12,s
    sep #$20
    sta.l oamMemory,x
    rep #$20
    lda 14,s
    sep #$20
    sta.l oamMemory+1,x
    rep #$20
    lda 16,s
    sta.l oamMemory+2,x
    lda 10,s
    and #12
    tay
    lda 12,s
    and #$0100
    beq native_obj_no_x
    iny
native_obj_no_x:
    lda 18,s
    and #1
    beq native_obj_no_large
    iny
    iny
native_obj_no_large:
    lda 10,s
    lsr a
    lsr a
    lsr a
    lsr a
    tax
    phk
    plb
    sep #$20
    lda native_obj_mask,y
    ora.l oamMemory+512,x
    sta.l oamMemory+512,x
    rep #$30
    ply
    plx
    plb
    plp
    rtl
native_obj_mask:
    .db 0,1,2,3,0,4,8,12,0,16,32,48,0,64,128,192
.ENDS
.BASE $00
.RAMSECTION "native_cache_indices" BANK $7f SLOT 3 KEEP
native_sprite_hint dsb 32768
native_meta_slot dsb 1024
.ENDS
.BASE $C0
.SECTION "native_clear_bss" SUPERFREE
native_clear_bss:
    php
    phb
    rep #$30
    pea $7e7e
    plb
    plb
    ldx #((SECTIONEND_port_bss-SECTIONSTART_port_bss+1)&$fffe)
    beq +
-   dex
    dex
    stz.w $2000,x
    bne -
+   plb
    plp
    rtl
.ENDS
.SECTION "native_offset" SUPERFREE
; 816-tcc's pointer + u32 expression drops the high-word result.
; Explicit full-width HiROM address arithmetic, returned in the pointer ABI.
native_offset:
    php
    rep #$30
    clc
    lda 5,s
    adc 9,s
    sta.b tcc__r0
    lda 7,s
    adc 11,s
    sta.b tcc__r0h
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_vblank_dma" SUPERFREE
; Flush prepared transfers in bounded VBlank batches. X is the descriptor's
; byte offset, Y is its conservative DMA-byte cost (including setup overhead).
; Keep the display enabled while large scene loads span several VBlanks.
native_flush:
    php
    phb
    phx
    phy
    rep #$30
    lda #0
    sep #$20
    pha
    plb
    rep #$20
    ldx #0
    ldy #0
native_flush_next:
    txa
    lsr a
    cmp.l queue_count
    bcc +
    brl native_flush_finish
+   lda.l queue_size,x
    sta.b tcc__r1
    tya
    clc
    adc.b tcc__r1
    adc #96
    cmp.l native_dma_budget
    bcc native_flush_transfer
    beq native_flush_transfer
    tya
    sta.b tcc__r2
    lda.l native_dma_budget
    sec
    sbc.b tcc__r2
    bcc native_flush_wait
    sec
    sbc #96
    bcc native_flush_wait
    and #$fffe
    cmp #128
    bcc native_flush_wait
    sta.b tcc__r1
    tya
    clc
    adc.b tcc__r1
    adc #96
    bra native_flush_transfer
native_flush_wait:
    sep #$20
    lda.l $4212
    bmi +
    rep #$20
    lda.l native_dma_late
    inc a
    sta.l native_dma_late
+   rep #$20
    jsl native_next_vblank
    ldy #0
    brl native_flush_next
native_flush_transfer:
    tay
    lda.l queue_dest,x
    sta $2116
    lda.b tcc__r1
    sta $4305
    lda.l queue_off,x
    sta $4302
    lda #$1801
    sta $4300
    sep #$20
    lda.l queue_bank,x
    sta $4304
    lda.l queue_bank+1,x
    sta $2115
    lda #1
    sta $420b
    rep #$20
    lda.b tcc__r1
    cmp.l queue_size,x
    beq native_flush_advance
    lda.l queue_size,x
    sec
    sbc.b tcc__r1
    sta.l queue_size,x
    lda.l queue_off,x
    clc
    adc.b tcc__r1
    sta.l queue_off,x
    lda.b tcc__r1
    lsr a
    sta.b tcc__r2
    lda.l queue_bank,x
    and #$0100
    beq native_flush_dest
    lda.b tcc__r2
    asl a
    asl a
    asl a
    asl a
    asl a
    sta.b tcc__r2
native_flush_dest:
    lda.l queue_dest,x
    clc
    adc.b tcc__r2
    sta.l queue_dest,x
    lda.l native_dma_splits
    inc a
    sta.l native_dma_splits
    brl native_flush_next
native_flush_advance:
    inx
    inx
    brl native_flush_next
native_flush_finish:
    sep #$20
    lda.l paldirty
    beq native_flush_oam
    stz $2121
    rep #$20
    lda #$2200
    sta $4300
    lda #palram
    sta $4302
    lda #512
    sta $4305
    sep #$20
    lda #:palram
    sta $4304
    lda #1
    sta $420b
    lda #0
    sta.l paldirty
native_flush_oam:
    rep #$30
    jsl oamUpdate
    jsl native_parallax_commit
    sep #$20
    lda.l $4212
    bmi +
    rep #$20
    lda.l native_dma_late
    inc a
    sta.l native_dma_late
+   rep #$30
    lda #0
    sta.l queue_count
    sta.l queue_used
    sta.l queue_total
    lda.l snes_vblank_count
    sta.l native_last_vblank
    ply
    plx
    plb
    plp
    rtl
.ENDS

.BASE $00
.RAMSECTION "parallax_hdma_buffer" BANK $7f SLOT 3 KEEP
par_hdma_active dsb 100
par_hdma_pending dsb 100
par_column_map dsb 2048
par_xoff dsb 8
par_yoff dsb 8
par_last_columns dsb 8
par_lx dsb 8
par_vs dsb 2
par_scroll_x dsb 2
par_scroll_y dsb 2
par_map_register dsb 2
native_bg_x dsb 2
native_bg_y dsb 2
native_bg_map_register dsb 2
native_wheel_current dsb 4
native_wheel_shown dsb 2
native_wheel_active dsb 2
native_zone_scan_x dsb 2
native_zone_scan_y dsb 2
native_zone_rect dsb 10
native_zone_map dsb 4
native_bg_frame_fallback dsb 2
native_dma_splits dsb 2
native_sprite_missing_keys dsb 512
native_big_missing_keys dsb 512
native_sprite_missing_count dsb 2
native_big_missing_count dsb 2
.ENDS
.BASE $C0
.SECTION "parallax_commit" SUPERFREE
native_par_column:
    php
    phb
    phx
    phy
    rep #$30
    lda 12,s
    sta.b tcc__r1
    lda 14,s
    sta.b tcc__r1h
    lda 10,s
    asl a
    tax
    lda 16,s
    and #31
    asl a
    tay
    lda #32
    sta.b tcc__r2
par_column_loop:
    lda [tcc__r1],y
    sta.l par_column_map,x
    txa
    clc
    adc #64
    tax
    tya
    inc a
    inc a
    and #63
    tay
    dec.b tcc__r2
    bne par_column_loop
    ply
    plx
    plb
    plp
    rtl

native_par_rows:
    php
    phb
    phx
    phy
    rep #$30
    sep #$20
    lda #:par_hdma_pending
    pha
    plb
    rep #$20
    lda.w par_vs
    lsr a
    lsr a
    lsr a
    and #31
    sta.b tcc__r0
    lda.w par_vs
    and #7
    eor #7
    inc a
    sta.b tcc__r1
    lda #224
    sta.b tcc__r2
    ldy #0
par_rows_loop:
    lda.b tcc__r1
    sep #$20
    sta.w par_hdma_pending,y
    rep #$20
    ldx.b tcc__r0
    lda.l par_star_row,x
    and #255
    asl a
    tax
    lda.w par_lx,x
    sta.w par_hdma_pending+1,y
    iny
    iny
    iny
    lda.b tcc__r0
    inc a
    and #31
    sta.b tcc__r0
    lda.b tcc__r2
    sec
    sbc.b tcc__r1
    beq par_rows_end
    sta.b tcc__r2
    cmp #8
    bcc +
    lda #8
+   sta.b tcc__r1
    bra par_rows_loop
par_rows_end:
    sep #$20
    lda #0
    sta.w par_hdma_pending,y
    rep #$30
    ply
    plx
    plb
    plp
    rtl

; Snapshot the next HDMA table only after all graphics have been committed.
; Channel 7 is reserved for BG3 horizontal offsets (two writes to $2111).
; Intermediate VBlanks retain the previous immutable table.
native_parallax_commit:
    php
    phx
    rep #$30
    lda.l par_hdma_enabled
    beq par_hdma_off
    ldx #98
-   lda.l par_hdma_pending,x
    sta.l par_hdma_active,x
    dex
    dex
    bpl -
    lda #$1102
    sta.l $4370
    lda #par_hdma_active
    sta.l $4372
    sep #$20
    lda #:par_hdma_active
    sta.l $4374
    lda #$80
    sta.l $420c
    bra par_hdma_done
par_hdma_off:
    sep #$20
    lda #0
    sta.l $420c
par_hdma_done:
    lda.l native_bg_map_register
    sta.l $2108
    lda.l native_bg_x
    sta.l $210f
    lda.l native_bg_x+1
    sta.l $210f
    lda.l native_bg_y
    sta.l $2110
    lda.l native_bg_y+1
    sta.l $2110
    ; The previous frame's HDMA can overwrite scroll writes made by the
    ; simulation. Commit both registers after disabling/replacing that table.
    lda.l par_map_register
    sta.l $2109
    lda.l par_scroll_x
    sta.l $2111
    lda.l par_scroll_x+1
    sta.l $2111
    lda.l par_scroll_y
    sta.l $2112
    lda.l par_scroll_y+1
    sta.l $2112
    rep #$30
    plx
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_enemy_move" SUPERFREE
; Enemy's fixed layout is 40 bytes. Move by signed dy/dx, then apply the
; arcade's wrapped Y and raw X bounds. Same result as the original C move().
native_enemy_move:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r1
    lda 12,s
    sta.b tcc__r1h
    lda 14,s
    and #255
    sta.b tcc__r0h
    jsr native_enemy_move_body
    ply
    plx
    plb
    plp
    rtl
native_enemy_move_fast:
    sta.b tcc__r0h
    lda.b tcc__r4
    sta.b tcc__r1
    lda.b tcc__r4h
    sta.b tcc__r1h
    jsr native_enemy_move_body
    rtl
native_enemy_move_body:
    ldy #8
    lda #0
    sep #$20
    lda [tcc__r1],y
    rep #$20
    cmp #128
    bcc +
    ora #$ff00
+   ldy #6
    clc
    adc [tcc__r1],y
    clc
    adc #16
    and #255
    cmp #241
    bcc native_enemy_y_ok
    cmp #248
    bcs native_enemy_check_small
    bra native_enemy_kill
native_enemy_check_small:
    tax
    lda.b tcc__r0h
    and #255
    beq native_enemy_kill
    txa
native_enemy_y_ok:
    cmp #248
    bcc +
    ora #$ff00
+   sec
    sbc #16
    sta [tcc__r1],y
    ldy #9
    lda #0
    sep #$20
    lda [tcc__r1],y
    rep #$20
    cmp #128
    bcc +
    ora #$ff00
+   ldy #4
    clc
    adc [tcc__r1],y
    sta [tcc__r1],y
    clc
    adc #96
    cmp #448
    bcs native_enemy_kill
    tax
    lda.b tcc__r0h
    and #255
    beq native_enemy_small_x
    txa
    cmp #32
    bcc native_enemy_kill
    bra native_enemy_moved
native_enemy_small_x:
    txa
    cmp #48
    bcc native_enemy_kill
native_enemy_moved:
    lda #1
    sta.b tcc__r0
    bra native_enemy_move_return
native_enemy_kill:
    pei (tcc__r1h)
    pei (tcc__r1)
    jsl en_remove
    pla
    pla
    stz.b tcc__r0
native_enemy_move_return:
    rts
.ENDS

.BASE $00
.RAMSECTION "native_bands_ram" APPENDTO "port_bss"
native_enemy_band dsb 10
.ENDS
.BASE $C0
.SECTION "native_enemy_bands" SUPERFREE
native_enemy_bands:
    php
    phx
    phy
    rep #$30
    lda #0
    ldx #8
-   sta.l native_enemy_band,x
    dex
    dex
    bpl -
    lda #:players
    sta.b tcc__r1h
    lda #players
    sta.b tcc__r1
    lda #2
    sta.b tcc__r3
    sta.b tcc__r5
    lda #284
    sta.b tcc__r4
    jsr native_bands_pool
    lda #:en_big
    sta.b tcc__r1h
    lda #en_big
    sta.b tcc__r1
    lda #9
    sta.b tcc__r3
    lda #1
    sta.b tcc__r5
    lda #40
    sta.b tcc__r4
    jsr native_bands_pool
    lda #:en_small
    sta.b tcc__r1h
    lda #en_small
    sta.b tcc__r1
    lda #16
    sta.b tcc__r3
    stz.b tcc__r5
    jsr native_bands_pool
    lda #:en_item
    sta.b tcc__r1h
    lda #en_item
    sta.b tcc__r1
    lda #8
    sta.b tcc__r3
    jsr native_bands_pool
    stz.b tcc__r0
    ldx #9
-   lda.l native_enemy_band,x
    and #255
    cmp #21
    bcs native_bands_over
    dex
    bpl -
    bra native_bands_done
native_bands_over:
    inc.b tcc__r0
native_bands_done:
    ply
    plx
    plp
    rtl
native_bands_pool:
    ldy #0
    lda [tcc__r1],y
    and #255
    bne +
    brl native_bands_next
+   lda.b tcc__r5
    cmp #2
    beq native_bands_live
    ldy #12
    lda [tcc__r1],y
    bne native_bands_live
    brl native_bands_next
native_bands_live:
    ldy #6
    lda [tcc__r1],y
    clc
    adc #32
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    tax
    stx.b tcc__r2
    lda.b tcc__r5
    beq native_bands_small
    cpx #9
    bcs native_bands_next
    sep #$20
    lda.l native_enemy_band,x
    clc
    adc #2
    sta.l native_enemy_band,x
    lda.l native_enemy_band+1,x
    clc
    adc #2
    sta.l native_enemy_band+1,x
    rep #$20
    bra native_bands_next
native_bands_small:
    cpx #10
    bcs +
    sep #$20
    lda.l native_enemy_band,x
    inc a
    sta.l native_enemy_band,x
    rep #$20
+   lda [tcc__r1],y
    clc
    adc #47
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    cmp.b tcc__r2
    beq native_bands_next
    cmp #10
    bcs native_bands_next
    tax
    sep #$20
    lda.l native_enemy_band,x
    inc a
    sta.l native_enemy_band,x
    rep #$20
native_bands_next:
    clc
    lda.b tcc__r1
    adc.b tcc__r4
    sta.b tcc__r1
    dec.b tcc__r3
    beq +
    brl native_bands_pool
+   rts
.ENDS

.BASE $C0
.SECTION "native_copy_fast" SUPERFREE
; Fast queue insertion for immutable, bank-contained ROM graphics. RAM,
; large chunks and bank crossings retain the C snapshot/splitting path.
native_copy:
    php
    phb
    phx
    phy
    rep #$30
    lda 16,s
    bne +
    brl native_copy_return
+
    cmp #2049
    bcc +
    brl native_copy_fallback
+
    lda 10,s
    clc
    adc 16,s
    bcc +
    brl native_copy_fallback
+
    lda.l queue_count
    tax
    cpx #512
    bcc +
    brl native_copy_overflow
+
    lda.l queue_total
    clc
    adc 16,s
    cmp #30001
    bcc +
    brl native_copy_overflow
+
    sta.l queue_total
    txa
    asl a
    tax
    lda 12,s
    and #255
    cmp #$c0
    bcs native_copy_rom
    lda.l queue_used
    clc
    adc #queue_data
    sta.b tcc__r2
    lda 16,s
    pha
    lda 14,s
    pha
    lda 14,s
    pha
    pea :queue_data
    pei (tcc__r2)
    jsl memcpy
    rep #$30
    tsc
    clc
    adc #10
    tcs
    lda.l queue_count
    asl a
    tax
    lda.l queue_used
    clc
    adc #queue_data
    sta.l queue_off,x
    lda #($8000 | :queue_data)
    sta.l queue_bank,x
    lda.l queue_used
    clc
    adc 16,s
    sta.l queue_used
    bra native_copy_descriptor
native_copy_rom:
    lda 10,s
    sta.l queue_off,x
    lda 12,s
    and #255
    ora #$8000
    sta.l queue_bank,x
native_copy_descriptor:
    lda 14,s
    sta.l queue_dest,x
    lda 16,s
    sta.l queue_size,x
    lda.l queue_count
    inc a
    sta.l queue_count
native_copy_return:
    ply
    plx
    plb
    plp
    rtl
native_copy_overflow:
    lda.l native_dma_overflow
    inc a
    sta.l native_dma_overflow
    bra native_copy_return
native_copy_fallback:
    ply
    plx
    plb
    plp
    jml native_copy_slow
.ENDS

.BASE $C0
.SECTION "native_collision" SUPERFREE
; Same odd/even cadence and arcade x/2 latch as enemies.c::collide.
native_collision_tick:
    php
    phb
    phx
    phy
    rep #$30
    lda.l frame
    and #1
    sta.b tcc__r0
    lda 14,s
    and #255
    cmp.b tcc__r0
    beq native_collision_due
    cmp #0
    beq native_collision_skip
    lda.l combined
    and #255
    beq native_collision_skip
native_collision_due:
    lda 10,s
    sta.b tcc__r1
    lda 12,s
    sta.b tcc__r1h
    ldy #4
    lda [tcc__r1],y
    clc
    adc #96
    lsr a
    ldy #29
    sep #$20
    sta [tcc__r1],y
    rep #$20
    lda #1
    bra native_collision_tick_done
native_collision_skip:
    lda #0
native_collision_tick_done:
    sta.b tcc__r0
    ply
    plx
    plb
    plp
    rtl

; Return the first eligible player's index, or $ffff. The snapshots match
; collect_shots; current player state and immunity can change during collisions.
native_enemy_contact:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r1
    lda 12,s
    sta.b tcc__r1h
    ldy #6
    lda [tcc__r1],y
    clc
    adc #16
    and #255
    sta.b tcc__r2
    ldy #29
    lda [tcc__r1],y
    and #255
    sta.b tcc__r3
    stz.b tcc__r0
native_contact_player:
    ldx.b tcc__r0
    lda.l pl_alive,x
    and #255
    bne +
    brl native_contact_next
+   lda.l pl_y,x
    and #255
    sta.b tcc__r4
    lda 14,s
    and #255
    bne +
    lda.b tcc__r4
    clc
    adc #8
    and #255
    sta.b tcc__r4
+   lda.b tcc__r4
    sec
    sbc.b tcc__r2
    bpl +
    eor #$ffff
    inc a
+   sta.b tcc__r4
    ldy #20
    lda [tcc__r1],y
    and #255
    sta.b tcc__r5
    lda.b tcc__r4
    cmp.b tcc__r5
    bcc +
    brl native_contact_next
+   lda.l pl_x2,x
    and #255
    sta.b tcc__r4
    lda 14,s
    and #255
    bne +
    lda.b tcc__r4
    clc
    adc #4
    and #255
    sta.b tcc__r4
+   lda.b tcc__r4
    sec
    sbc.b tcc__r3
    bpl +
    eor #$ffff
    inc a
+   sta.b tcc__r4
    ldy #21
    lda [tcc__r1],y
    and #255
    sta.b tcc__r5
    lda.b tcc__r4
    cmp.b tcc__r5
    bcs native_contact_next
    ldx #0
    lda.b tcc__r0
    beq +
    lda.l native_player_layout
    tax
+   lda.l players,x
    cmp #1
    bne native_contact_next
    lda 14,s
    and #255
    bne native_contact_hostile
    ldy #17
    lda [tcc__r1],y
    and #255
    bne native_contact_done
native_contact_hostile:
    lda.l players+23,x
    and #255
    beq native_contact_done
native_contact_next:
    inc.b tcc__r0
    lda.b tcc__r0
    cmp #2
    beq +
    brl native_contact_player
+   lda #$ffff
    sta.b tcc__r0
native_contact_done:
    ply
    plx
    plb
    plp
    rtl
.ENDS

.BASE $00
.RAMSECTION "native_vblank_state" APPENDTO "port_bss"
native_last_vblank dsb 2
native_vblank_reused dsb 2
native_dma_budget dsb 2
.ENDS
.BASE $C0
.SECTION "native_wait_vblank" SUPERFREE
; Reuse the current VBlank only when it has not committed a logical frame.
; The per-line budget reserves OAM/palette and setup time; queue rollover
; always waits for a fresh VBlank and samples its remaining transfer budget.
native_wait_vblank:
    php
    phx
    rep #$30
    lda #3800
    sta.l native_dma_budget
    lda.l snes_vblank_count
    cmp.l native_last_vblank
    beq native_wait_next
    sep #$20
    lda.l $4212
    and #$80
    beq native_wait_next
    lda.l $213f
    lda.l $2137
    lda.l $213d
    cmp #225
    bcc native_wait_next
    cmp #252
    bcs native_wait_next
    rep #$20
    and #255
    sec
    sbc #225
    asl a
    tax
    lda.l native_vblank_budget,x
    sta.l native_dma_budget
    lda.l native_vblank_reused
    inc a
    sta.l native_vblank_reused
    plx
    plp
    rtl
native_wait_next:
    rep #$30
    jsl native_next_vblank
    plx
    plp
    rtl
native_next_vblank:
    php
    phx
    rep #$30
    jsl WaitForVBlank
    sep #$20
    lda.l $213f
    lda.l $2137
    lda.l $213d
    cmp #225
    bcc native_fresh_short
    cmp #252
    bcs native_fresh_short
    rep #$20
    and #255
    sec
    sbc #225
    asl a
    tax
    lda.l native_vblank_budget,x
    bra native_fresh_store
native_fresh_short:
    rep #$20
    lda #100
native_fresh_store:
    sta.l native_dma_budget
    plx
    plp
    rtl
native_vblank_budget:
    .dw 3800,3650,3500,3350,3200,3050,2900,2750,2600,2450,2300,2150,2000,1850,1700,1550,1400,1250,1100,950,800,650,500,350,200,100,100
.ENDS

.BASE $00
.RAMSECTION "native_glyph_cache" BANK $7f SLOT 3 KEEP
native_glyph_hint dsb 16384
.ENDS
.BASE $C0
.SECTION "native_sprite_fast" SUPERFREE
; spr_32(code:u16, colour:u8, x:s16, y:s16, flags:u8).
; Only verified cache hits take this path; misses retain the C loader.
spr_32:
    php
    phb
    phx
    phy
    rep #$30
    lda 13,s
    beq native_sprite_reject
    cmp #288
    bcs native_sprite_reject
    lda 15,s
    clc
    adc #31
    cmp #255
    bcc native_sprite_visible
native_sprite_reject:
    ply
    plx
    plb
    plp
    rtl
native_sprite_visible:
    lda.l native_spr_count
    cmp #128
    bcs native_sprite_fallback
    lda 12,s
    and #15
    xba
    asl a
    asl a
    asl a
    sta.b tcc__r0
    lda 10,s
    and #2047
    tax
    ora.b tcc__r0
    sta.b tcc__r0
    lda.l native_big_hint,x
    and #255
    beq native_sprite_fallback
    dec a
    asl a
    tax
    lda.l native_big_keys,x
    cmp.b tcc__r0
    bne native_sprite_fallback
    lda.l native_spr_stamp
    sta.l native_big_used,x
    lda.l native_big_attributes,x
    sta.b tcc__r3
    lda 17,s
    and #3
    asl a
    tax
    lda.l native_sprite_flips,x
    ora.b tcc__r3
    sta.b tcc__r3
    lda 13,s
    sec
    sbc #32
    sta.b tcc__r1
    lda 15,s
    sta.b tcc__r2
    lda.l native_spr_count
    asl a
    asl a
    sta.b tcc__r4
    lda.l native_spr_count
    inc a
    sta.l native_spr_count
    lda #2
    sta.b tcc__r5
    brl native_sprite_emit
native_sprite_return:
    ply
    plx
    plb
    plp
    rtl
native_sprite_fallback:
    ply
    plx
    plb
    plp
    jml spr_32_slow
native_sprite_emit:
    ldx.b tcc__r4
    lda.b tcc__r1
    sep #$20
    sta.l oamMemory,x
    lda.b tcc__r2
    sta.l oamMemory+1,x
    rep #$20
    lda.b tcc__r3
    sta.l oamMemory+2,x
    lda.b tcc__r4
    and #12
    clc
    adc.b tcc__r5
    tax
    lda.b tcc__r1
    and #$100
    beq +
    inx
+   lda.l native_obj_mask,x
    and #255
    sta.b tcc__r0
    lda.b tcc__r4
    lsr a
    lsr a
    lsr a
    lsr a
    tax
    sep #$20
    lda.b tcc__r0
    ora.l oamMemory+512,x
    sta.l oamMemory+512,x
    rep #$30
    brl native_sprite_return

spr_16:
    php
    phb
    phx
    phy
    rep #$30
    lda 13,s
    cmp #17
    bcc native_small_reject
    cmp #288
    bcs native_small_reject
    lda 15,s
    clc
    adc #15
    cmp #239
    bcc native_small_visible
native_small_reject:
    ply
    plx
    plb
    plp
    rtl
native_small_visible:
    lda.l native_spr_count
    cmp #128
    bcs native_small_fallback
    lda 12,s
    and #15
    xba
    asl a
    asl a
    asl a
    sta.b tcc__r0
    lda 10,s
    and #2047
    ora.b tcc__r0
    tax
    lda.l native_sprite_hint,x
    and #255
    beq native_small_fallback
    dec a
    asl a
    tax
    lda.l native_spr_stamp
    sta.l native_small_used,x
    lda.l native_small_attributes,x
    sta.b tcc__r3
    lda 17,s
    and #3
    asl a
    tax
    lda.l native_sprite_flips,x
    ora.b tcc__r3
    sta.b tcc__r3
    lda 13,s
    sec
    sbc #32
    sta.b tcc__r1
    lda 15,s
    sta.b tcc__r2
    lda.l native_spr_count
    asl a
    asl a
    sta.b tcc__r4
    lda.l native_spr_count
    inc a
    sta.l native_spr_count
    stz.b tcc__r5
    brl native_sprite_emit
native_small_return:
    ply
    plx
    plb
    plp
    rtl
native_small_fallback:
    ply
    plx
    plb
    plp
    jml spr_16_slow
native_sprite_flips:
    .dw 0,$4000,$8000,$c000
.ENDS

.BASE $C0
.SECTION "native_enemy_tick" SUPERFREE
; Visit slots in their original order, including newly spawned later slots.
; Keep the far bank and big flag on the stack across arbitrary AI callbacks.
native_enemy_pool:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    tax
    lda 14,s
    tay
    beq native_enemy_pool_empty
    sep #$20
    lda 12,s
    pha
    plb
    rep #$20
    lda 12,s
    pha
    lda 18,s
    and #255
    pha
native_enemy_pool_loop:
    lda.w 0,x
    and #255
    beq native_enemy_pool_next
    phx
    phy
    sep #$20
    lda 5,s
    pha
    rep #$20
    lda 8,s
    pha
    txa
    pha
    jsl native_enemy_update
    rep #$30
    tsc
    clc
    adc #5
    tcs
    ply
    plx
native_enemy_pool_next:
    txa
    clc
    adc #40
    tax
    dey
    bne native_enemy_pool_loop
    pla
    pla
native_enemy_pool_empty:
    ply
    plx
    plb
    plp
    rtl
; Common enemy tick. Script changes and blocked terrain retain the C path.
; r2/r3 preserve the original position; leaf movement/terrain preserve r2..r5.
native_enemy_update:
    php
    phb
    phx
    phy
    rep #$30
    pea 0
    lda 12,s
    sta.b tcc__r4
    lda 14,s
    sta.b tcc__r4h
    ldy #2
    lda [tcc__r4],y
    and #255
    sta.b tcc__r5
    and #$40
    bne native_update_fallback_early
    ldy #10
    lda [tcc__r4],y
    and #255
    cmp #1
    bne native_update_common
    lda.b tcc__r5
    and #4
    beq native_update_fallback_early
    ldy #14
    lda [tcc__r4],y
    pha
    pei (tcc__r4h)
    pei (tcc__r4)
    jsl native_enemy_show
    tsc
    clc
    adc #6
    tcs
    lda.b tcc__r0
    beq native_update_fallback_early
    lda #1
    sta 1,s
    lda 12,s
    sta.b tcc__r4
    lda 14,s
    sta.b tcc__r4h
    ldy #2
    lda [tcc__r4],y
    and #255
    sta.b tcc__r5
    bra native_update_common
native_update_fallback_early:
    pla
    ply
    plx
    plb
    plp
    jml native_enemy_update_slow
native_update_common:
    ldy #4
    lda [tcc__r4],y
    sta.b tcc__r2
    ldy #6
    lda [tcc__r4],y
    sta.b tcc__r3
    lda.b tcc__r5
    and #$20
    beq native_update_timer
    lda.l en_scroll_dx
    and #255
    cmp #128
    bcc +
    ora #$ff00
+   sta.b tcc__r0
    lda.b tcc__r2
    sec
    sbc.b tcc__r0
    ldy #4
    sta [tcc__r4],y
    lda.l en_scroll_dy
    and #255
    cmp #128
    bcc +
    ora #$ff00
+   sta.b tcc__r0
    lda.b tcc__r3
    sec
    sbc.b tcc__r0
    ldy #6
    sta [tcc__r4],y
native_update_timer:
    lda 1,s
    bne native_update_move_loaded
    ldy #10
    sep #$20
    lda [tcc__r4],y
    dec a
    sta [tcc__r4],y
    rep #$20
native_update_move_loaded:
    lda 16,s
    and #255
    jsl native_enemy_move_fast
    lda.b tcc__r0
    bne +
    brl native_update_return
+   lda 16,s
    and #255
    beq native_update_terrain
    ldy #4
    lda [tcc__r4],y
    clc
    adc #112
    ldy #36
    sta [tcc__r4],y
    ldy #6
    lda [tcc__r4],y
    clc
    adc #16
    ldy #33
    sep #$20
    sta [tcc__r4],y
    rep #$20
native_update_terrain:
    lda.b tcc__r5
    and #4
    bne native_update_collide
    lda 16,s
    and #255
    jsl native_enemy_terrain_fast
    lda.b tcc__r0
    beq native_update_collide
    ldy #4
    lda.b tcc__r2
    sta [tcc__r4],y
    ldy #6
    lda.b tcc__r3
    sta [tcc__r4],y
    ldy #10
    sep #$20
    lda [tcc__r4],y
    inc a
    sta [tcc__r4],y
    rep #$20
    pla
    ply
    plx
    plb
    plp
    jml native_enemy_update_slow
native_update_collide:
    pla
    ply
    plx
    plb
    plp
    jml native_enemy_collide
native_update_return:
    pla
    ply
    plx
    plb
    plp
    rtl

native_enemy_terrain:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r1
    lda 12,s
    sta.b tcc__r1h
    lda 14,s
    and #255
    xba
    ora.b tcc__r1h
    sta.b tcc__r1h
    jsr native_enemy_terrain_body
    ply
    plx
    plb
    plp
    rtl
native_enemy_terrain_fast:
    and #255
    xba
    ora.b tcc__r4h
    sta.b tcc__r1h
    lda.b tcc__r4
    sta.b tcc__r1
    jsr native_enemy_terrain_body
    rtl
native_enemy_terrain_body:
    lda.b tcc__r1h
    and #$ff00
    beq native_terrain_small
    lda #112
    bra native_terrain_x
native_terrain_small:
    lda #120
native_terrain_x:
    ldy #4
    clc
    adc [tcc__r1],y
    clc
    adc.l level+4
    and #$fff
    sta.b tcc__r0
    lda.b tcc__r1h
    and #$ff00
    beq +
    lda #32
    bra ++
+   lda #24
++  ldy #6
    clc
    adc [tcc__r1],y
    and #255
    clc
    adc.l level+6
    and #$ff0
    asl a
    sta.b tcc__r0h
    lda.b tcc__r0
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc.b tcc__r0h
    tax
    lda.l terrain,x
    and #255
    sta.b tcc__r0h
    lda.b tcc__r0
    lsr a
    lsr a
    lsr a
    lsr a
    and #7
    tax
    lda.l native_terrain_bits,x
    and #255
    and.b tcc__r0h
    beq +
    lda #1
+   sta.b tcc__r0
    rts
native_terrain_bits:
    .db $80,$40,$20,$10,8,4,2,1
.ENDS

.BASE $C0
.SECTION "native_collide_fast" SUPERFREE
; Skip the general projectile-collision frame when there are no flying
; player shots (or the object is shotproof). Contact actions remain shared C.
native_enemy_collide:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r1
    lda 12,s
    sta.b tcc__r1h
    lda.l native_live_shots
    beq native_collide_common
    ldy #2
    lda [tcc__r1],y
    and #1
    bne native_collide_common
    ply
    plx
    plb
    plp
    jml native_enemy_collide_slow
native_collide_common:
    lda.l frame
    and #1
    sta.b tcc__r0
    lda 14,s
    and #255
    cmp.b tcc__r0
    beq native_collide_due
    cmp #0
    bne +
    brl native_collide_return
+   lda.l combined
    and #255
    bne native_collide_due
    brl native_collide_return
native_collide_due:
    ldy #4
    lda [tcc__r1],y
    clc
    adc #96
    lsr a
    ldy #29
    sep #$20
    sta [tcc__r1],y
    rep #$20
    ldy #2
    lda [tcc__r1],y
    and #2
    beq +
    brl native_collide_return
+   sep #$20
    lda 14,s
    pha
    rep #$20
    lda 13,s
    pha
    lda 13,s
    pha
    jsl native_enemy_contact
    tsc
    clc
    adc #5
    tcs
    lda.b tcc__r0
    cmp #2
    bcc +
    brl native_collide_return
+   lda 14,s
    and #255
    bne native_collide_hostile
    ldy #17
    lda [tcc__r1],y
    and #255
    beq native_collide_hostile
    jsr native_collide_push_player
    lda 16,s
    pha
    lda 16,s
    pha
    jsl en_pickup
    bra native_collide_clean
native_collide_hostile:
    jsr native_collide_push_player
    jsl player_kill
    lda 16,s
    pha
    lda 16,s
    pha
    jsl en_kill_by
native_collide_clean:
    pla
    pla
    pla
    pla
native_collide_return:
    ply
    plx
    plb
    plp
    rtl
; Push a Player far pointer below this JSR's return address, then return
; with that pointer as the next C call's argument block.
native_collide_push_player:
    pla
    sta.b tcc__r5
    lda.b tcc__r0
    beq +
    lda.l native_player_layout
+   clc
    adc #players
    sta.b tcc__r4
    pea :players
    pei (tcc__r4)
    pei (tcc__r5)
    rts
.ENDS

.BASE $C0
.SECTION "native_collect_contacts" SUPERFREE
; Snapshot both players, including an absent partner whose ring may still
; own live shots. Return whether the detailed C projectile list is needed.
native_collect_contacts:
    php
    phx
    phy
    rep #$30
    lda.l players
    cmp #1
    beq +
    lda #0
    bra ++
+   lda #1
++  sep #$20
    sta.l pl_alive
    rep #$20
    lda.l players+6
    clc
    adc #16
    sep #$20
    sta.l pl_y
    rep #$20
    lda.l players+4
    clc
    adc #96
    lsr a
    sep #$20
    sta.l pl_x2
    rep #$20
    lda.l players+284
    cmp #1
    beq +
    lda #0
    bra ++
+   lda #1
++  sep #$20
    sta.l pl_alive+1
    rep #$20
    lda.l players+290
    clc
    adc #16
    sep #$20
    sta.l pl_y+1
    rep #$20
    lda.l players+288
    clc
    adc #96
    lsr a
    sep #$20
    sta.l pl_x2+1
    rep #$20
    ldx #44
    ldy #18
native_collect_scan:
    lda.l players,x
    and #255
    cmp #1
    beq native_collect_present
    txa
    clc
    adc #22
    tax
    dey
    beq native_collect_empty
    cpy #9
    bne native_collect_scan
    txa
    clc
    adc #86
    tax
    bra native_collect_scan
native_collect_present:
    lda #1
    bra native_collect_done
native_collect_empty:
    lda #0
native_collect_done:
    sta.b tcc__r0
    ply
    plx
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_big_lookup" SUPERFREE
native_big_find:
    php
    phx
    rep #$30
    ldx #0
-   lda.l native_big_keys,x
    cmp 7,s
    beq native_big_found
    inx
    inx
    cpx #24
    bcc -
    lda #$ffff
    bra native_big_find_done
native_big_found:
    txa
    lsr a
native_big_find_done:
    sta.b tcc__r0
    plx
    plp
    rtl
native_big_victim:
    php
    phx
    rep #$30
    lda #$ffff
    sta.b tcc__r0
    stz.b tcc__r2
    ldx #0
native_big_lru:
    lda.l native_big_keys,x
    cmp #$ffff
    beq native_big_empty
    lda.l native_spr_stamp
    sec
    sbc.l native_big_used,x
    cmp.b tcc__r2
    bcc native_big_lru_next
    beq native_big_lru_next
    sta.b tcc__r2
    txa
    lsr a
    sta.b tcc__r0
native_big_lru_next:
    inx
    inx
    cpx #24
    bcc native_big_lru
    bra native_big_lru_done
native_big_empty:
    lda.b tcc__r2
    cmp #$ffff
    beq native_big_lru_done
    txa
    lsr a
    sta.b tcc__r0
native_big_lru_done:
    plx
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_hud_fast" SUPERFREE
native_hud_put:
    php
    phx
    rep #$30
    lda 7,s
    sec
    sbc #4
    cmp #32
    bcs native_hud_return
    asl a
    sta.b tcc__r0
    lda 9,s
    cmp #28
    bcs native_hud_return
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.b tcc__r0
    tax
    bra native_hud_store
native_panel_put:
    php
    phx
    rep #$30
    lda 7,s
    cmp #40
    bcs native_hud_return
    lda 9,s
    cmp #28
    bcs native_hud_return
    asl a
    asl a
    asl a
    sta.b tcc__r0
    asl a
    asl a
    clc
    adc.b tcc__r0
    clc
    adc 7,s
    asl a
    tax
    lda.l native_panel_cells,x
    cmp #$ffff
    beq native_hud_return
    tax
native_hud_store:
    lda 11,s
    cmp.l hud_map,x
    beq native_hud_return
    sta.l hud_map,x
    txa
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    asl a
    asl a
    tax
    lda.l native_hud_rows,x
    ora.l hud_dirty
    sta.l hud_dirty
    lda.l native_hud_rows+2,x
    ora.l hud_dirty+2
    sta.l hud_dirty+2
native_hud_return:
    plx
    plp
    rtl
native_hud_rows:
    .dw 1,0
    .dw 2,0
    .dw 4,0
    .dw 8,0
    .dw 16,0
    .dw 32,0
    .dw 64,0
    .dw 128,0
    .dw 256,0
    .dw 512,0
    .dw 1024,0
    .dw 2048,0
    .dw 4096,0
    .dw 8192,0
    .dw 16384,0
    .dw 32768,0
    .dw 0,1
    .dw 0,2
    .dw 0,4
    .dw 0,8
    .dw 0,16
    .dw 0,32
    .dw 0,64
    .dw 0,128
    .dw 0,256
    .dw 0,512
    .dw 0,1024
    .dw 0,2048
    .dw 0,4096
    .dw 0,8192
    .dw 0,16384
    .dw 0,32768
.ENDS

.BASE $00
.RAMSECTION "boss_contact_masks" BANK $7f SLOT 3 KEEP
native_boss_masks dsb 4
native_boss_shot_list dsb 72
native_boss_shot_list_bytes dsb 2
native_boss_snapshot_frame dsb 4
native_boss_snapshot_valid dsb 2
native_boss_contact_possible dsb 2
.ENDS
.BASE $C0
.SECTION "native_boss_hitmask" SUPERFREE
; Exact boss_shots geometry. Player/shot fields are asserted by the QA
; layout checks; emit a nine-bit mask per player, preserving P1/P2 order.
; PHP/PHX/PHY add five bytes: py +9, px +11, c +13, d2 +14.
native_boss_hitmask:
    php
    phx
    phy
    rep #$30
    lda #0
    sta.l native_boss_masks
    sta.l native_boss_masks+2
    lda.l native_boss_snapshot_valid
    beq native_boss_snapshot_build
    lda.l frame_counter
    cmp.l native_boss_snapshot_frame
    bne native_boss_snapshot_build
    lda.l frame_counter+2
    cmp.l native_boss_snapshot_frame+2
    bne native_boss_snapshot_build
    brl native_boss_cached_geometry
native_boss_snapshot_build:
    lda #18
    sta.b tcc__r0
    lda #0
    sta.b tcc__r1
    ldx #36
    ldy #1
native_boss_snapshot_scan:
    lda.l players+8,x
    and #255
    cmp #1
    bne native_boss_snapshot_next
    txa
    sta.b tcc__r2
    ldx.b tcc__r1
    lda.b tcc__r2
    sta.l native_boss_shot_list,x
    tya
    sta.l native_boss_shot_list+2,x
    ldx.b tcc__r2
    lda.b tcc__r1
    clc
    adc #4
    sta.b tcc__r1
native_boss_snapshot_next:
    dec.b tcc__r0
    beq native_boss_snapshot_done
    lda.b tcc__r0
    cmp #9
    beq native_boss_snapshot_p2
    txa
    clc
    adc #22
    tax
    tya
    asl a
    tay
    bra native_boss_snapshot_scan
native_boss_snapshot_p2:
    ldx #320
    ldy #1
    bra native_boss_snapshot_scan
native_boss_snapshot_done:
    lda.b tcc__r1
    sta.l native_boss_shot_list_bytes
    lda.l frame_counter
    sta.l native_boss_snapshot_frame
    lda.l frame_counter+2
    sta.l native_boss_snapshot_frame+2
    lda #1
    sta.l native_boss_snapshot_valid
native_boss_cached_geometry:
    lda.l native_boss_shot_list_bytes
    sta.b tcc__r4h
    bne +
    brl native_boss_cached_return
+   lda 9,s
    sec
    sbc #16
    sta.b tcc__r1
    lda 11,s
    sec
    sbc #96
    sec
    sbc.l boss_shift
    sta.b tcc__r2
    lda 13,s
    and #255
    sta.b tcc__r3
    lda 14,s
    and #255
    sta.b tcc__r3h
    lda #0
    sta.b tcc__r5
native_boss_cached_loop:
    ldx.b tcc__r5
    lda.l native_boss_shot_list+2,x
    sta.b tcc__r4
    lda.l native_boss_shot_list,x
    tax
    lda.l players+8,x
    and #255
    cmp #1
    bne native_boss_cached_next
    lda.l players+13,x
    and #255
    clc
    adc.b tcc__r3
    sta.b tcc__r0
    lda.b tcc__r1
    sec
    sbc.l players+2,x
    bpl +
    eor #$ffff
    inc a
+   cmp.b tcc__r0
    bcs native_boss_cached_next
    lda.l players+12,x
    and #255
    clc
    adc.b tcc__r3h
    sta.b tcc__r0
    lda.b tcc__r2
    sec
    sbc.l players,x
    bpl +
    eor #$ffff
    inc a
+   cmp.b tcc__r0
    bcs native_boss_cached_next
    cpx #320
    bcs native_boss_cached_p2
    lda.l native_boss_masks
    ora.b tcc__r4
    sta.l native_boss_masks
    bra native_boss_cached_next
native_boss_cached_p2:
    lda.l native_boss_masks+2
    ora.b tcc__r4
    sta.l native_boss_masks+2
native_boss_cached_next:
    lda.b tcc__r5
    clc
    adc #4
    sta.b tcc__r5
    cmp.b tcc__r4h
    bcs native_boss_cached_return
    brl native_boss_cached_loop
native_boss_cached_return:
    ply
    plx
    plp
    rtl

.ENDS

.BASE $C0
.SECTION "native_pj_draw" SUPERFREE
weapon_select:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    ldy #15
    lda [tcc__r1],y
    and #255
    bne native_select_owned
    ldy #17
native_select_scan:
    lda [tcc__r1],y
    and #255
    bne native_select_first
    iny
    cpy #22
    bne native_select_scan
    bra native_select_clear
native_select_first:
    tya
    sec
    sbc #16
    ldy #15
    sep #$20
    sta [tcc__r1],y
    rep #$20
native_select_clear:
    ldy #2
    lda [tcc__r1],y
    and #255
    tax
    sep #$20
    lda #0
    sta.l pad_weapon_req,x
    rep #$30
    ply
    plx
    plp
    rtl
native_select_owned:
    ply
    plx
    plp
    jml native_weapon_select_slow
native_weapon_linear:
    php
    phb
    phx
    phy
    rep #$30
    lda 14,s
    and #255
    tay
    beq native_linear_return
    lda 10,s
    clc
    adc #36
    tax
    sep #$20
    lda 12,s
    pha
    plb
    rep #$20
    lda 12,s
    pha
native_linear_loop:
    lda.w 8,x
    and #255
    beq native_linear_next
    phx
    phy
    lda 5,s
    pha
    txa
    pha
    jsl native_linear_slot
    rep #$30
    tsc
    clc
    adc #4
    tcs
    ply
    plx
native_linear_next:
    txa
    clc
    adc #22
    tax
    dey
    bne native_linear_loop
    pla
native_linear_return:
    ply
    plx
    plb
    plp
    rtl
    .dl native_linear_slow
native_final_draw:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    tax
    sep #$20
    lda 12,s
    pha
    plb
    rep #$20
    ldy #8
native_final_draw_loop:
    lda.w 0,x
    and #255
    beq native_final_draw_next
    lda.w 16,x
    beq native_final_draw_next
    phx
    phy
    sep #$20
    lda #0
    pha
    rep #$20
    lda.w 2,x
    sec
    sbc #16
    pha
    lda.w 4,x
    sec
    sbc #96
    sec
    sbc.l boss_shift
    pha
    sep #$20
    lda.w 18,x
    pha
    rep #$20
    lda.w 16,x
    pha
    jsl spr_32
    rep #$30
    tsc
    clc
    adc #8
    tcs
    ply
    plx
native_final_draw_next:
    txa
    clc
    adc #28
    tax
    dey
    bne native_final_draw_loop
    ply
    plx
    plb
    plp
    rtl
    .dl native_final_draw_slow
pj_draw:
    php
    phx
    phy
    rep #$30
    lda.l native_pj_live
    beq native_pj_draw_end
    ldx #0
    ldy #40
native_pj_draw_loop:
    lda.l native_pj,x
    and #255
    beq native_pj_draw_next
    lda.l native_pj+20,x
    beq native_pj_draw_next
    phx
    phy
    sep #$20
    lda #0
    pha
    rep #$20
    lda.l native_pj+2,x
    sec
    sbc #16
    pha
    lda.l native_pj+4,x
    sec
    sbc #96
    sec
    sbc.l boss_shift
    pha
    sep #$20
    lda.l native_pj+22,x
    pha
    rep #$20
    lda.l native_pj+20,x
    pha
    lda.l native_pj,x
    and #255
    cmp #4
    beq native_pj_draw_big
    jsl spr_16
    bra native_pj_draw_clean
native_pj_draw_big:
    jsl spr_32
native_pj_draw_clean:
    rep #$30
    tsc
    clc
    adc #8
    tcs
    ply
    plx
native_pj_draw_next:
    txa
    clc
    adc #32
    tax
    dey
    bne native_pj_draw_loop
native_pj_draw_end:
    ply
    plx
    plp
    rtl
; Retained as a differential oracle for the native paths.
    .dl native_pj_draw_slow,native_boss_shots_slow
.ENDS

.BASE $C0
.SECTION "native_boss_touch" SUPERFREE
boss_touch:
    php
    phb
    phx
    phy
    rep #$30
    ldx #0
    ldy #0
native_touch_loop:
    jsr native_touch_test
    beq native_touch_next
    phx
    phy
    pea :players
    txa
    clc
    adc #players
    pha
    jsl player_kill
    rep #$30
    tsc
    clc
    adc #4
    tcs
    ply
    plx
    ldy #1
native_touch_next:
    txa
    clc
    adc #284
    tax
    cpx #568
    bcc native_touch_loop
    sty.b tcc__r0
    ply
    plx
    plb
    plp
    rtl
native_touch_test:
    lda.l players,x
    cmp #1
    bne native_touch_miss
    lda.l players+23,x
    and #255
    bne native_touch_miss
    lda 18,s
    and #255
    cmp #128
    bcc +
    ora #$ff00
+   clc
    adc.l players+6,x
    clc
    adc #16
    sec
    sbc 12,s
    bpl +
    eor #$ffff
    inc a
+   sta.b tcc__r0
    lda 16,s
    and #255
    cmp.b tcc__r0
    bcc native_touch_miss
    beq native_touch_miss
    lda 19,s
    and #255
    cmp #128
    bcc +
    ora #$ff00
+   clc
    adc.l players+4,x
    clc
    adc #96
    clc
    adc.l boss_shift
    sec
    sbc 14,s
    bpl +
    eor #$ffff
    inc a
+   sta.b tcc__r0
    lda 17,s
    and #255
    cmp.b tcc__r0
    bcc native_touch_miss
    beq native_touch_miss
    lda #1
    rts
native_touch_miss:
    lda #0
    rts
    .dl native_boss_touch_slow
.ENDS

.BASE $C0
.SECTION "native_bg_cell" SUPERFREE
; Expand one 32x32 metatile into the 64x32 ring, preserving empty tiles,
; palette and both flips. Only sixteen source words are read.
native_bg_cell:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    lda 13,s
    asl a
    asl a
    asl a
    asl a
    clc
    adc #$3010
    sta.b tcc__r2
    lda 15,s
    and #$c000
    ora.b tcc__r2
    sta.b tcc__r2
    lda #0
    sta.b tcc__r3
    lda 15,s
    bit #$4000
    beq +
    lda #3
    sta.b tcc__r3
+   lda 15,s
    bit #$8000
    beq +
    lda.b tcc__r3
    ora #12
    sta.b tcc__r3
+   lda 17,s
    asl a
    tax
    lda #0
    sta.b tcc__r4
native_bg_cell_loop:
    lda.b tcc__r1h
    and #255
    beq native_bg_cell_blank
    lda.b tcc__r4
    eor.b tcc__r3
    sta.b tcc__r5
    asl a
    tay
    lda [tcc__r1],y
    beq native_bg_cell_blank
    and #$2000
    lsr a
    lsr a
    lsr a
    ora.b tcc__r2
    clc
    adc.b tcc__r5
    bra native_bg_cell_store
native_bg_cell_blank:
    lda #0
native_bg_cell_store:
    sta.l native_bg_map,x
    inx
    inx
    inc.b tcc__r4
    lda.b tcc__r4
    cmp #16
    beq native_bg_cell_end
    and #3
    bne native_bg_cell_loop
    txa
    clc
    adc #56
    tax
    bra native_bg_cell_loop
native_bg_cell_end:
    ply
    plx
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_final_motion" SUPERFREE
native_final_load:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    ldy #9
    lda [tcc__r1],y
    and #255
    asl a
    sta.b tcc__r0
    asl a
    clc
    adc.b tcc__r0
    sta.b tcc__r0
    ldy #12
    lda [tcc__r1],y
    clc
    adc.b tcc__r0
    sta.b tcc__r2
    ldy #14
    lda [tcc__r1],y
    sta.b tcc__r2h
    ldy #0
    lda [tcc__r2],y
    sta.b tcc__r3
    ldy #4
    lda [tcc__r2],y
    ldy #6
    sta [tcc__r1],y
    ldy #2
    lda [tcc__r2],y
    ldy #16
    sta [tcc__r1],y
    lda.b tcc__r3
    sep #$20
    ldy #8
    sta [tcc__r1],y
    rep #$20
    lda.b tcc__r3
    xba
    sep #$20
    ldy #18
    sta [tcc__r1],y
    rep #$30
    ply
    plx
    plp
    rtl
native_final_move:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    ldy #6
    lda [tcc__r1],y
    and #255
    cmp #128
    bcc +
    ora #$ff00
+   ldy #2
    clc
    adc [tcc__r1],y
    sta [tcc__r1],y
    ldy #7
    lda [tcc__r1],y
    and #255
    cmp #128
    bcc +
    ora #$ff00
+   ldy #4
    clc
    adc [tcc__r1],y
    sta [tcc__r1],y
    ply
    plx
    plp
    rtl
    .dl native_final_load_slow,native_final_move_slow
.ENDS

.BASE $C0
.SECTION "native_weapon_shots" SUPERFREE
native_weapon_shots:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sec
    sbc #players
    clc
    adc #36
    tax
    ldy #9
native_weapon_draw_loop:
    lda.l players+8,x
    and #255
    beq native_weapon_draw_next
    phx
    phy
    sep #$20
    lda #0
    pha
    rep #$20
    lda.l players+2,x
    pha
    lda.l players,x
    pha
    sep #$20
    lda.l players+18,x
    pha
    rep #$20
    lda.l players+16,x
    pha
    jsl spr_16
    rep #$30
    tsc
    clc
    adc #8
    tcs
    ply
    plx
native_weapon_draw_next:
    txa
    clc
    adc #22
    tax
    dey
    bne native_weapon_draw_loop
    ply
    plx
    plp
    rtl
    .dl native_weapons_draw_slow
.ENDS

.BASE $C0
.SECTION "native_pj_bullet" SUPERFREE
native_pj_bullet_step:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    lda 13,s
    xba
    and #$0300
    sta.b tcc__r2
    ldy #24
    lda [tcc__r1],y
    and #255
    asl a
    asl a
    asl a
    clc
    adc.b tcc__r2
    sta.b tcc__r2
    ldy #25
    lda [tcc__r1],y
    and #255
    asl a
    clc
    adc.b tcc__r2
    tax
    lda.l bullet_cycle,x
    ldy #6
    sta [tcc__r1],y
    ldy #25
    lda [tcc__r1],y
    inc a
    and #3
    sep #$20
    sta [tcc__r1],y
    rep #$20
    and #1
    beq native_pj_even_phase
    lda #$126
    ldy #20
    sta [tcc__r1],y
    lda #8
    bra native_pj_colour
native_pj_even_phase:
    lda #$127
    ldy #20
    sta [tcc__r1],y
    lda #7
native_pj_colour:
    sep #$20
    ldy #22
    sta [tcc__r1],y
    rep #$30
    ply
    plx
    plp
    rtl
pj_bank_live:
    php
    phx
    phy
    rep #$30
    lda #0
    sta.b tcc__r0
    ldx #0
    ldy #40
native_pj_bank_loop:
    lda.l native_pj,x
    and #255
    cmp #3
    bne native_pj_bank_next
    lda.l native_pj+1,x
    and #255
    cmp 9,s
    ; Parameter is a byte: compare its low byte only.
    sep #$20
    cmp 9,s
    rep #$20
    bne native_pj_bank_next
    inc.b tcc__r0
native_pj_bank_next:
    txa
    clc
    adc #32
    tax
    dey
    bne native_pj_bank_loop
    ply
    plx
    plp
    rtl
pj_capped_live:
    php
    phx
    phy
    rep #$30
    lda #0
    sta.b tcc__r0
    ldx #0
    ldy #40
native_pj_cap_loop:
    lda.l native_pj,x
    and #255
    cmp #2
    beq native_pj_cap_count
    cmp #3
    bne native_pj_cap_next
    lda.l native_pj+1,x
    and #255
    cmp #255
    bne native_pj_cap_next
native_pj_cap_count:
    inc.b tcc__r0
native_pj_cap_next:
    txa
    clc
    adc #32
    tax
    dey
    bne native_pj_cap_loop
    ply
    plx
    plp
    rtl
    .dl native_pj_bank_slow,native_pj_capped_slow,native_pj_bullet_step_slow
.ENDS

.BASE $00
.RAMSECTION "native_panel_snapshot" BANK $7f SLOT 3 KEEP
native_hud_snapshot dsb 56
.ENDS
.BASE $C0
.SECTION "native_panel_probe" SUPERFREE
native_panel_probe:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    lda 13,s
    and #255
    bne +
    brl native_panel_dirty
+
    lda.l frame
    and #12
    sta.b tcc__r2
    lda.l native_hud_snapshot+54
    and #255
    cmp.b tcc__r2
    beq +
    brl native_panel_dirty
+
    ldy #0
    ldx #0
native_panel_cmp:
    lda [tcc__r1],y
    cmp.l native_hud_snapshot,x
    beq +
    brl native_panel_dirty
+
    iny
    iny
    inx
    inx
    cpx #28
    bcc native_panel_cmp
    ldx #0
native_panel_scores:
    lda.l players+32,x
    cmp.l native_hud_snapshot+28,x
    beq +
    brl native_panel_dirty
+
    lda.l players+316,x
    cmp.l native_hud_snapshot+32,x
    beq +
    brl native_panel_dirty
+
    inx
    inx
    cpx #4
    bcc native_panel_scores
    ldx #0
native_panel_stats:
    lda.l players+14,x
    cmp.l native_hud_snapshot+36,x
    beq +
    brl native_panel_dirty
+
    lda.l players+298,x
    cmp.l native_hud_snapshot+45,x
    beq +
    brl native_panel_dirty
+
    inx
    inx
    cpx #8
    bcc native_panel_stats
    lda.l players+22
    and #255
    sta.b tcc__r0
    lda.l native_hud_snapshot+44
    and #255
    cmp.b tcc__r0
    beq +
    brl native_panel_dirty
+
    lda.l players+306
    and #255
    sta.b tcc__r0
    lda.l native_hud_snapshot+53
    and #255
    cmp.b tcc__r0
    beq +
    brl native_panel_dirty
+
    lda #0
    bra native_panel_return
native_panel_dirty:
    ldy #0
    ldx #0
native_panel_copy:
    lda [tcc__r1],y
    sta.l native_hud_snapshot,x
    iny
    iny
    inx
    inx
    cpx #28
    bcc native_panel_copy
    ldx #0
native_panel_copy_scores:
    lda.l players+32,x
    sta.l native_hud_snapshot+28,x
    lda.l players+316,x
    sta.l native_hud_snapshot+32,x
    inx
    inx
    cpx #4
    bcc native_panel_copy_scores
    ldx #0
native_panel_copy_stats:
    lda.l players+14,x
    sta.l native_hud_snapshot+36,x
    lda.l players+298,x
    sta.l native_hud_snapshot+45,x
    inx
    inx
    cpx #8
    bcc native_panel_copy_stats
    sep #$20
    lda.l players+22
    sta.l native_hud_snapshot+44
    lda.l players+306
    sta.l native_hud_snapshot+53
    lda.l frame
    and #12
    sta.l native_hud_snapshot+54
    rep #$20
    lda #1
native_panel_return:
    sta.b tcc__r0
    ply
    plx
    plp
    rtl
    .dl native_panel_changed_slow
.ENDS

.BASE $C0
.SECTION "native_par_columns_fast" SUPERFREE
; The ROM stores each visible column twice vertically. Fully unrolled
; copies avoid per-tile address arithmetic and source-wrap branches.
native_par_columns:
    php
    phb
    phx
    phy
    rep #$30
    lda 10,s
    sta.b tcc__r0
    lda #0
    sta.b tcc__r1
    sep #$20
    lda #:par_column_map
    pha
    plb
    rep #$20
native_par_fast_loop:
    lda.b tcc__r1
    clc
    adc #4
    lsr a
    tax
    lda.l par_star_col,x
    and #255
    asl a
    tax
    lda.l par_lx,x
    sta.b tcc__r2
    cmp.l par_last_columns,x
    bne native_par_fast_changed
    lda.b tcc__r0
    bne native_par_fast_changed
    brl native_par_fast_next
native_par_fast_changed:
    lda.b tcc__r2
    and #7
    xba
    asl a
    asl a
    asl a
    asl a
    sta.b tcc__r4
    lda.b tcc__r1
    xba
    lsr a
    clc
    adc.b tcc__r4
    sta.b tcc__r4
    lda.b tcc__r2
    lsr a
    lsr a
    and #62
    clc
    adc.b tcc__r4
    tax
    lda.b tcc__r1
    asl a
    tay
    lda.l native_star_phases+0,x
    sta.w par_column_map+0,y
    lda.l native_star_phases+2,x
    sta.w par_column_map+64,y
    lda.l native_star_phases+4,x
    sta.w par_column_map+128,y
    lda.l native_star_phases+6,x
    sta.w par_column_map+192,y
    lda.l native_star_phases+8,x
    sta.w par_column_map+256,y
    lda.l native_star_phases+10,x
    sta.w par_column_map+320,y
    lda.l native_star_phases+12,x
    sta.w par_column_map+384,y
    lda.l native_star_phases+14,x
    sta.w par_column_map+448,y
    lda.l native_star_phases+16,x
    sta.w par_column_map+512,y
    lda.l native_star_phases+18,x
    sta.w par_column_map+576,y
    lda.l native_star_phases+20,x
    sta.w par_column_map+640,y
    lda.l native_star_phases+22,x
    sta.w par_column_map+704,y
    lda.l native_star_phases+24,x
    sta.w par_column_map+768,y
    lda.l native_star_phases+26,x
    sta.w par_column_map+832,y
    lda.l native_star_phases+28,x
    sta.w par_column_map+896,y
    lda.l native_star_phases+30,x
    sta.w par_column_map+960,y
    lda.l native_star_phases+32,x
    sta.w par_column_map+1024,y
    lda.l native_star_phases+34,x
    sta.w par_column_map+1088,y
    lda.l native_star_phases+36,x
    sta.w par_column_map+1152,y
    lda.l native_star_phases+38,x
    sta.w par_column_map+1216,y
    lda.l native_star_phases+40,x
    sta.w par_column_map+1280,y
    lda.l native_star_phases+42,x
    sta.w par_column_map+1344,y
    lda.l native_star_phases+44,x
    sta.w par_column_map+1408,y
    lda.l native_star_phases+46,x
    sta.w par_column_map+1472,y
    lda.l native_star_phases+48,x
    sta.w par_column_map+1536,y
    lda.l native_star_phases+50,x
    sta.w par_column_map+1600,y
    lda.l native_star_phases+52,x
    sta.w par_column_map+1664,y
    lda.l native_star_phases+54,x
    sta.w par_column_map+1728,y
    lda.l native_star_phases+56,x
    sta.w par_column_map+1792,y
    lda.l native_star_phases+58,x
    sta.w par_column_map+1856,y
    lda.l native_star_phases+60,x
    sta.w par_column_map+1920,y
    lda.l native_star_phases+62,x
    sta.w par_column_map+1984,y
native_par_fast_next:
    inc.b tcc__r1
    lda.b tcc__r1
    cmp #32
    bcs +
    brl native_par_fast_loop
+   lda.l queue_count
    cmp #512
    bcs native_par_fast_overflow
    asl a
    tax
    lda #par_column_map
    sta.l queue_off,x
    lda #($8000 | :par_column_map)
    sta.l queue_bank,x
    lda #$7800
    sta.l queue_dest,x
    lda #2048
    sta.l queue_size,x
    clc
    adc.l queue_total
    cmp #30001
    bcs native_par_fast_overflow
    sta.l queue_total
    lda.l queue_count
    inc a
    sta.l queue_count
    bra native_par_fast_done
native_par_fast_overflow:
    lda.l native_dma_overflow
    inc a
    sta.l native_dma_overflow
native_par_fast_done:
    ply
    plx
    plb
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_enemy_draw" SUPERFREE
native_enemy_draw_small:
    php
    phb
    phx
    phy
    rep #$30
    lda 14,s
    beq native_enemy_small_return
    tay
    asl a
    asl a
    clc
    adc 14,s
    asl a
    asl a
    asl a
    clc
    adc 10,s
    pha
    lda 12,s
    pha
    lda 20,s
    asl a
    asl a
    clc
    adc 20,s
    asl a
    asl a
    asl a
    clc
    adc 14,s
    tax
native_enemy_small_loop:
    txa
    cmp 3,s
    bne +
    lda 1,s
    tax
+   lda.l $7e0000,x
    and #255
    beq native_enemy_small_next
    lda.l $7e000c,x
    beq native_enemy_small_next
    phx
    phy
    sep #$20
    lda #0
    pha
    rep #$20
    lda.l $7e0006,x
    pha
    lda.l $7e0004,x
    pha
    sep #$20
    lda.l $7e000b,x
    pha
    rep #$20
    lda.l $7e000c,x
    pha
    jsl spr_16
    rep #$30
    tsc
    clc
    adc #8
    tcs
    ply
    plx
native_enemy_small_next:
    txa
    clc
    adc #40
    tax
    dey
    bne native_enemy_small_loop
    pla
    pla
native_enemy_small_return:
    ply
    plx
    plb
    plp
    rtl
native_enemy_draw_big:
    php
    phx
    phy
    rep #$30
    lda 9,s
    asl a
    asl a
    clc
    adc 9,s
    asl a
    asl a
    asl a
    tax
    lda.l en_big,x
    and #255
    beq native_enemy_big_return
    lda.l en_big+12,x
    beq native_enemy_big_return
    sep #$20
    lda #0
    pha
    rep #$20
    lda.l en_big+6,x
    pha
    lda.l en_big+4,x
    pha
    sep #$20
    lda.l en_big+11,x
    pha
    rep #$20
    lda.l en_big+12,x
    pha
    jsl spr_32
    rep #$30
    tsc
    clc
    adc #8
    tcs
native_enemy_big_return:
    ply
    plx
    plp
    rtl
    .dl native_enemy_draw_small_slow,native_enemy_draw_big_slow
.ENDS

.BASE $C0
.SECTION "native_fill" SUPERFREE
; Bank-contained C buffers, arbitrary byte value/count, including odd sizes.
; Eight word stores replace the SDK's byte-at-a-time clearing loop.
native_memset:
    php
    phb
    phx
    phy
    rep #$30
    lda 14,s
    and #255
    sta.b tcc__r2
    xba
    ora.b tcc__r2
    sta.b tcc__r2
    lda 10,s
    tax
    lda 16,s
    tay
    sep #$20
    lda 12,s
    pha
    plb
    rep #$20
native_fill_blocks:
    cpy #16
    bcc native_fill_words
    lda.b tcc__r2
    sta.w 0,x
    sta.w 2,x
    sta.w 4,x
    sta.w 6,x
    sta.w 8,x
    sta.w 10,x
    sta.w 12,x
    sta.w 14,x
    txa
    clc
    adc #16
    tax
    tya
    sec
    sbc #16
    tay
    bra native_fill_blocks
native_fill_words:
    cpy #2
    bcc native_fill_odd
    lda.b tcc__r2
    sta.w 0,x
    inx
    inx
    dey
    dey
    bra native_fill_words
native_fill_odd:
    cpy #0
    beq native_fill_return
    lda.b tcc__r2
    sep #$20
    sta.w 0,x
    rep #$20
native_fill_return:
    lda 10,s
    sta.b tcc__r0
    lda 12,s
    sta.b tcc__r0h
    ply
    plx
    plb
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_bg_entry" SUPERFREE
native_bg_entry:
    php
    phx
    phy
    rep #$30
    lda.l native_bg_frame_fallback
    bne native_bg_entry_fallback
    lda 9,s
    and #127
    sec
    sbc.l native_zone_rect
    bcc native_bg_entry_outside
    cmp.l native_zone_rect+4
    bcs native_bg_entry_outside
    sta.b tcc__r0
    lda 11,s
    and #127
    sec
    sbc.l native_zone_rect+2
    bcc native_bg_entry_outside
    cmp.l native_zone_rect+6
    bcs native_bg_entry_outside
    sta.b tcc__r2
    lda.l native_zone_rect+4
    sep #$20
    sta.l $004202
    lda.b tcc__r2
    sta.l $004203
    rep #$20
    ; Far-pointer loads provide more than the multiplier's eight-cycle delay.
    lda.l native_zone_map
    sta.b tcc__r1
    lda.l native_zone_map+2
    sta.b tcc__r1h
    lda.l $004216
    clc
    adc.b tcc__r0
    asl a
    tay
    lda [tcc__r1],y
    bra native_bg_entry_return
native_bg_entry_outside:
    lda #$ffff
native_bg_entry_return:
    sta.b tcc__r0
    ply
    plx
    plp
    rtl
native_bg_entry_fallback:
    ply
    plx
    plp
    jml native_bg_entry_slow
    .dl native_bg_entry_slow
.ENDS

.BASE $C0
.SECTION "native_bg_slot" SUPERFREE
; Strict first-wins LRU, including stamp wrap and all-currently-pinned cases.
; Bit 15 tags a newly assigned slot; the C loader queues its ROM pattern.
native_bg_slot:
    php
    phx
    phy
    rep #$30
    lda 9,s
    cmp #1024
    bcc +
    brl native_bg_slot_none
+
    sta.b tcc__r0
    tax
    lda.l native_meta_slot,x
    and #255
    beq native_bg_slot_miss
    dec a
    asl a
    tax
    lda.l native_bg_stamp
    sta.l native_bg_used,x
    txa
    lsr a
    brl native_bg_slot_return
native_bg_slot_miss:
    lda.l native_bg_stamp
    sta.b tcc__r3
    lda #0
    sta.b tcc__r1
    sta.b tcc__r2
    ldx #0
native_bg_slot_scan:
    lda.l native_bg_keys,x
    cmp #$ffff
    beq native_bg_slot_empty
    lda.b tcc__r3
    sec
    sbc.l native_bg_used,x
    bra native_bg_slot_age
native_bg_slot_empty:
    lda #$ffff
native_bg_slot_age:
    cmp.b tcc__r1
    bcc native_bg_slot_next
    beq native_bg_slot_next
    sta.b tcc__r1
    stx.b tcc__r2
    cmp #$ffff
    beq native_bg_slot_selected
native_bg_slot_next:
    inx
    inx
    cpx #94
    bcc native_bg_slot_scan
native_bg_slot_selected:
    lda.b tcc__r1
    beq native_bg_slot_none
    ldx.b tcc__r2
    lda.l native_bg_keys,x
    cmp #$ffff
    beq native_bg_slot_assign
    tax
    sep #$20
    lda #0
    sta.l native_meta_slot,x
    rep #$20
native_bg_slot_assign:
    ldx.b tcc__r2
    lda.b tcc__r0
    sta.l native_bg_keys,x
    lda.b tcc__r3
    sta.l native_bg_used,x
    txa
    lsr a
    inc a
    ldx.b tcc__r0
    sep #$20
    sta.l native_meta_slot,x
    rep #$20
    lda.l native_bg_misses
    inc a
    sta.l native_bg_misses
    lda.b tcc__r2
    lsr a
    ora #$8000
    bra native_bg_slot_return
native_bg_slot_none:
    lda #$ffff
native_bg_slot_return:
    sta.b tcc__r0
    ply
    plx
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_enemy_show" SUPERFREE
; Resolve only display/GOTO steps. Native behaviours, kill and malformed
; control chains remain with the original dispatcher, without partial writes.
native_enemy_show:
    php
    phx
    phy
    rep #$30
    lda 9,s
    sta.b tcc__r1
    lda 11,s
    sta.b tcc__r1h
    lda 13,s
    sta.b tcc__r2
    lda #32
    sta.b tcc__r3
native_enemy_show_find:
    lda.b tcc__r2
    asl a
    sta.b tcc__r0
    asl a
    clc
    adc.b tcc__r0
    clc
    adc #en_mot
    sta.b tcc__r4
    lda #:en_mot
    sta.b tcc__r4h
    ldy #0
    lda [tcc__r4],y
    sta.b tcc__r5
    and #255
    bne native_enemy_show_load
    lda.b tcc__r5
    and #$ff00
    bne native_enemy_show_control
    ldy #4
    lda [tcc__r4],y
    sta.b tcc__r2
    dec.b tcc__r3
    bne native_enemy_show_find
native_enemy_show_control:
    lda #0
    bra native_enemy_show_return
native_enemy_show_load:
    ldy #4
    lda [tcc__r4],y
    ldy #12
    sta [tcc__r1],y
    ldy #2
    lda [tcc__r4],y
    ldy #8
    sta [tcc__r1],y
    lda.b tcc__r5
    ldy #10
    sta [tcc__r1],y
    lda.b tcc__r2
    inc a
    ldy #14
    sta [tcc__r1],y
    sep #$20
    lda #1
    sta.l native_enemy_cont
    rep #$20
    lda #1
native_enemy_show_return:
    sta.b tcc__r0
    ply
    plx
    plp
    rtl
.ENDS

.BASE $C0
.SECTION "native_world_collision" SUPERFREE
terrain_solid:
    php
    phx
    phy
    rep #$30
    lda 9,s
    cmp #4096
    bcs native_world_empty
    sta.b tcc__r1
    lda 11,s
    cmp #4096
    bcs native_world_empty
    and #$ff0
    asl a
    sta.b tcc__r0h
    lda.b tcc__r1
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc.b tcc__r0h
    tax
    lda.l terrain,x
    and #255
    sta.b tcc__r0h
    lda.b tcc__r1
    lsr a
    lsr a
    lsr a
    lsr a
    and #7
    tax
    lda.l native_terrain_bits,x
    and #255
    and.b tcc__r0h
    beq native_world_empty
    lda #1
    bra native_world_done
native_world_empty:
    lda #0
native_world_done:
    sta.b tcc__r0
    ply
    plx
    plp
    rtl
    .dl native_terrain_solid_slow
.ENDS

.BASE $C0
.SECTION "native_boss_contacts_state" SUPERFREE
; Called immediately before each boss/projectile update. These routines can
; remove vulnerability during their loop, but never grant it to an immune
; player; the actual contact helper still rechecks every player at the hit.
native_boss_contact_snapshot:
    php
    rep #$30
    lda.l players
    cmp #1
    bne native_boss_contacts_p2
    lda.l players+23
    and #255
    beq native_boss_contacts_yes
native_boss_contacts_p2:
    lda.l players+284
    cmp #1
    bne native_boss_contacts_no
    lda.l players+307
    and #255
    beq native_boss_contacts_yes
native_boss_contacts_no:
    lda #0
    bra native_boss_contacts_store
native_boss_contacts_yes:
    lda #1
native_boss_contacts_store:
    sta.l native_boss_contact_possible
    plp
    rtl
.ENDS
