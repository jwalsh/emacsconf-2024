watch:
	mpv https://live0.emacsconf.org/gen.webm

watch-dev:
	mpv https://live0.emacsconf.org/dev.webm

gypsum:
	guix shell -m ./manifest_guile-gi.scm -- guile --r7rs
