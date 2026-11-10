.DEFAULT_GOAL := all
.SECONDARY:
PVSNESLIB_HOME ?= $(abspath ../../pvsneslib-sdk-4.6)
export PVSNESLIB_HOME
export ROMNAME := sidearms_md_snes
export ROMTITLE := SIDE ARMS MD SNES
HIROM := 1
FASTROM := 1
ROMBANKS := 64
ROMSIZE := 0C
CARTRIDGETYPE := 02
SRAMSIZE := 03
SRC := src
CFLAGS += -Iinc
AUDIOFILES := ../build/music/sfx.it $(foreach c,21 22 23 24 25 26 27 28 29 2a 2c 2e 33 34 35 36 38,../build/music/cmd$(c).it) ../sidearms_snes/music/stage1.it ../sidearms_snes/music/alt.it res/capcom.it
export SOUNDBANK := res/soundbank
SMCONVFLAGS := -s -o $(SOUNDBANK) -i -b 56
include $(PVSNESLIB_HOME)/devkitsnes/snes_rules
OFILES := $(sort $(OFILES) src/capcom_assets.obj)
src/capcom_assets.asm: ../tools/build_capcom.py ../tools/capcom_splash.png
	python3 ../tools/build_capcom.py
res/capcom.it: ../tools/build_capcom_music.py ../tools/capcom_logo.wav
	python3 ../tools/build_capcom_music.py
$(CFILES:.c=.ps): $(wildcard inc/*.h inc/gen/*.h src/logic/*.h)
$(CFILES:.c=.asm): ../tools/fix_asm.py ../tools/rom_constants.py
$(filter ../build/music/%,$(AUDIOFILES)) ../build/music/manifest.json &: ../tools/prepare_music.py ../sidearms_snes/res/sfx.it $(wildcard ../sidearms_snes/music/cmd*.it)
	python3 ../tools/prepare_music.py
$(SOUNDBANK).asm: Makefile $(AUDIOFILES)
	$(SMCONV) $(SMCONVFLAGS) $(AUDIOFILES)
	python3 ../tools/fix_asm.py $@
%.asm: %.ps
	python3 ../tools/fix_asm.py $<
	python3 ../tools/rom_constants.py $<
	$(OPT) -i $< -o $@
	python3 ../tools/fix_asm.py $@
$(ROMNAME).sfc: $(OFILES)
	@echo '[objects]' > linkfile
	@for object in $(OFILES) $(wildcard $(LIBDIRSOBJSW)/*.obj); do echo "$$object" >> linkfile; done
	$(LD) -d -s -v -c -L $(LIBDIRSOBJS) linkfile $@
	@sed 's/://' $(ROMNAME).sym > $(ROMNAME).sym.tmp
	@mv $(ROMNAME).sym.tmp $(ROMNAME).sym
	@cp $(ROMNAME).sym $(ROMNAME).symfull
	@sed '/ SECTIONSTART_/d;/ SECTIONEND_/d;/ RAM_USAGE_SLOT_/d;' $(ROMNAME).symfull > $(ROMNAME).sym
.PHONY: all
all: $(ROMNAME).sfc
src/audio.obj: res/soundbank.h
src/audio.ps: res/sound_meta.h
res/soundbank.h: res/soundbank.obj
res/sound_meta.h: res/soundbank.asm ../tools/sound_meta.py
	python3 ../tools/sound_meta.py res/soundbank.bnk $@
