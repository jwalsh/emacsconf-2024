#!/usr/bin/env python3

import subprocess
import sys
from typing import Optional, Literal
from pydantic import BaseModel, Field
import ollama

class CommitMessage(BaseModel):
    commit_type: str = Field(description="Type of change")
    scope: Optional[Literal['dev', 'gen', 'chat', 'stream', 'org', 'poetry']] = Field(
        default=None,
        description="Scope of change",
    )
    short_description: str = Field(description="Brief description")
    long_description: Optional[str] = Field(default=None)

    def format_message(self) -> str:
        """Format the commit message."""
        header = f"{self.commit_type}"
        if self.scope:
            header += f"({self.scope})"
        desc = self.short_description.rstrip('.')
        header += f": {desc}"
        
        if self.long_description:
            return f"{header}\n\n{self.long_description}"
        return header

class GitCommitAI:
    CYAN = '\033[0;36m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    NC = '\033[0m'

    def __init__(self, model: str = "llama3.2", stage_all: bool = False):
        self.model = model
        self.stage_all = stage_all

    def print_color(self, color: str, message: str):
        """Print a message in color."""
        print(f"{color}{message}{self.NC}")

    def stage_files(self) -> bool:
        """Stage files for commit."""
        try:
            if self.stage_all:
                subprocess.run(['git', 'add', '.'], check=True)
                return True
            
            status = subprocess.check_output(['git', 'status', '--porcelain']).decode()
            if not status:
                self.print_color(self.RED, "No changes to commit")
                return False
            
            print("\nUnstaged changes:")
            print(status)
            self.print_color(self.CYAN, "\nStage all changes? [y/N]")
            if input().lower().startswith('y'):
                subprocess.run(['git', 'add', '.'], check=True)
                return True
            return False
        except subprocess.CalledProcessError as e:
            self.print_color(self.RED, f"Failed to stage files: {e}")
            return False

    def check_git_changes(self) -> str:
        """Check for and return git changes."""
        try:
            diff = subprocess.check_output(['git', 'diff', '--staged']).decode()
            if not diff:
                if not self.stage_files():
                    self.print_color(self.RED, "No changes staged for commit")
                    sys.exit(1)
                diff = subprocess.check_output(['git', 'diff', '--staged']).decode()
            return diff
        except subprocess.CalledProcessError as e:
            self.print_color(self.RED, f"Git command failed: {e}")
            sys.exit(1)
        except Exception as e:
            self.print_color(self.RED, f"Unexpected error: {e}")
            sys.exit(1)

    def generate_commit_message(self, diff: str) -> CommitMessage:
        """Generate a commit message using Ollama."""
        self.print_color(self.CYAN, f"Analyzing changes with {self.model}...")

        prompt = "Create a conventional commit message for this diff:"

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": f"{prompt}\n\n{diff}"}],
                format=CommitMessage.model_json_schema()
            )
            
            self.print_color(self.CYAN, "Raw JSON response:")
            print(response.message.content)
            
            return CommitMessage.model_validate_json(response.message.content)
        except Exception as e:
            self.print_color(self.RED, f"Error generating commit message: {e}")
            sys.exit(1)

    def commit_changes(self, message: str):
        """Commit changes with the given message."""
        try:
            subprocess.run(['git', 'commit', '-m', message], check=True)
            self.print_color(self.GREEN, "Changes committed!")
        except subprocess.CalledProcessError as e:
            self.print_color(self.RED, f"Failed to commit changes: {e}")
            sys.exit(1)

    def run(self):
        """Run the commit message generator."""
        diff = self.check_git_changes()
        commit_msg = self.generate_commit_message(diff)
        
        self.print_color(self.CYAN, "\nFormatted commit message:")
        formatted_msg = commit_msg.format_message()
        print(formatted_msg)

        self.print_color(self.CYAN, "\nUse this message? [y/N]")
        if input().lower().startswith('y'):
            self.commit_changes(formatted_msg)
        else:
            self.print_color(self.CYAN, "Commit cancelled")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI-powered conventional commit message generator")
    parser.add_argument("-m", "--model", default="llama3.2", help="Ollama model to use")
    parser.add_argument("-a", "--all", action="store_true", help="Stage all changes before committing")
    args = parser.parse_args()

    try:
        committer = GitCommitAI(model=args.model, stage_all=args.all)
        committer.run()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
