#!/usr/bin/env python3

import sys
from typing import Literal
import click
import subprocess
from pydantic import BaseModel, Field
import ollama

class CommitMessage(BaseModel):
    """Schema for conventional commit messages."""
    commit_type: Literal[
        'feat', 'fix', 'docs', 'style', 'refactor',
        'perf', 'test', 'build', 'ci', 'chore'
    ] = Field(description="Type of change")
    
    scope: Literal[
        'schedule',    # Conference schedule and timing
        'stream',      # Streaming setup and configurations
        'track',       # Track-specific content (general/development)
        'talk',        # Individual talk details
        'chat',        # Chat and communication channels
        'setup',       # Setup instructions and configurations
        'org',         # Org-mode related content
        'core',        # Core Emacs/development topics
        'speaker',     # Speaker information
        'qa'          # Q&A and interaction details
    ] | None = Field(
        default=None,
        description="Scope of the change"
    )
    
    short_description: str = Field(
        description="Brief description of the change",
        min_length=1,
        max_length=100
    )
    
    long_description: str | None = Field(
        default=None,
        description="Detailed explanation if needed"
    )

    def format_message(self) -> str:
        """Format as conventional commit message."""
        header = f"{self.commit_type}"
        if self.scope:
            header += f"({self.scope})"
        desc = self.short_description.rstrip('.')
        header += f": {desc}"
        
        if self.long_description:
            return f"{header}\n\n{self.long_description}"
        return header

class ReviewResult(BaseModel):
    """Schema for commit message validation results."""
    passed: bool = Field(description="Whether the commit message passed validation")
    issues: list[str] = Field(
        default_factory=list,
        description="List of issues found, if any"
    )

class GitCommitAI:
    def __init__(
        self,
        generator: str = "llama3.2",
        validator: str = "phi3",
        max_attempts: int = 3
    ):
        self.generator = generator
        self.validator = validator
        self.max_attempts = max_attempts
        self.schema = CommitMessage.model_json_schema()
        self.review_schema = ReviewResult.model_json_schema()

    def get_staged_changes(self) -> str:
        """Get staged git changes."""
        try:
            diff = subprocess.check_output(['git', 'diff', '--staged']).decode()
            if not diff.strip():
                click.echo("No changes staged for commit", err=True)
                click.echo("Use 'git add <files>' to stage changes", err=True)
                sys.exit(1)
            return diff
        except subprocess.CalledProcessError as e:
            click.echo(f"Git error: {e}", err=True)
            sys.exit(1)

    def generate_message(self, diff: str, attempt: int = 1, feedback: str = None) -> CommitMessage:
        """Generate commit message using model."""
        prompt = [
            {"role": "system", "content": """You are a Git commit message generator.
Create conventional commit messages that are clear, specific, and follow the schema exactly.
Focus on the actual changes in the diff, not meta-information."""},
            {"role": "user", "content": f"""Generate a commit message as JSON matching this schema:
{self.schema}

Guidelines:
- Use specific scopes from the schema
- Keep descriptions concise and clear
- Focus on what changed and why"""
            }
        ]

        if feedback and attempt > 1:
            prompt.append({
                "role": "user", 
                "content": f"Consider this feedback from the reviewer:\n{feedback}\nPlease revise accordingly."
            })

        prompt.append({"role": "user", "content": f"Changes to analyze:\n{diff}"})

        try:
            response = ollama.chat(
                model=self.generator,
                messages=prompt,
                format=self.schema
            )
            return CommitMessage.model_validate_json(response.message.content)
        except Exception as e:
            click.echo(f"Error generating message: {e}", err=True)
            return None

    def validate_message(self, message: str) -> tuple[bool, str]:
        """Validate message using validator model."""
        prompt = [
            {"role": "system", "content": """You are a commit message reviewer.
Provide specific, actionable feedback focusing on conventional commits compliance.
Return a structured review result."""},
            {"role": "user", "content": f"""Review this commit message:
{message}

Return JSON matching this schema:
{self.review_schema}

Evaluate:
1. Conventional commits format compliance
2. Clarity and specificity
3. Appropriate scope usage
4. Description accuracy"""
            }
        ]

        try:
            response = ollama.chat(
                model=self.validator,
                messages=prompt,
                format=self.review_schema
            )
            result = ReviewResult.model_validate_json(response.message.content)
            return result.passed, "\n".join(result.issues) if result.issues else ""
        except Exception as e:
            return False, str(e)

    def commit_changes(self, message: str) -> bool:
        """Commit changes with the given message."""
        try:
            subprocess.run(['git', 'commit', '-m', message], check=True, text=True)
            click.secho("✓ Changes committed successfully!", fg="green")
            return True
        except subprocess.CalledProcessError as e:
            click.secho(f"Failed to commit: {e}", fg="red", err=True)
            return False

    def run(self) -> None:
        """Run the commit message generation and validation flow."""
        diff = self.get_staged_changes()
        
        feedback = None
        for attempt in range(1, self.max_attempts + 1):
            # Generation attempt
            click.secho(f"\n🤖 [{self.generator}] Analyzing changes... (Attempt {attempt}/{self.max_attempts})", fg="blue")
            if feedback:
                click.secho(f"Considering feedback from {self.validator}:", fg="yellow")
                click.echo(f"  {feedback}")
            
            commit_msg = self.generate_message(diff, attempt, feedback)
            if not commit_msg:
                continue
            
            formatted = commit_msg.format_message()
            click.echo("\nProposed commit message:")
            click.secho(formatted, fg="bright_blue")
            
            # Validation
            click.secho(f"\n🔍 [{self.validator}] Reviewing commit message...", fg="blue")
            passed, feedback = self.validate_message(formatted)
            
            if passed:
                click.secho("✓ Message approved!", fg="green")
                if feedback:
                    click.secho("Suggestions for future commits:", fg="yellow")
                    click.echo(f"  {feedback}")
                break
            else:
                click.secho("✗ Changes requested", fg="red")
                click.secho("Feedback:", fg="yellow")
                for line in feedback.split('\n'):
                    click.echo(f"  {line}")
                
                if attempt < self.max_attempts:
                    click.secho(f"\n🔄 Asking {self.generator} to revise based on {self.validator}'s feedback...", fg="blue")
        
        if click.confirm("\n💬 Use this message?", default=False):
            self.commit_changes(formatted)

@click.command()
@click.option(
    '-g', '--generator',
    default="llama3.2",
    help="Model to use for generation",
    show_default=True
)
@click.option(
    '-v', '--validator',
    default="phi3",
    help="Model to use for validation",
    show_default=True
)
@click.option(
    '-n', '--attempts',
    default=3,
    help="Maximum generation attempts",
    show_default=True
)
def main(generator: str, validator: str, attempts: int) -> None:
    """AI-powered conventional commit message generator for EmacsConf."""
    try:
        committer = GitCommitAI(
            generator=generator,
            validator=validator,
            max_attempts=attempts
        )
        committer.run()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(130)  # Standard interrupt exit code
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
