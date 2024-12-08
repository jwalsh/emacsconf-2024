#!/bin/bash

# Set paths
WHISPER_PATH="$HOME/opt/whisper.cpp"
MODEL="$WHISPER_PATH/models/ggml-base.bin"

# Get absolute paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
MEDIA_DIR="$( cd "$SCRIPT_DIR/../media.emacsconf.org/2024" &> /dev/null && pwd )"
TRANSCRIPT_DIR="$( cd "$SCRIPT_DIR/../transcripts" &> /dev/null && pwd )"

# Create output directory
mkdir -p "$TRANSCRIPT_DIR"

# Process all main videos
for video in "$MEDIA_DIR"/*--main.webm; do
    if [[ -f "$video" ]]; then
        base_name=$(basename "$video" .webm)
        
        # Skip if VTT already exists
        if [ -f "$TRANSCRIPT_DIR/$base_name.vtt" ]; then
            echo "Skipping (exists): $base_name"
            continue
        fi
        
        echo "Processing: $base_name"
        ffmpeg -i "$video" -ar 16000 -ac 1 -c:a pcm_s16le -f wav pipe:1 2>/dev/null | \
        "$WHISPER_PATH/main" \
            -m "$MODEL" \
            -f - \
            -of "$TRANSCRIPT_DIR/$base_name" \
            --output-vtt \
            -t 8
    fi
done

echo "Done processing videos"
