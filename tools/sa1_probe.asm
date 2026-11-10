.MEMORYMAP
    SLOTSIZE $8000
    DEFAULTSLOT 0
    SLOT 0 $8000
.ENDME
.ROMBANKSIZE $8000
.ROMBANKS 32
.SNESHEADER
    ID "S1PR"
    NAME "SIDE ARMS SA1 PROBE "
    SLOWROM
    LOROM
    CARTRIDGETYPE $34
    ROMSIZE $0A
    SRAMSIZE $03
    COUNTRY $01
    LICENSEECODE $00
    VERSION $00
.ENDSNES
.SNESNATIVEVECTOR
    COP Idle
    BRK Idle
    ABORT Idle
    NMI ProbeNMI
    IRQ Idle
.ENDNATIVEVECTOR
.SNESEMUVECTOR
    COP Idle
    ABORT Idle
    NMI Idle
    RESET Main
    IRQBRK Idle
.ENDEMUVECTOR
.BANK 0 SLOT 0
.ORG 0
.SECTION "probe_code" FORCE
Main:
    sei
    clc
    xce
    rep #$30
    ldx #$1fff
    txs
    sep #$20
    lda #$80
    sta.l $002100
    lda #0
    sta.l $7e2000
    lda #$ff
    sta.l $002229
    stz $3000
    stz $3001
    rep #$20
    lda #0
    sta.l $7e2028
    sep #$20
    lda #$80
    sta.l $004200
    rep #$20
    jsr ReadCounter
    sta.l $7e2010
    lda.l $7e2028
    sta.l $7e2040
    sep #$20
    ldx #0
CopyInputs:
    lda.l Input,x
    sta.l $003010,x
    inx
    cpx #272
    bne CopyInputs
    rep #$20
    jsr ReadCounter
    sta.l $7e2012
    lda.l $7e2028
    sta.l $7e2042
    lda #$3000
    tcd
    lda #BATCH_COUNT
    sta $0e
CPURepeat:
    jsr CollideBatch
    dec $0e
    bne CPURepeat
    jsr ReadCounter
    sta.l $7e2014
    lda.l $7e2028
    sta.l $7e2044
    ldx #0
CopyCPUResults:
    lda.l $003120,x
    sta.l $7e2100,x
    lda #$ffff
    sta.l $003120,x
    inx
    inx
    cpx #576
    bne CopyCPUResults
    lda #SA1Entry
    sta.l $002203
    jsr ReadCounter
    sta.l $7e2016
    lda.l $7e2028
    sta.l $7e2046
    sep #$20
    lda #1
    sta $3001
    stz $2200
    ldx #$ffff
WaitResult:
    lda.l $003000
    cmp #$a5
    beq Received
    dex
    bne WaitResult
    lda #$ee
    sta.l $7e2000
    stz $2121
    lda #$1f
    sta $2122
    stz $2122
    lda #$0f
    sta $2100
    jmp Idle
Received:
    rep #$20
    jsr ReadCounter
    sta.l $7e2018
    lda.l $7e2028
    sta.l $7e2048
    ldx #0
CopySA1Results:
    lda.l $003120,x
    sta.l $7e2340,x
    inx
    inx
    cpx #576
    bne CopySA1Results
    jsr ReadCounter
    sta.l $7e201a
    lda.l $7e2028
    sta.l $7e204a
    sep #$20
    stz $3000
    rep #$20
    jsr ReadCounter
    sta.l $7e2060
    lda.l $7e2028
    sta.l $7e2070
    sep #$20
    ldx #0
CopySecondInputs:
    lda.l Input2,x
    sta.l $003010,x
    inx
    cpx #272
    bne CopySecondInputs
    rep #$20
    jsr ReadCounter
    sta.l $7e2062
    lda.l $7e2028
    sta.l $7e2072
    lda #BATCH_COUNT
    sta $0e
CPUSecondRepeat:
    jsr CollideBatch
    dec $0e
    bne CPUSecondRepeat
    jsr ReadCounter
    sta.l $7e2064
    lda.l $7e2028
    sta.l $7e2074
    ldx #0
CopySecondCPUResults:
    lda.l $003120,x
    sta.l $7e27c0,x
    lda #$ffff
    sta.l $003120,x
    inx
    inx
    cpx #576
    bne CopySecondCPUResults
    jsr ReadCounter
    sta.l $7e2066
    lda.l $7e2028
    sta.l $7e2076
    sep #$20
    lda #1
    sta $3001
    ldx #$ffff
WaitSecondResult:
    lda.l $003000
    cmp #$a5
    beq SecondReceived
    dex
    bne WaitSecondResult
    lda #$ee
    sta.l $7e2000
    jmp Idle
SecondReceived:
    rep #$20
    jsr ReadCounter
    sta.l $7e2068
    lda.l $7e2028
    sta.l $7e2078
    ldx #0
