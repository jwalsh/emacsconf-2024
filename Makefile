
# Makefile
.PHONY: help watch watch-dev gypsum notes rust-example scheme-example elisp-example

CYAN=\033[0;36m
RESET=\033[0m

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'

watch: ## Watch general track stream
	mpv https://live0.emacsconf.org/gen.webm

watch-dev: ## Watch development track stream
	mpv https://live0.emacsconf.org/dev.webm

gypsum: ## Run Gypsum in Guix shell
	guix shell -m ./manifest_guile-gi.scm -- guile --r7rs

notes: ## Create a new org note with timestamp
	@emacs --batch --eval "(progn \
		(require 'org) \
		(with-temp-buffer \
			(insert (format \"#+TITLE: EmacsConf Notes - %s\n#+DATE: %s\n\n* Notes\n\" \
				(format-time-string \"%Y-%m-%d\") \
				(format-time-string \"%Y-%m-%d %H:%M\"))) \
			(write-file \"notes/$(shell date +%Y%m%d).org\")))"

rust-example: ## Create a new Rust example
	@mkdir -p examples/rust
	@echo 'fn main() {\n    println!("Hello from Rust!");\n}' > examples/rust/example.rs
	@rustc examples/rust/example.rs -o examples/rust/example
	@./examples/rust/example

scheme-example: ## Create a new Scheme example
	@mkdir -p examples/scheme
	@echo '(display "Hello from Scheme!\n")' > examples/scheme/example.scm
	@guile examples/scheme/example.scm

elisp-example: ## Create a new Elisp example
	@mkdir -p examples/elisp
	@echo '(message "Hello from Elisp!")' > examples/elisp/example.el
	@emacs --batch -l examples/elisp/example.el


commit-simple: ## Just show the suggested commit message without committing
	@poetry run python git-conv.py

commit: ## Staff Software commit message review 
	poetry run python git-conv.py -g codellama -v jwalsh/staff-engineers -n 5

mirror: ## Media mirror
	wget -mkEpnp https://media.emacsconf.org/2024/
