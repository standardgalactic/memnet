#!/usr/bin/env bash

# icepick.sh
#
# Creates a semantic repository snapshot by concatenating
# admissible source files into a single archive.
#
# Excludes:
#   - binaries
#   - media
#   - archives
#   - git internals
#   - transcripts
#   - generated text projections
#   - LaTeX
#   - subtitle systems
#
# Usage:
#   ./icepick.sh
#
# Optional:
#   ./icepick.sh snapshot.txt

set -euo pipefail

OUTPUT="${1:-icepick.txt}"

TMP="$(mktemp)"

echo "ICEPICK REPOSITORY SNAPSHOT" > "$TMP"
echo "Generated: $(date)" >> "$TMP"
echo >> "$TMP"

find . \
    -type f \
    ! -path "*/.git/*" \
    ! -path "*/__pycache__/*" \
    ! -path "*/node_modules/*" \
    ! -path "*/venv/*" \
    ! -path "*/.venv/*" \
    ! -path "*/target/*" \
    ! -path "*/build/*" \
    ! -path "*/dist/*" \
    ! -path "*/.idea/*" \
    ! -path "*/.vscode/*" \
    ! -name "*.png" \
    ! -name "*.jpg" \
    ! -name "*.jpeg" \
    ! -name "*.gif" \
    ! -name "*.webp" \
    ! -name "*.mp3" \
    ! -name "*.wav" \
    ! -name "*.flac" \
    ! -name "*.ogg" \
    ! -name "*.mp4" \
    ! -name "*.mkv" \
    ! -name "*.avi" \
    ! -name "*.mov" \
    ! -name "*.pdf" \
    ! -name "*.zip" \
    ! -name "*.tar" \
    ! -name "*.gz" \
    ! -name "*.7z" \
    ! -name "*.exe" \
    ! -name "*.dll" \
    ! -name "*.so" \
    ! -name "*.o" \
    ! -name "*.a" \
    ! -name "*.pyc" \
    ! -name "*.class" \
    ! -name "*.lock" \
    ! -name "*.json" \
    ! -name "*.srt" \
    ! -name "*.tsv" \
    ! -name "*.vtt" \
    ! -name "*.txt" \
    ! -name "*.tex" \
    ! -name "*.log" \
    ! -name "*.out" \
    ! -name "*.aux" \
    ! -name "icepick.txt" \
    | sort | while read -r file
do

    if file "$file" | grep -qiE 'text|xml|empty'; then

        {
            echo
            echo "=================================================="
            echo "FILE: $file"
            echo "=================================================="
            echo

            cat "$file"

            echo
            echo
        } >> "$TMP"

    fi

done

mv "$TMP" "$OUTPUT"

echo
echo "Snapshot written to:"
echo "  $OUTPUT"
echo
echo "Total size:"
du -h "$OUTPUT"
