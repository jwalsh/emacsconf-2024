#!/usr/bin/env python3

import os
from pathlib import Path
import click
import ollama
from typing import Optional, List, Tuple
from dataclasses import dataclass
import json
from webvtt import WebVTT
from datetime import datetime
from pydantic import BaseModel

class TechnicalTerm(BaseModel):
    """A technical term with context."""
    name: str
    definition: str
    context: str

class TalkSummaryFormat(BaseModel):
    """Schema for talk summaries from the model."""
    key_points: list[str]
    technical_terms: list[TechnicalTerm]

@dataclass
class TalkSummary:
    """Full talk summary including metadata."""
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

def find_vtt_files(media_dir: Path, local_transcript_dir: Path) -> List[Tuple[Path, bool]]:
    """Find VTT files and indicate if they are official or local transcripts."""
    vtt_files = []
    
    # Check media directory for official VTTs
    for vtt in media_dir.glob('**/*.vtt'):
        if '--main.vtt' in str(vtt) and '--chapters' not in str(vtt):
            vtt_files.append((vtt, True))  # True indicates official VTT
            
    # Check local transcripts directory
    if local_transcript_dir.exists():
        for vtt in local_transcript_dir.glob('*.vtt'):
            if not any(official_vtt.stem == vtt.stem for official_vtt, _ in vtt_files):
                vtt_files.append((vtt, False))  # False indicates local transcript
                
    return sorted(vtt_files, key=lambda x: x[0].stem)

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

def verify_content(content: str, title: str) -> bool:
    """Verify if content appears to be valid transcript content."""
    # Quick size checks first
    words = content.split()
    if len(words) < 300:  # Main transcripts typically have >300 words
        click.echo("Warning: Content too short to be main transcript")
        return False
        
    try:
        response = ollama.chat(
            model="phi3",
            messages=[{
                "role": "user", 
                "content": f"Does this appear to be a full talk transcript for '{title}'? Return JSON with verified: true/false and reason. First 200 chars:\n{content[:200]}"
            }],
            format={
                "type": "object", 
                "properties": {
                    "verified": {"type": "boolean"},
                    "reason": {"type": "string"}
                }, 
                "required": ["verified", "reason"]
            }
        )
        result = json.loads(response.message.content)
        if not result.get('verified', False):
            click.echo(f"Warning: {result.get('reason', 'Unknown reason')}")
        return result.get('verified', False)
    except Exception as e:
        click.echo(f"Verification error: {e}")
        return False

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
    return f"""Analyze this EmacsConf talk and provide a structured summary. Return as JSON.

Talk details:
Title: {title}
Speaker: {speaker}

Extract key technical points and important technical terms, focusing on Emacs-related concepts and tools.
For each technical term, include its definition and how it was specifically used in this talk.

Keep the response format exactly as:
{{
  "key_points": ["point 1", "point 2", ...],
  "technical_terms": [
    {{"name": "term name", "definition": "clear definition", "context": "how used in talk"}},
    ...
  ]
}}

Transcript:
{content[:4000]}"""

def generate_summary_collection(summaries_dir: Path):
    """Generate a single org file containing all summaries."""
    summary_file = summaries_dir.parent / "summaries.org"
    
    content = f"""#+TITLE: EmacsConf 2024 Talk Summaries
#+DATE: {datetime.now().strftime('%Y-%m-%d')}

"""
    
    for org_file in sorted(summaries_dir.glob("*.org")):
        if org_file.name.startswith("."): continue
        content += f"\n* [[{org_file}][Source]]\n\n"
        sections = org_file.read_text().split("** Meta")[0]
        content += sections + "\n"
    
    summary_file.write_text(content)
    click.echo(f"Generated {summary_file}")

def save_debug_output(debug_dir: Path, title: str, content: str):
    """Save debug output to file."""
    debug_file = debug_dir / f"{title.replace(' ', '_').lower()}_raw.txt"
    if debug_file.exists():
        existing = debug_file.read_text()
        content = f"{existing}\n\n{datetime.now().isoformat()}\n{content}"
    debug_file.write_text(content)

def generate_summary(content: str, title: str, speaker: str, output_path: Path, is_official: bool) -> Optional[TalkSummary]:
    """Generate summary using Llama with structured outputs."""
    debug_dir = output_path / "debug"
    debug_dir.mkdir(exist_ok=True)
    
    try:
        # Only verify content for non-official transcripts
        if not is_official and not verify_content(content, title):
            save_debug_output(debug_dir, title, f"\n=== Content Verification Failed ===\nFirst 500 chars:\n{content[:500]}")
            return None
            
        # Generate summary
        response = ollama.chat(
            model="llama3.2",
            messages=[{
                "role": "user", 
                "content": get_prompt(content, title, speaker)
            }],
            format=TalkSummaryFormat.model_json_schema()
        )
        
        if not response.message.content:
            save_debug_output(debug_dir, title, "\n=== Error ===\nEmpty response from model")
            return None
            
        save_debug_output(debug_dir, title, f"\n=== Model Response ===\n{response.message.content}")
        
        # Save raw response before parsing
        raw_file = output_path / "raw" / f"{title.replace(' ', '_').lower()}.json"
        raw_file.parent.mkdir(exist_ok=True)
        raw_file.write_text(response.message.content)
            
        parsed = TalkSummaryFormat.model_validate_json(response.message.content)
        
        return TalkSummary(
            title=title,
            speaker=speaker,
            key_points=parsed.key_points,
            technical_terms=parsed.technical_terms,
            meta={"model": "llama3.2", "transcript": "official" if is_official else "generated"}
        )
        
    except Exception as e:
        error_msg = f"\n=== Error ===\n{str(e)}"
        save_debug_output(debug_dir, title, error_msg)
        click.echo(f"Error generating summary: {e}", err=True)
        return None

@click.command()
@click.argument('media_dir', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help="Overwrite existing summaries")
@click.option('--output', default='summaries', help="Output directory for summaries")
@click.option('--transcripts', default='transcripts', help="Directory containing generated transcripts")
@click.option('--verbose', is_flag=True, help="Show detailed processing information")
def main(media_dir: str, force: bool, output: str, transcripts: str, verbose: bool):
    """Generate technical summaries for EmacsConf VTT files."""
    media_path = Path(media_dir)
    output_path = Path(output)
    transcript_path = Path(transcripts)
    output_path.mkdir(exist_ok=True)

    # Get both official and local VTT files
    vtt_files = find_vtt_files(media_path, transcript_path)
    click.echo(f"Found {len(vtt_files)} VTT files to process")

    for vtt_file, is_official in vtt_files:
        summary_file = output_path / f"{vtt_file.stem}.org"
        source = "official" if is_official else "generated"
        
        if summary_file.exists() and not force:
            click.echo(f"Skipping (exists): {summary_file}")
            continue

        click.echo(f"\nProcessing: {vtt_file.name} ({source})")
        
        content = parse_vtt_content(vtt_file)
        if not content:
            continue

        title, speaker = extract_talk_info(vtt_file.name)
        if verbose:
            click.echo(f"Title: {title}")
            click.echo(f"Speaker: {speaker}")
        
        summary = generate_summary(content, title, speaker, output_path, is_official)
        
        if summary:
            summary_file.write_text(summary.to_org())
            click.echo(f"✓ Generated: {summary_file}")
        else:
            click.echo(f"✗ Failed: {vtt_file.name}")
    
    # Generate combined summary file
    generate_summary_collection(output_path)

if __name__ == '__main__':
    main()
