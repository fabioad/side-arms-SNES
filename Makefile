.DEFAULT_GOAL := all
PYTHON ?= python3
SIDEARMS_SOURCE ?= $(CURDIR)/rom
export SIDEARMS_SOURCE
SOURCE_FILES := $(wildcard src/*.[ch] inc/*.h tools/*.py tools/*.json)

.PHONY: all assets md-assets md-rom check-source check check-sections check-frontend check-campaign check-rush check-audio check-ending check-render check-options analyze run
all: build/native-assets.stamp
	mkdir -p build/tmp
	$(MAKE) -C snes

check-source:
	$(PYTHON) tools/arcade_source.py

build/md-assets.stamp: $(SOURCE_FILES) $(wildcard rom/*)
	$(MAKE) md-assets

build/native-assets.stamp: build/md-assets.stamp tools/prepare_snes.py tools/build_wheels.py tools/build_home_logo.py tools/c89_loops.py snes/src/hud_prefix.inc
	mkdir -p build snes/res
	$(PYTHON) tools/prepare_snes.py
	touch build/native-assets.stamp

md-assets: check-source
	mkdir -p build snes/res
	$(PYTHON) tools/extract_levels.py
	$(PYTHON) tools/extract_player.py
	$(PYTHON) tools/extract_spawns.py
	$(PYTHON) tools/extract_sound.py
	$(PYTHON) tools/build_assets.py
	touch build/md-assets.stamp

# Original Mega Drive build, kept alongside the SNES port.
md-rom:
	$(MAKE) -f Makefile.md all

assets: md-assets
	$(PYTHON) tools/prepare_snes.py
	touch build/native-assets.stamp

check: all
	$(PYTHON) tools/test_assets.py
	$(PYTHON) tools/test_music.py
	$(PYTHON) -u tools/test_snes.py

check-sections: all
	$(PYTHON) -u tools/qa_sections.py

check-frontend: all
	$(PYTHON) -u tools/qa_frontend.py

check-campaign: all
	$(PYTHON) -u tools/qa_campaign.py

check-rush: all
	$(PYTHON) -u tools/qa_campaign.py --rush

check-audio: all
	$(PYTHON) -u tools/qa_audio.py

check-ending: all
	$(PYTHON) -u tools/qa_ending.py

.PHONY: check-items
.PHONY: check-collision
check-collision: all
	$(PYTHON) -u tools/qa_collision_native.py

.PHONY: check-native check-ui
check-native: all
	$(PYTHON) -u tools/qa_collision_native.py
	$(PYTHON) -u tools/qa_enemy_native.py
	$(PYTHON) -u tools/qa_sprite_native.py
	$(PYTHON) -u tools/qa_sprite_cache.py
	$(PYTHON) -u tools/qa_memory_native.py
	$(PYTHON) -u tools/qa_dma_native.py
	$(PYTHON) -u tools/qa_bg_native.py
	$(PYTHON) -u tools/qa_cache_motion.py
	$(PYTHON) -u tools/qa_draw_groups.py
	$(PYTHON) -u tools/qa_panel_native.py
	$(PYTHON) -u tools/qa_enemy_pool.py
	$(PYTHON) -u tools/qa_boss_contacts.py
	$(PYTHON) -u tools/qa_boss_native.py
	$(PYTHON) -u tools/qa_projectile_native.py
	$(PYTHON) -u tools/qa_final_native.py
	$(PYTHON) -u tools/qa_weapon_update.py

check-ui: all
	$(PYTHON) -u tools/qa_ui_performance.py --scenario menu
	$(PYTHON) -u tools/qa_ui_performance.py --scenario intro
	$(PYTHON) -u tools/qa_home_logo.py

.PHONY: check-player-bounds
check-player-bounds: all
	$(PYTHON) -u tools/qa_player_bounds.py

.PHONY: check-parallax
check-parallax: all
	$(PYTHON) -u tools/qa_parallax.py
	$(PYTHON) -u tools/qa_parallax_home.py
	$(PYTHON) -u tools/qa_parallax_home.py --off

check-performance: all
	$(PYTHON) -u tools/qa_performance.py

.PHONY: check-boss-performance
check-boss-performance: all
	$(PYTHON) -u tools/qa_boss_performance.py

check-items: all
	$(PYTHON) -u tools/qa_items.py

check-render: all
	$(PYTHON) -u tools/qa_render.py

check-options: all
	$(PYTHON) -u tools/qa_options.py

analyze: check-source
	bash tools/analyze_source.sh

run: all
	retroarch -L /usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so snes/sidearms_md_snes.sfc
