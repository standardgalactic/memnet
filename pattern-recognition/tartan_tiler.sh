#!/usr/bin/env bash

# tartan_tiler.sh
# 1D TARTAN-style recursive semantic tiling.
# Partitions a signal into coherent tiles where
# oscillation of Phi stays below threshold epsilon.
#
# RSVP interpretation: implements the TARTAN approximation
# theorem constructively — recursively bisects the signal
# until each tile satisfies osc(Phi, T) <= epsilon.
# Each tile output includes its mean (Phi approx),
# range (oscillation), and coherence = 1/(1+osc).
#
# Input: one numeric value per line.

INPUT="${1:-signal.txt}"
EPSILON="${2:-0.25}"   # max allowed oscillation per tile

mapfile -t data < "$INPUT"
length=${#data[@]}

echo "tile_start,tile_end,tile_size,mean_phi,oscillation,coherence,is_coherent"

tile_stack=("0,$((length-1))")

while [[ ${#tile_stack[@]} -gt 0 ]]; do

    # Pop last entry
    entry="${tile_stack[-1]}"
    unset 'tile_stack[-1]'

    IFS=',' read -r lo hi <<< "$entry"
    size=$(( hi - lo + 1 ))

    # Compute min, max, mean over this tile
    min="${data[$lo]}"
    max="${data[$lo]}"
    sum="${data[$lo]}"

    for ((i=lo+1; i<=hi; i++)); do
        v="${data[$i]}"
        min=$(awk "BEGIN { print ($v < $min) ? $v : $min }")
        max=$(awk "BEGIN { print ($v > $max) ? $v : $max }")
        sum=$(awk "BEGIN { print $sum + $v }")
    done

    mean=$(awk  "BEGIN { print $sum / $size }")
    osc=$(awk   "BEGIN { print $max - $min }")
    coh=$(awk   "BEGIN { print 1 / (1 + $osc) }")
    ok=$(awk    "BEGIN { print ($osc <= $EPSILON || $size <= 1) ? 1 : 0 }")

    if [[ "$ok" == "1" ]]; then
        # Tile is coherent — emit it
        echo "$lo,$hi,$size,$mean,$osc,$coh,1"
    else
        # Bisect and push both halves
        mid=$(( (lo + hi) / 2 ))
        tile_stack+=("$lo,$mid")
        tile_stack+=("$((mid+1)),$hi")
    fi

done
