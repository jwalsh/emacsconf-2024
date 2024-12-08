#!/usr/bin/env python3

import os
from pathlib import Path
import click
import ollama
from typing import Optional, List
from dataclasses import dataclass
import json
from webvtt import WebVTT
from datetime import datetime

@dataclass
class TechnicalTerm:
    """A technical term with context."""
    name: str
    definition: str
    context: str = ""

@dataclass
class TalkSummary:
    """Schema for talk summaries."""
    title: str
    speaker: str
    key_points: list[str]
    technical_terms: list[TechnicalTerm]
    meta: dict

    def to_org(self) -> str:
        terms_table = "| Term | Definition | Context |\n|-\n"
        for term in self.technical_terms:
            name = term.name.replace('|', '\\vert{}')
            definition = term.definition.replace('|', '\\vert{}')
            context = term.context.replace('|', '\\vert{}')
            terms_table += f"| {name} | {definition} | {context} |\n"

        return f"""* {self.title}
:PROPERTIES:
:SPEAKER: {self.speaker}
:END:

** Key Points
{chr(10).join(f'- {point}' for point in self.key_points)}

** Technical Terms
{terms_table}

** Meta
- Generated: {datetime.now().isoformat()}
- Model: {self.meta.get('model', 'unknown')}"""

def parse_vtt_content(vtt_path: Path) -> str:
    """Extract text content from VTT file."""
    try:
        vtt = WebVTT.read(str(vtt_path))
        text = " ".join(caption.text for caption in vtt)
        click.echo(f"Extracted {len(text)} characters")
        return text
    except Exception as e:
        click.echo(f"Error parsing {vtt_path}: {e}", err=True)
        return ""

def extract_talk_info(filename: str) -> tuple[str, str]:
    """Extract talk title and speaker from filename."""
    parts = filename.split('--')
    if len(parts) >= 3:
        title = parts[1].replace('-', ' ').title()
        speaker = parts[2].split('.')[0].replace('-', ' ').title()
        return title, speaker
    return "Unknown Title", "Unknown Speaker"

def get_prompt(content: str, title: str, speaker: str) -> str:
    """Get prompt for summary generation."""
    return f"""Analyze this EmacsConf talk:
Title: {title}
Speaker: {speaker}

Extract technical points and terms. For each term include:
1. Clear definition
2. How it was used in the talk
3. Connection to Emacs

Format response exactly as:
Key Points:
- [technical point]
- [another point]

Technical Terms:
Term: [term name]
Definition: [definition]
Context: [usage in talk]

Transcript start:
{content[:4000]}"""

def generate_summary(content: str, title: str, speaker: str) -> Optional[TalkSummary]:
    """Generate summary."""
    try:
        response = ollama.chat(
            model="phi3",
            messages=[{"role": "user", "content": get_prompt(content, title, speaker)}]
        )
        
        if not response.message.content:
            return None
            
        lines = response.message.content.split('\n')
        key_points = []
        technical_content = []
        current_section = None
        
        for line in lines:
            if 'Key Points:' in line:
                current_section = 'points'
            elif 'Technical Terms:' in line:
                current_section = 'terms'
            elif line.strip().startswith('- ') and current_section == 'points':
                key_points.append(line.strip()[2:])
            elif current_section == 'terms':
                technical_content.append(line)
        
        # Parse technical terms
        terms = []
        current_term = {}
        
        for line in technical_content:
            line = line.strip()
            if line.startswith('Term:'):
                if current_term:
                    terms.append(TechnicalTerm(**current_term))
                    current_term = {}
                current_term['name'] = line[5:].strip()
            elif line.startswith('Definition:'):
                current_term['definition'] = line[11:].strip()
            elif line.startswith('Context:'):
                current_term['context'] = line[8:].strip()
        
        if current_term:
            terms.append(TechnicalTerm(**current_term))
        
        return TalkSummary(
            title=title,
            speaker=speaker,
            key_points=key_points,
            technical_terms=terms,
            meta={"model": "phi3"}
        )
        
    except Exception as e:
        click.echo(f"Error generating summary: {e}", err=True)
        return None

@click.command()
@click.argument('media_dir', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help="Overwrite existing summaries")
@click.option('--output', default='summaries', help="Output directory for summaries")
@click.option('--verbose', is_flag=True, help="Show detailed processing information")
def main(media_dir: str, force: bool, output: str, verbose: bool):
    """Generate technical summaries for EmacsConf VTT files."""
    media_path = Path(media_dir)
    output_path = Path(output)
    output_path.mkdir(exist_ok=True)

    vtt_files = [f for f in media_path.glob('**/*.vtt') 
                 if '--main.vtt' in str(f) and '--chapters' not in str(f)]

    click.echo(f"Found {len(vtt_files)} VTT files to process")

    for vtt_file in vtt_files:
        summary_file = output_path / f"{vtt_file.stem}.org"
        
        if summary_file.exists() and not force:
            click.echo(f"Skipping (exists): {summary_file}")
            continue

        click.echo(f"\nProcessing: {vtt_file.name}")
        
        content = parse_vtt_content(vtt_file)
        if not content:
            continue

        title, speaker = extract_talk_info(vtt_file.name)
        if verbose:
            click.echo(f"Title: {title}")
            click.echo(f"Speaker: {speaker}")
        
        summary = generate_summary(content, title, speaker)
        
        if summary:
            summary_file.write_text(summary.to_org())
            click.echo(f"✓ Generated: {summary_file}")
        else:
            click.echo(f"✗ Failed: {vtt_file.name}")

if __name__ == '__main__':
    main()
