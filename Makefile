
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

# Add to your existing Makefile

COMMIT_TEMPLATE="Analyze this git diff and create a conventional commit message following these rules:\n\
1. Use types: feat|fix|docs|style|refactor|test|chore\n\
2. Optional scope in parentheses\n\
3. Short description in imperative mood\n\
4. Optionally followed by longer description\n\
5. Include relevant technical details\n\
\nDiff:\n"

commit-msg: ## Generate conventional commit message from current diff
	@if [ -z "$$(git diff)" ]; then \
		echo "$(CYAN)No changes to commit$(RESET)"; \
		exit 1; \
	fi
	@echo -e "$(COMMIT_TEMPLATE)" > /tmp/commit_prompt.txt
	@git diff >> /tmp/commit_prompt.txt
	@echo "$(CYAN)Generating commit message...$(RESET)"
	@ollama run codellama:latest < /tmp/commit_prompt.txt > /tmp/commit_msg.txt
	@echo "$(CYAN)Suggested commit message:$(RESET)"
	@cat /tmp/commit_msg.txt
	@echo "\n$(CYAN)Use this message? [y/N]$(RESET)"
	@read -r response; \
	if [ "$$response" = "y" ]; then \
		git commit -F /tmp/commit_msg.txt; \
	else \
		echo "$(CYAN)Commit cancelled$(RESET)"; \
	fi

suggest-commit: ## Just show the suggested commit message without committing
	@if [ -z "$$(git diff)" ]; then \
		echo "$(CYAN)No changes to analyze$(RESET)"; \
		exit 1; \
	fi
	@echo -e "$(COMMIT_TEMPLATE)" > /tmp/commit_prompt.txt
	@git diff >> /tmp/commit_prompt.txt
	@echo "$(CYAN)Generating commit suggestion...$(RESET)"
	@ollama run codellama:latest < /tmp/commit_prompt.txt