CopySecondSA1Results:
    lda.l $003120,x
    sta.l $7e2580,x
    inx
    inx
    cpx #576
    bne CopySecondSA1Results
    jsr ReadCounter
    sta.l $7e206a
    lda.l $7e2028
    sta.l $7e207a
    sep #$20
    lda #$a5
    sta.l $7e2000
    jsr ShowSuccess
Idle:
    bra Idle
ReadCounter:
    php
    sep #$20
    lda.l $002137
    lda.l $00213f
    lda.l $00213d
    sta.l $7e201e
    lda.l $00213d
    and #1
    sta.l $7e201f
    plp
    lda.l $7e201e
    rts
ProbeNMI:
    pha
    php
    rep #$20
    lda.l $7e2028
    inc a
    sta.l $7e2028
    plp
    pla
    rti
ShowSuccess:
    .ACCU 8
    stz $2105
    lda #$08
    sta $2107
    stz $210b
    lda #$01
    sta $212c
    lda #$80
    sta $2115
    rep #$20
    .ACCU 16
    stz $2116
    sep #$20
    .ACCU 8
    ldx #0
FontLoop:
    lda.l Font,x
    sta $2118
    inx
    lda.l Font,x
    sta $2119
    inx
    cpx #112
    bne FontLoop
    rep #$20
    .ACCU 16
    lda #$0800
    sta $2116
    sep #$20
    .ACCU 8
    ldx #1024
ClearMap:
    stz $2118
    stz $2119
    dex
    bne ClearMap
    rep #$20
    .ACCU 16
    lda #$098c
    sta $2116
    sep #$20
    .ACCU 8
    ldx #0
TitleLoop:
    lda.l Title,x
    sta $2118
    stz $2119
    inx
    cpx #7
    bne TitleLoop
    stz $2121
    stz $2122
    lda #$02
    sta $2122
    lda #$ff
    sta $2122
    lda #$7f
    sta $2122
    lda #$0f
    sta $2100
    rts
SA1Entry:
    sei
    clc
    xce
    rep #$30
    ldx #$07ff
    txs
    sep #$20
    lda #$ff
    sta.l $00222a
    stz $3001
    rep #$20
    lda #$3000
    tcd
    lda #BATCH_COUNT
    sta $0e
SA1Repeat:
    jsr CollideBatch
    dec $0e
    bne SA1Repeat
    sep #$20
    lda #$a5
    sta.l $003000
SA1Idle:
    lda.l $003000
    cmp #$a5
    beq SA1Idle
SA1Wait:
    lda.l $003001
    cmp #1
    bne SA1Wait
    stz $3001
    rep #$20
    lda #BATCH_COUNT
    sta $0e
SA1SecondRepeat:
    jsr CollideBatch
    dec $0e
    bne SA1SecondRepeat
    sep #$20
    lda #$a5
    sta.l $003000
SA1Done:
    bra SA1Done
CollideBatch:
    .ACCU 16
    lda #$3120
    sta $0c
    ldx #0
NextEnemy:
    ldy #0
NextShot:
    lda $30b4,y
    sec
    sbc $3030,x
    bpl PositiveY
    eor #$ffff
    inc a
PositiveY:
    sta $08
    lda $3070,x
    clc
    adc $30fc,y
    cmp $08
    bcc Miss
    beq Miss
    lda $3090,y
    sec
    sbc $3010,x
    bpl PositiveX
    eor #$ffff
    inc a
PositiveX:
    sta $08
    lda $3050,x
    clc
    adc $30d8,y
    cmp $08
    bcc Miss
    beq Miss
    lda #1
    bra StoreHit
Miss:
    lda #0
StoreHit:
    sta ($0c)
    inc $0c
    inc $0c
    iny
    iny
    cpy #36
    bne NextShot
    inx
    inx
    cpx #32
    bne NextEnemy
    rts
Title:
    .db 1,2,3,4,0,5,6
Input:
    .INCBIN "build/sa1_probe/collision_input.bin"
Input2:
    .INCBIN "build/sa1_probe/collision_input_2.bin"
Font:
    .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    .db $3c,0,$42,0,$40,0,$3c,0,$02,0,$42,0,$3c,0,0,0
    .db $18,0,$24,0,$42,0,$7e,0,$42,0,$42,0,$42,0,0,0
    .db 0,0,0,0,0,0,$7e,0,0,0,0,0,0,0,0,0
    .db $18,0,$38,0,$18,0,$18,0,$18,0,$18,0,$7e,0,0,0
    .db $3c,0,$42,0,$42,0,$42,0,$42,0,$42,0,$3c,0,0,0
    .db $42,0,$44,0,$48,0,$70,0,$48,0,$44,0,$42,0,0,0
.ENDS
